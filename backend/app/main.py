import os
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from . import openai_extractor
from .db_models import Base, Garment
from .describe_images import describe_image, embed_text

app = FastAPI()
client: OpenAI | None = None


def get_client() -> OpenAI:
    global client
    if client is None:
        if "OPENAI_API_KEY" not in os.environ:
            raise RuntimeError("OPENAI_API_KEY not set")
        client = OpenAI()
    return client


@app.get("/")
def read_root():
    return {"message": "Prethrift API"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = None) -> dict[str, Any]:  # type: ignore[assignment]
    if file is None:  # FastAPI will inject UploadFile for 'file' form field
        raise HTTPException(status_code=400, detail="Missing file upload field 'file'")
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")
    try:
        contents = await file.read()
        # OpenAI client expects a file-like object; use bytes via in-memory buffer
        import io

        buffer = io.BytesIO(contents)
        buffer.name = file.filename  # type: ignore[attr-defined]
        result = get_client().audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=buffer,
        )
        text = getattr(result, "text", None) or getattr(result, "data", {}).get("text")  # defensive
        return {"filename": file.filename, "text": text}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


class PreferenceExtractRequest(BaseModel):
    conversation: str
    model: str | None = None


@app.post("/preferences/extract")
def preferences_extract(req: PreferenceExtractRequest) -> dict[str, Any]:
    """Extract structured garment preferences from a conversation transcript.

    Body:
      conversation: Raw conversation text (required)
      model: Optional OpenAI model override (default gpt-4o-mini)
    """
    if not req.conversation.strip():
        raise HTTPException(status_code=400, detail="conversation must not be empty")
    try:
        result = openai_extractor.extract_preferences(
            conversation=req.conversation, model=req.model or "gpt-4o-mini"
        )
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


class IngestRequest(BaseModel):
    external_id: str
    image_base64: str  # base64 encoded image data (png/jpg)
    attributes: dict[str, list[str]] | None = None
    title: str | None = None
    brand: str | None = None
    price: float | None = None
    currency: str | None = None


@app.post("/garments/ingest")
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
        from . import ingest as ingest_mod

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


class RefreshDescriptionRequest(BaseModel):
    garment_id: int
    model: str | None = None
    overwrite: bool = False


@app.post("/garments/refresh-description")
def refresh_description(req: RefreshDescriptionRequest) -> dict[str, Any]:
    """Recompute a garment's textual description & embedding from its image.

    Requires garment.image_path to be set. Skips if description exists unless overwrite.
    """
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        g = session.get(Garment, req.garment_id)
        if not g:
            raise HTTPException(status_code=404, detail="garment not found")
        if not g.image_path:
            raise HTTPException(status_code=400, detail="garment has no image_path")
        if g.description and not req.overwrite:
            return {"garment_id": g.id, "description": g.description, "cached": True}
        # Build temporary minimal client wrapper expecting same API as in describe_image
        if "OPENAI_API_KEY" not in os.environ:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY not set")
        client = get_client()
        from pathlib import Path

        try:
            text = describe_image(client, Path(g.image_path), req.model or "gpt-4o-mini")
            embedding = embed_text(client, text)
            g.description = text
            if embedding:
                g.description_embedding = embedding
            session.commit()
            return {
                "garment_id": g.id,
                "description": text,
                "embedding_dims": len(embedding) if embedding else 0,
                "cached": False,
            }
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e)) from e
