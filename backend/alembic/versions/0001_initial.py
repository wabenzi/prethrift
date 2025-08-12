"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-08-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # garment
    op.create_table(
        "garment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("external_id", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(length=256)),
        sa.Column("brand", sa.String(length=128)),
        sa.Column("price", sa.Float),
        sa.Column("currency", sa.String(length=8)),
        sa.Column("image_path", sa.String(length=512)),
        sa.Column("image_embedding", sa.JSON),
        sa.Column("description", sa.String(length=2048)),
        sa.Column("description_embedding", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # attribute_value
    op.create_table(
        "attribute_value",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("family", sa.String(length=32), nullable=False, index=True),
        sa.Column("value", sa.String(length=64), nullable=False, index=True),
        sa.UniqueConstraint("family", "value", name="uq_family_value"),
    )

    # garment_attribute
    op.create_table(
        "garment_attribute",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "garment_id", sa.Integer, sa.ForeignKey("garment.id", ondelete="CASCADE"), index=True
        ),
        sa.Column(
            "attribute_value_id",
            sa.Integer,
            sa.ForeignKey("attribute_value.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("1.0")),
        sa.UniqueConstraint("garment_id", "attribute_value_id", name="uq_garment_attr"),
    )

    # inventory_image
    op.create_table(
        "inventory_image",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("file_path", sa.String(length=512), nullable=False, unique=True, index=True),
        sa.Column("original_format", sa.String(length=16)),
        sa.Column("optimized_format", sa.String(length=16)),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("hash", sa.String(length=64), index=True),
        sa.Column(
            "processed", sa.Boolean, nullable=False, server_default=sa.text("false"), index=True
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # inventory_item
    op.create_table(
        "inventory_item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "image_id",
            sa.Integer,
            sa.ForeignKey("inventory_image.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column(
            "garment_id", sa.Integer, sa.ForeignKey("garment.id", ondelete="SET NULL"), index=True
        ),
        sa.Column("slot_index", sa.Integer, nullable=False),
        sa.Column("description", sa.String(length=2048)),
        sa.Column("description_embedding", sa.JSON),
        sa.Column(
            "attributes_extracted", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("color_stats", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("image_id", "slot_index", name="uq_image_slot"),
    )

    # user_preference
    op.create_table(
        "user_preference",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(length=64), index=True),
        sa.Column(
            "attribute_value_id",
            sa.Integer,
            sa.ForeignKey("attribute_value.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("weight", sa.Float, nullable=False, server_default=sa.text("1.0")),
        sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("1.0")),
        sa.Column("last_updated", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "attribute_value_id", name="uq_user_attr_pref"),
    )

    # interaction_event
    op.create_table(
        "interaction_event",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(length=64), index=True),
        sa.Column(
            "garment_id", sa.Integer, sa.ForeignKey("garment.id", ondelete="CASCADE"), index=True
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("weight_delta", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column(
            "processed", sa.Boolean, nullable=False, server_default=sa.text("false"), index=True
        ),
    )


def downgrade():
    op.drop_table("interaction_event")
    op.drop_table("user_preference")
    op.drop_table("inventory_item")
    op.drop_table("inventory_image")
    op.drop_table("garment_attribute")
    op.drop_table("attribute_value")
    op.drop_table("garment")
