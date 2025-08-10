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

# --- Off-topic detection additions ---

def _build_fashion_vocab() -> set[str]:  # pragma: no cover
    try:
        from ..ontology import ONTOLOGY  # type: ignore
        vocab: set[str] = set()
        for fam, vals in ONTOLOGY.items():  # noqa: F402
            vocab.add(fam)
            vocab.update(vals)
        vocab.update({
            "vintage", "retro", "denim", "suede", "leather", "silk", "cotton", "linen", "wool",
            "outfit", "garment", "clothing"
        })
        return vocab
    except Exception:  # pragma: no cover
        return {"shirt", "pants", "dress", "skirt", "jacket", "jeans", "vintage", "denim"}

_FASHION_VOCAB = _build_fashion_vocab()
_OFF_TOPIC_MARKERS = {
    "bitcoin", "ethereum", "docker", "kubernetes", "recipe", "weather", "forecast", "football",
    "soccer", "stocks", "price", "currency", "python", "javascript", "movie", "music", "lyrics"
}

def _is_off_topic(q: str) -> tuple[bool, str]:
    import re as _re
    norm = q.lower().strip()
    if not norm:
        return True, "empty query"
    tokens = _re.findall(r"[a-zA-Z]+", norm)
    if not tokens:
        return True, "no alpha tokens"
    if any(t in _OFF_TOPIC_MARKERS for t in tokens):
        # allow fashion tokens to override
        fashion_hits = [t for t in tokens if t in _FASHION_VOCAB]
        if not fashion_hits:
            return True, "contains off-topic tokens"
    fashion_hits = [t for t in tokens if t in _FASHION_VOCAB]
    if fashion_hits:
        return False, "fashion tokens present"
    if len(tokens) >= 3:
        return True, "no fashion tokens in multi-word query"
    return False, "short generic allowed"

router = APIRouter(prefix="", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    limit: int | None = 10
    model: str | None = None
    user_id: str | None = None
    force: bool | None = False


class SearchResultItem(BaseModel):  # expanded garment representation
    garment_id: int | None = None
    score: float | None = None
    title: str | None = None
    brand: str | None = None
    price: float | None = None
    currency: str | None = None
    image_path: str | None = None
    description: str | None = None
    attributes: list[dict[str, Any]] | None = None
    explanation: dict[str, Any] | None = None
    thumbnail_url: str | None = None
    explanation_summary: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    query: str | None = None
    results: list[SearchResultItem] | None = None
    attributes: dict[str, Any] | None = None
    ambiguous: bool | None = None
    clarification: str | None = None
    off_topic: bool | None = None
    off_topic_reason: str | None = None
    message: str | None = None


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> dict[str, Any]:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    try:
        if not req.force:
            off_topic, reason = _is_off_topic(req.query)
            if off_topic:
                return {
                    "query": req.query,
                    "results": [],
                    "attributes": {},
                    "off_topic": True,
                    "off_topic_reason": reason,
                    "ambiguous": False,
                    "message": (
                        "That query doesn't look related to garments. Try adding a garment type, "
                        "style, era, color, or material (e.g., '70s brown suede jacket')."
                    ),
                }
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
        result["off_topic"] = False
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
