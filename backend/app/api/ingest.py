from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["ingest"])


class IngestRequest(BaseModel):
    external_id: str
    image_base64: str  # base64 encoded image data (png/jpg)
    attributes: dict[str, list[str]] | None = None
    title: str | None = None
    brand: str | None = None
    price: float | None = None
    currency: str | None = None


@router.post("/garments/ingest")
def garments_ingest(req: IngestRequest) -> dict[str, Any]:
    """Ingest a garment with an image (base64) and optional attributes.

    Returns garment_id and external_id. If the external_id was previously ingested, the
    existing id is returned (idempotent).
    """
    if not req.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 required")
    try:
        import base64
        import hashlib
        from pathlib import Path

        # Decode image
        try:
            image_bytes = base64.b64decode(req.image_base64, validate=True)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"invalid base64: {e}") from e

        # Persist image to disk
        storage_dir = os.getenv("IMAGE_STORAGE_DIR", "data/images")
        Path(storage_dir).mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(req.external_id.encode()).hexdigest()[:10]
        image_path = Path(storage_dir) / f"{digest}.img"
        image_path.write_bytes(image_bytes)

        # Lazy import ingest module so tests can patch env before import
        from .. import ingest as ingest_mod

        # Convert attributes to expected type (dict[str, Iterable[str]]) explicitly
        raw_attrs: dict[str, list[str]] | None = None
        if req.attributes:
            raw_attrs = {k: list(v) for k, v in req.attributes.items()}
        garment_id = ingest_mod.ingest_garment(
            external_id=req.external_id,
            image_path=str(image_path),
            raw_attributes=raw_attrs,
            title=req.title,
            brand=req.brand,
            price=req.price,
            currency=req.currency,
        )
        return {"garment_id": garment_id, "external_id": req.external_id}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
