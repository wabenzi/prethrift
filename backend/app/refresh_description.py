"""Shared core logic for refreshing a garment's description.

Both the legacy root endpoint (kept in main for test monkeypatch compatibility)
and the new /user/garments/refresh-description endpoint delegate here so the
business logic (attribute inference, embedding, caching) lives in one place.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .db_models import AttributeValue, Garment
from .inventory_utils import safe_add_garment_attribute as _safe_add_garment_attribute
from .ontology import attribute_confidences, classify_basic_cached

# Type aliases for injected functions (easier to monkeypatch in tests)
DescribeFn = Callable[[Any, Path, str], str]
EmbedFn = Callable[[str], list[float]]


def refresh_description_core(
    session: Session,
    garment_id: int,
    *,
    overwrite: bool,
    model: str,
    describe_fn: DescribeFn,
    embed_fn: EmbedFn,
    client: Any | None = None,
) -> dict[str, object]:
    """Refresh (or reuse) a garment description.

    Parameters
    ----------
    session : Session
        Active SQLAlchemy session (caller owns transaction lifecycle).
    garment_id : int
        Target garment id.
    overwrite : bool
        If False and description already present, short-circuits with cached=True.
    model : str
        Vision model name passed to describe_fn.
    describe_fn : callable(client, path, model)->str
        Function that returns description text (supports monkeypatching).
    embed_fn : callable(text)->list[float]
        Embedding function (already possibly cached) that returns vector or [].
    client : Any | None
        Optional OpenAI client (passed through to describe_fn).
    """
    g = session.get(Garment, garment_id)
    if not g:
        raise HTTPException(status_code=404, detail="garment not found")
    if not g.image_path:
        raise HTTPException(status_code=400, detail="garment has no image_path")
    if g.description and not overwrite:
        return {"garment_id": g.id, "description": g.description, "cached": True}

    # Generate description text
    text = describe_fn(client, Path(g.image_path), model)
    embedding = embed_fn(text) or []
    g.description = text
    if embedding:
        from contextlib import suppress

        with suppress(Exception):  # pragma: no cover - defensive
            g.description_embedding = embedding

    # Attribute inference & persistence
    inferred = classify_basic_cached(text)
    if inferred:
        conf_map = attribute_confidences(text, inferred)
        existing_pairs = {(ga.attribute.family, ga.attribute.value) for ga in g.attributes or []}
        for fam, vals in inferred.items():
            for v in vals:
                if (fam, v) in existing_pairs:
                    continue
                av = session.query(AttributeValue).filter_by(family=fam, value=v).first()
                if not av:
                    av = AttributeValue(family=fam, value=v)
                    session.add(av)
                    session.flush()
                _safe_add_garment_attribute(
                    session,
                    garment_id=g.id,
                    av_id=av.id,
                    confidence=conf_map.get((fam, v), 0.5),
                )
    session.commit()
    return {
        "garment_id": g.id,
        "description": text,
        "embedding_dims": len(embedding),
        "cached": False,
    }
