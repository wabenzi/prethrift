"""Query pipeline: parse user text -> structured + embedding -> retrieve & rank garments.

Initial simple implementation; can evolve to ANN + feedback-aware reranking.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from . import openai_extractor, user_state
from .db_models import Base, Garment
from .describe_images import embed_text


@dataclass
class ParsedQuery:
    raw: str
    attributes: dict[str, list[str]]  # family -> values
    text_embedding: list[float] | None


@dataclass
class RankedGarment:
    garment_id: int
    score: float
    title: str | None
    description: str | None
    explanation: dict[str, float]


def _cos(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        m = min(len(a), len(b))
        a = a[:m]
        b = b[:m]
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def parse_query(text: str, model: str | None = None) -> ParsedQuery:
    text = (text or "").strip()
    if not text:
        return ParsedQuery(raw=text, attributes={}, text_embedding=None)
    pref = openai_extractor.extract_preferences(conversation=text, model=model or "gpt-4o-mini")
    attribs: dict[str, list[str]] = {}
    for fam, values in pref.get("families", {}).items():  # families may not exist
        # values expected list[str]
        if isinstance(values, list):
            attribs[fam] = [str(v) for v in values]
    # Local import to avoid circular dependency at module import time
    from .main import get_client  # inline import

    client = get_client()
    emb = user_state.cache_query_embedding(text, lambda t: embed_text(client, t))
    return ParsedQuery(raw=text, attributes=attribs, text_embedding=emb)


def _attribute_overlap_score(parsed: ParsedQuery, garment: Garment) -> float:
    if not parsed.attributes:
        return 0.0
    if not garment.attributes:
        return 0.0
    # Build garment family->set(values)
    fam_map: dict[str, set[str]] = {}
    for ga in garment.attributes:
        fam_map.setdefault(ga.attribute.family, set()).add(ga.attribute.value)
    score = 0.0
    possible = 0.0
    for fam, vals in parsed.attributes.items():
        qset = set(vals)
        gset = fam_map.get(fam)
        if not gset:
            continue
        inter = len(qset & gset)
        union = len(qset | gset)
        if union:
            score += inter / union
            possible += 1
    if possible == 0:
        return 0.0
    return score / possible


def _load_user_preferences(user_id: str | None) -> dict[int, float]:
    if not user_id:
        return {}
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
    Base.metadata.create_all(engine)
    from sqlalchemy import select as _select

    from .db_models import UserPreference

    prefs: dict[int, float] = {}
    with Session(engine) as session:
        rows = session.scalars(
            _select(UserPreference).where(UserPreference.user_id == user_id)
        ).all()
        for r in rows:
            prefs[r.attribute_value_id] = r.weight
    return prefs


def _load_user_positive_embedding(user_id: str | None) -> list[float] | None:
    if not user_id:
        return None
    cached = user_state.get_user_embedding(user_id)
    if cached is not None:
        return cached
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
    Base.metadata.create_all(engine)

    from sqlalchemy import select as _select

    from .db_models import InteractionEvent

    with Session(engine) as session:
        events = session.scalars(
            _select(InteractionEvent).where(
                (InteractionEvent.user_id == user_id)
                & (InteractionEvent.event_type.in_(["like", "click"]))
            )
        ).all()
        vectors: list[list[float]] = []
        for ev in events:
            g = session.get(Garment, ev.garment_id)
            if g and g.description_embedding:
                vectors.append(g.description_embedding)
        emb = user_state.combine_embeddings(vectors)
        user_state.set_user_embedding(user_id, emb)
        return emb


def retrieve_and_rank(
    parsed: ParsedQuery, limit: int = 10, user_id: str | None = None
) -> list[RankedGarment]:
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Preload attribute relationships for scoring
        garments = session.scalars(select(Garment)).all()
        # eager load attributes
        for g in garments:
            # access relationship to load
            _ = g.attributes
        user_pref_weights = _load_user_preferences(user_id)
        user_positive_emb = _load_user_positive_embedding(user_id)
        results: list[RankedGarment] = []
        for g in garments:
            explanation: dict[str, float] = {}
            score = 0.0
            text_sim_weight = 0.6
            attr_weight = 0.25
            pref_weight = 0.1
            pos_centroid_weight = 0.15
            if parsed.text_embedding and g.description_embedding:
                sim = _cos(parsed.text_embedding, g.description_embedding)
                explanation["text_similarity"] = sim
                score += text_sim_weight * sim
            attr_score = _attribute_overlap_score(parsed, g)
            explanation["attribute_overlap"] = attr_score
            score += attr_weight * attr_score
            # preference score: average weight of garment attributes present in user prefs
            if user_pref_weights and g.attributes:
                weights = [user_pref_weights.get(ga.attribute_value_id, 0.0) for ga in g.attributes]
                if weights:
                    pref_score = sum(weights) / len(weights)
                    # normalize with tanh to bound extreme values
                    import math as _m

                    bounded = _m.tanh(pref_score / 3.0)  # soft bound
                    explanation["preference_weight"] = bounded
                    score += pref_weight * bounded
            if user_positive_emb and g.description_embedding:
                pos_sim = _cos(user_positive_emb, g.description_embedding)
                explanation["positive_profile_similarity"] = pos_sim
                score += pos_centroid_weight * pos_sim
            if score > 0:
                results.append(
                    RankedGarment(
                        garment_id=g.id,
                        score=score,
                        title=g.title,
                        description=g.description,
                        explanation=explanation,
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


def search(
    text: str,
    limit: int = 10,
    model: str | None = None,
    user_id: str | None = None,
) -> dict:
    parsed = parse_query(text, model=model)
    ranked = retrieve_and_rank(parsed, limit=limit, user_id=user_id)
    return {
        "query": parsed.raw,
        "attributes": parsed.attributes,
        "results": [
            {
                "garment_id": r.garment_id,
                "score": r.score,
                "title": r.title,
                "description": r.description,
                "explanation": r.explanation,
            }
            for r in ranked
        ],
    }
