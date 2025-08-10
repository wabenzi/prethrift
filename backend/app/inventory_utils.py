from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from sqlalchemy.orm import Session

from .db_models import GarmentAttribute


def persist_inventory_image_file(filename: str, image_b64: str) -> str:
    storage_dir = os.getenv("INVENTORY_IMAGE_DIR", "data/inventory")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)
    raw = base64.b64decode(image_b64, validate=True)
    digest = hashlib.sha1(raw).hexdigest()[:12]
    out = Path(storage_dir) / f"{digest}-{filename}"
    out.write_bytes(raw)
    return str(out)


def safe_add_garment_attribute(
    session: Session, garment_id: int, av_id: int, confidence: float
) -> None:
    from sqlalchemy.exc import IntegrityError

    try:
        with session.begin_nested():
            session.add(
                GarmentAttribute(
                    garment_id=garment_id,
                    attribute_value_id=av_id,
                    confidence=confidence,
                )
            )
            session.flush()
    except IntegrityError:
        pass
