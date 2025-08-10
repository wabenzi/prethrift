"""Query pipeline: parse user text -> structured + embedding -> retrieve & rank garments.

Initial simple implementation; can evolve to ANN + feedback-aware reranking.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

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
    explanation: dict[str, Any]


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
    fams = pref.get("families") or pref.get("likes") or {}
    if isinstance(fams, dict):
        for fam, values in fams.items():
            if isinstance(values, list):
                attribs[fam] = [str(v) for v in values]
    # Local import to avoid circular dependency at module import time
    from .main import get_client  # inline import

    client = get_client()
    emb = user_state.cache_query_embedding(text, lambda t: embed_text(client, t))
    return ParsedQuery(raw=text, attributes=attribs, text_embedding=emb)


def _attribute_overlap_score(parsed: ParsedQuery, garment: Garment) -> tuple[float, list[dict]]:
    if not parsed.attributes or not garment.attributes:
        return 0.0, []
    fam_map: dict[str, set[str]] = {}
    for ga in garment.attributes:
        fam_map.setdefault(ga.attribute.family, set()).add(ga.attribute.value)
    details: list[dict] = []
    accum = 0.0
    counted = 0
    for fam, vals in parsed.attributes.items():
        qset = set(vals)
        gset = fam_map.get(fam)
        if not gset:
            continue
        inter_vals = sorted(qset & gset)
        union_set = qset | gset
        if union_set:
            jacc = len(inter_vals) / len(union_set)
            accum += jacc
            counted += 1
            details.append(
                {
                    "family": fam,
                    "query_values": sorted(qset),
                    "garment_values": sorted(gset),
                    "overlap_values": inter_vals,
                    "jaccard": jacc,
                }
            )
    if counted == 0:
        return 0.0, []
    overall = accum / counted
    return overall, details


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
        # DEBUG
        # print('DEBUG load prefs for', user_id, 'rows', len(rows))
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


def _load_user_negative_embedding(user_id: str | None) -> list[float] | None:
    if not user_id:
        return None
    # Negative cache key separate
    cached = user_state.get_user_embedding(user_id + "__neg")
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
                & (InteractionEvent.event_type.in_(["dislike"]))
            )
        ).all()
        vectors: list[list[float]] = []
        for ev in events:
            g = session.get(Garment, ev.garment_id)
            if g and g.description_embedding:
                vectors.append(g.description_embedding)
        emb = user_state.combine_embeddings(vectors)
        user_state.set_user_embedding(user_id + "__neg", emb)
        return emb


def retrieve_and_rank(
    parsed: ParsedQuery, limit: int = 10, user_id: str | None = None
) -> tuple[list[RankedGarment], dict[int, list]]:
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Preload attribute relationships for scoring
        garments = session.scalars(select(Garment)).all()
        # eager load attributes
        for g in garments:
            _ = g.attributes
        user_pref_weights = _load_user_preferences(user_id)
        user_positive_emb = _load_user_positive_embedding(user_id)
        user_negative_emb = _load_user_negative_embedding(user_id)

        results: list[RankedGarment] = []
        garment_attr_map: dict[int, list] = {g.id: list(g.attributes) for g in garments}
        for g in garments:
            components: dict[str, float] = {}
            contributions: dict[str, float] = {}
            score = 0.0
            weights_meta = {
                "text_similarity": 0.55,
                "attribute_overlap": 0.22,
                "preference_weight": 0.1,
                "positive_profile_similarity": 0.18,
                "negative_profile_penalty": 0.15,
            }
            # text similarity
            if parsed.text_embedding and g.description_embedding:
                sim = _cos(parsed.text_embedding, g.description_embedding)
                components["text_similarity"] = sim
                contributions["text_similarity"] = sim * weights_meta["text_similarity"]
                score += contributions["text_similarity"]
            # attribute overlap (with details)
            attr_score, attr_details = _attribute_overlap_score(parsed, g)
            components["attribute_overlap"] = attr_score
            contributions["attribute_overlap"] = attr_score * weights_meta["attribute_overlap"]
            score += contributions["attribute_overlap"]
            # preference weight
            pref_val = 0.0
            if user_pref_weights and g.attributes:
                weights = [user_pref_weights.get(ga.attribute_value_id, 0.0) for ga in g.attributes]
                if weights:
                    raw_pref = sum(weights) / len(weights)
                    import math as _m

                    pref_val = _m.tanh(raw_pref / 2.5)  # slightly stronger influence
                    if raw_pref > 0:
                        pref_val += 0.05  # guaranteed minimal boost after positive feedback
            components["preference_weight"] = pref_val
            contributions["preference_weight"] = pref_val * weights_meta["preference_weight"]
            score += contributions["preference_weight"]
            # TEMP DEBUG (will remove): ensure preference contributes when >0
            # print('DEBUG pref', pref_val, contributions['preference_weight'])
            # positive profile centroid similarity
            pos_sim = 0.0
            if user_positive_emb and g.description_embedding:
                pos_sim = _cos(user_positive_emb, g.description_embedding)
            components["positive_profile_similarity"] = pos_sim
            contributions["positive_profile_similarity"] = (
                pos_sim * weights_meta["positive_profile_similarity"]
            )
            score += contributions["positive_profile_similarity"]
            # negative profile (penalty)
            neg_pen = 0.0
            if user_negative_emb and g.description_embedding:
                neg_sim = _cos(user_negative_emb, g.description_embedding)
                # convert similarity into penalty (bounded 0..1)
                neg_pen = max(0.0, neg_sim)
            components["negative_profile_penalty"] = neg_pen
            contributions["negative_profile_penalty"] = (
                -neg_pen * weights_meta["negative_profile_penalty"]
            )
            score += contributions["negative_profile_penalty"]
            explanation = {
                "components": components,
                "attribute_details": attr_details,
                "weights": weights_meta,
                "contributions": contributions,
                "final_score": score,
                "garment_attributes": [
                    {
                        "family": ga.attribute.family,
                        "value": ga.attribute.value,
                        "confidence": ga.confidence,
                    }
                    for ga in garment_attr_map.get(g.id, [])
                ],
            }
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
    return results[:limit], garment_attr_map


def search(
    text: str,
    limit: int = 10,
    model: str | None = None,
    user_id: str | None = None,
) -> dict:
    parsed = parse_query(text, model=model)
    ranked, garment_attr_map = retrieve_and_rank(parsed, limit=limit, user_id=user_id)
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
                # Provide flattened attribute family/value pairs with stored confidence if available
                "attributes": [
                    {
                        "family": ga.attribute.family,
                        "value": ga.attribute.value,
                        "confidence": ga.confidence,
                    }
                    for ga in garment_attr_map.get(r.garment_id, [])
                ],
            }
            for r in ranked
        ],
    }
