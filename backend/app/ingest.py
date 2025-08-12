"""Garment ingestion pipeline: create garment, extract image embedding, attach attributes."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .db_models import AttributeValue, Base, Garment, GarmentAttribute
from .image_features import image_to_feature
from .ontology import normalize

_ENGINE = None  # lazily initialized
_ENGINE_URL = None
_DB_SECRET_CACHE: dict | None = None


def _resolve_database_url() -> str:
    """Derive a SQLAlchemy database URL.

    Priority:
      1. Explicit DATABASE_URL env var.
      2. If DATABASE_SECRET_ARN present -> fetch secret (once) from Secrets Manager
         expecting JSON with keys: username, password, host, port, dbname.
      3. Fallback to local SQLite file for dev.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    secret_arn = os.getenv("DATABASE_SECRET_ARN")
    if secret_arn:
        global _DB_SECRET_CACHE
        if _DB_SECRET_CACHE is None:  # lazy fetch & cache
            try:
                import boto3  # type: ignore

                sm = boto3.client("secretsmanager")
                resp = sm.get_secret_value(SecretId=secret_arn)
                raw = resp.get("SecretString") or "{}"
                _DB_SECRET_CACHE = json.loads(raw)
            except Exception as e:  # pragma: no cover - best effort
                raise RuntimeError(f"Failed to retrieve DB secret: {e}") from e
        cfg = _DB_SECRET_CACHE or {}
        user = cfg.get("username")
        pwd = cfg.get("password")
        host = cfg.get("host") or cfg.get("hostname")
        port = cfg.get("port", 5432)
        db = cfg.get("dbname") or cfg.get("database") or "prethrift"
        if not (user and pwd and host):
            raise RuntimeError("Database secret missing required fields (username/password/host)")
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
    # default local
    return "sqlite:///./db/prethrift.db"


def get_engine():
    """Return a (possibly re-created) SQLAlchemy engine honoring current config."""
    global _ENGINE, _ENGINE_URL
    url = _resolve_database_url()
    if _ENGINE is None or url != _ENGINE_URL:
        _ENGINE = create_engine(url, future=True)
        _ENGINE_URL = url
        Base.metadata.create_all(_ENGINE)
    return _ENGINE


def init_db() -> None:
    get_engine()  # ensures metadata created


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
    raw_attributes: Mapping[str, Iterable[str]] | None = None,
    title: str | None = None,
    brand: str | None = None,
    price: float | None = None,
    currency: str | None = None,
) -> int:
    """Ingest a garment: create row, compute image embedding, attach attributes.

    Returns garment id.
    """
    engine = get_engine()
    with Session(engine) as session:
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
