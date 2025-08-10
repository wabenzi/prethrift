from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import query_pipeline
from ..core import get_client


def _is_ambiguous(q: str) -> bool:
    """Heuristic ambiguity detector.

    Flags queries that are overly short, purely generic category/color words,
    or contain conflicting plural categories without modifiers.
    """
    ql = q.lower().strip()
    if not ql:
        return True
    if len(ql) < 3:
        return True
    tokens = [t for t in ql.replace("/", " ").split() if t]
    if len(tokens) <= 2:
        generic = {"shirt", "pants", "dress", "jacket", "top", "red", "blue", "black", "shoes"}
        if all(t in generic for t in tokens):
            return True
    # conflicting categories heuristic
    cat_words = {"shirt", "pants", "dress", "skirt", "jacket", "jeans", "shoes", "tee", "tshirt"}
    cats_in = [t for t in tokens if t in cat_words]
    return bool(len(set(cats_in)) > 1 and len(tokens) <= 4)


def _clarify_query(original: str, model: str | None) -> str:
    """Use OpenAI to gently ask user for clarification; fall back to static message."""
    try:
        if "OPENAI_API_KEY" not in __import__("os").environ:
            raise RuntimeError("no key")
        client = get_client()
        prompt = (
            "The user issued a fashion search query that seems ambiguous or underspecified. "
            f"Query: '{original}'. Provide a brief, friendly clarification question asking for a "
            "more specific attribute (e.g., color shade, garment type, style) in <=25 words."
        )
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You generate one short clarifying question."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=60,
        )
        content = getattr(resp.choices[0].message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:  # noqa: BLE001
        pass
    return (
        "Could you add a bit more detail (e.g., style, fit, material, or color nuance) so I can "
        "improve the results?"
    )

router = APIRouter(prefix="", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    limit: int | None = 10
    model: str | None = None
    user_id: str | None = None


@router.post("/search")
def search(req: SearchRequest) -> dict[str, Any]:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    try:
        ambiguous = _is_ambiguous(req.query)
        result = query_pipeline.search(
            req.query, limit=req.limit or 10, model=req.model, user_id=req.user_id
        )
        if ambiguous:
            clarification = _clarify_query(req.query, req.model)
            result["clarification"] = clarification
            result["ambiguous"] = True
        else:
            result["ambiguous"] = False
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
