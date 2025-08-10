"""SQLAlchemy ORM models for garment attributes and user preferences."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

metadata_obj = MetaData()


class Base(DeclarativeBase):
    metadata = metadata_obj


class Garment(Base):
    __tablename__ = "garment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(256))
    brand: Mapped[str | None] = mapped_column(String(128))
    price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(8))
    image_path: Mapped[str | None] = mapped_column(String(512))
    image_embedding: Mapped[list[float] | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(2048))
    description_embedding: Mapped[list[float] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    attributes: Mapped[list[GarmentAttribute]] = relationship(
        back_populates="garment", cascade="all,delete-orphan"
    )


class InventoryImage(Base):
    """Raw inventory image (may depict multiple garments)."""

    __tablename__ = "inventory_image"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_path: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    original_format: Mapped[str | None] = mapped_column(String(16))
    optimized_format: Mapped[str | None] = mapped_column(String(16))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    hash: Mapped[str | None] = mapped_column(String(64), index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class InventoryItem(Base):
    """Individual garment interpretation extracted from an inventory image."""

    __tablename__ = "inventory_item"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_image.id", ondelete="CASCADE"), index=True
    )
    garment_id: Mapped[int | None] = mapped_column(
        ForeignKey("garment.id", ondelete="SET NULL"), index=True
    )
    slot_index: Mapped[int] = mapped_column(
        Integer
    )  # sequential index if multiple garments detected
    description: Mapped[str | None] = mapped_column(String(2048))
    description_embedding: Mapped[list[float] | None] = mapped_column(JSON)
    attributes_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    color_stats: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    __table_args__ = (UniqueConstraint("image_id", "slot_index", name="uq_image_slot"),)


class AttributeValue(Base):
    __tablename__ = "attribute_value"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[str] = mapped_column(String(64), index=True)
    __table_args__ = (UniqueConstraint("family", "value", name="uq_family_value"),)


class GarmentAttribute(Base):
    __tablename__ = "garment_attribute"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    garment_id: Mapped[int] = mapped_column(
        ForeignKey("garment.id", ondelete="CASCADE"), index=True
    )
    attribute_value_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_value.id", ondelete="CASCADE"), index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    garment: Mapped[Garment] = relationship(back_populates="attributes")
    attribute: Mapped[AttributeValue] = relationship()
    __table_args__ = (UniqueConstraint("garment_id", "attribute_value_id", name="uq_garment_attr"),)


class UserPreference(Base):
    __tablename__ = "user_preference"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    attribute_value_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_value.id", ondelete="CASCADE"), index=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    attribute: Mapped[AttributeValue] = relationship()
    __table_args__ = (UniqueConstraint("user_id", "attribute_value_id", name="uq_user_attr_pref"),)


class InteractionEvent(Base):
    __tablename__ = "interaction_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    garment_id: Mapped[int] = mapped_column(
        ForeignKey("garment.id", ondelete="CASCADE"), index=True
    )
    # event_type examples: view, click, add_to_cart, purchase, dislike
    event_type: Mapped[str] = mapped_column(String(32))
    weight_delta: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
