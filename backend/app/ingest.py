"""Garment ingestion pipeline: create garment, extract image embedding, attach attributes."""

from __future__ import annotations

import os
from collections.abc import Iterable

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .db_models import AttributeValue, Base, Garment, GarmentAttribute
from .image_features import image_to_feature
from .ontology import normalize

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./prethrift.db")
_engine = create_engine(DATABASE_URL, future=True)


def init_db() -> None:
    Base.metadata.create_all(_engine)


def get_or_create_attribute(session: Session, family: str, value: str) -> AttributeValue:
    stmt = select(AttributeValue).where(
        AttributeValue.family == family, AttributeValue.value == value
    )
    existing = session.scalars(stmt).first()
    if existing:
        return existing
    attr = AttributeValue(family=family, value=value)
    session.add(attr)
    session.flush()
    return attr


def ingest_garment(
    external_id: str,
    image_path: str,
    raw_attributes: dict[str, Iterable[str]] | None = None,
    title: str | None = None,
    brand: str | None = None,
    price: float | None = None,
    currency: str | None = None,
) -> int:
    """Ingest a garment: create row, compute image embedding, attach attributes.

    Returns garment id.
    """
    init_db()
    with Session(_engine) as session:
        # Check duplicate
        existing = session.scalars(
            select(Garment).where(Garment.external_id == external_id)
        ).first()
        if existing:
            return existing.id

        embedding = image_to_feature(image_path)
        garment = Garment(
            external_id=external_id,
            title=title,
            brand=brand,
            price=price,
            currency=currency,
            image_path=image_path,
            image_embedding=embedding.tolist(),
        )
        session.add(garment)
        session.flush()

        if raw_attributes:
            for family, vals in raw_attributes.items():
                for v in vals:
                    n = normalize(family, v)
                    if not n:
                        continue
                    attr = get_or_create_attribute(session, family, n)
                    session.add(
                        GarmentAttribute(
                            garment_id=garment.id,
                            attribute_value_id=attr.id,
                            confidence=1.0,
                        )
                    )
        session.commit()
        return garment.id
