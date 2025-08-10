from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .. import openai_extractor
from ..core import embed_text_cached, get_client
from ..db_models import Base
from ..describe_images import describe_image as _orig_describe_image
from ..refresh_description import DescribeFn, refresh_description_core

# Re-export describe_image name for tests that monkeypatch this module directly.
describe_image = _orig_describe_image

__all__ = [
    "router",
    "preferences_extract",
    "refresh_description",
    "describe_image",
]

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/ping")
async def user_ping():
    return {"ok": True}


class PreferenceExtractRequest(BaseModel):
    conversation: str
    model: str | None = None


@router.post("/preferences/extract")
def preferences_extract(req: PreferenceExtractRequest) -> dict[str, object]:
    if not req.conversation.strip():
        raise HTTPException(status_code=400, detail="conversation must not be empty")
    try:
        return openai_extractor.extract_preferences(
            conversation=req.conversation, model=req.model or "gpt-4o-mini"
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


class RefreshDescriptionRequest(BaseModel):
    garment_id: int
    model: str | None = None
    overwrite: bool = False


@router.post("/garments/refresh-description")
def refresh_description(req: RefreshDescriptionRequest) -> dict[str, object]:
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # For tests we allow operation with or without a real OpenAI key: if missing, no client
        client = None
        if "OPENAI_API_KEY" in os.environ and not os.environ.get("OPENAI_API_KEY", " ").startswith(
            "test-"
        ):
            try:
                client = get_client()
            except Exception:  # pragma: no cover
                client = None
        try:
            # Prefer module-level describe_image; fall back to main if only patched there.
            # Module level symbol (monkeypatched in tests) else fallback
            describe_fn: DescribeFn = globals().get("describe_image", _orig_describe_image)  # type: ignore[assignment]
            return refresh_description_core(
                session,
                req.garment_id,
                overwrite=req.overwrite,
                model=req.model or "gpt-4o-mini",
                describe_fn=describe_fn,
                embed_fn=embed_text_cached,
                client=client,
            )
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e)) from e


## Legacy routes removed (tests now target /user paths directly)
