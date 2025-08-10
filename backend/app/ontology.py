"""In-memory ontology and utilities for garment attributes.

Provides:
    * Controlled vocabularies (ONTOLOGY)
    * Synonym normalization (SYNONYMS)
    * Heuristic attribute extractor with lightweight caching
    * Confidence scoring for extracted attributes
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AttributeValue:  # simple value object (not DB model)
    family: str
    value: str
    canonical: str


ONTOLOGY: dict[str, set[str]] = {
    "category": {"jacket", "shirt", "pants", "dress", "skirt", "shoes"},
    "fit": {"relaxed", "regular", "slim", "oversized"},
    "material": {"cotton", "denim", "wool", "leather", "linen", "silk", "synthetic"},
    "color_primary": {
        "black",
        "white",
        "navy",
        "olive",
        "brown",
        "gray",
        "red",
        "blue",
        "green",
        "beige",
    },
    "pattern": {"solid", "striped", "plaid", "floral", "graphic"},
    "style": {"vintage", "minimalist", "workwear", "streetwear", "formal", "casual"},
    "season": {"spring", "summer", "fall", "winter", "all-season"},
    "occasion": {"casual", "work", "evening", "outdoor"},
    "neckline": {"crew", "v-neck", "scoop", "collar"},
    "sleeve_length": {"short", "long", "sleeveless"},
}

SYNONYMS: dict[str, str] = {
    "tee": "shirt",
    "t-shirt": "shirt",
    "tee shirt": "shirt",
    "trousers": "pants",
    "coat": "jacket",
    "vintage style": "vintage",
    "work wear": "workwear",
    "olive green": "olive",
    "earth tone": "olive",
    "cream": "beige",
    "off white": "beige",
    "vneck": "v-neck",
    "short-sleeve": "short",
    "short-sleeved": "short",
    "long-sleeve": "long",
    "long-sleeved": "long",
}


def normalize(family: str, raw: str) -> str | None:
    r = raw.strip().lower()
    if r in SYNONYMS:
        r = SYNONYMS[r]
    if family in ONTOLOGY and r in ONTOLOGY[family]:
        return r
    return None


def families() -> list[str]:
    return list(ONTOLOGY.keys())


def all_values() -> dict[str, list[str]]:
    return {k: sorted(v) for k, v in ONTOLOGY.items()}


_CLASSIFY_CACHE: dict[str, dict[str, list[str]]] = {}
_CLASSIFY_HITS = 0
_CLASSIFY_MISSES = 0


def classify_basic(description: str) -> dict[str, list[str]]:
    """Extract ontology attributes from free-form description using heuristics.

    Goals: low false positive rate, determinism, inexpensive.
    """
    text = description.lower()
    tokens = re.findall(r"[a-zA-Z]+(?:'[a-z]+)?", text)
    token_set = set(tokens)

    out: dict[str, list[str]] = {}

    def add(fam: str, raw: str):
        valn = normalize(fam, raw)
        if not valn:
            return
        out.setdefault(fam, [])
        if valn not in out[fam]:
            out[fam].append(valn)

    fam_matches: dict[str, set[str]] = {}

    def fam_add(fam: str, val: str):
        fam_matches.setdefault(fam, set()).add(val)

    # Token / boundary matches
    for fam in ["category", "style", "color_primary", "pattern", "neckline", "sleeve_length"]:
        for candidate in ONTOLOGY.get(fam, []):
            if " " in candidate:
                if re.search(r"\b" + re.escape(candidate) + r"\b", text):
                    fam_add(fam, candidate)
            else:
                if candidate in token_set:
                    fam_add(fam, candidate)

    # Synonym surfaces
    for surf, canon in SYNONYMS.items():
        if (" " in surf and re.search(r"\b" + re.escape(surf) + r"\b", text)) or (
            " " not in surf and surf in token_set
        ):
            for fam, values in ONTOLOGY.items():
                if canon in values:
                    fam_add(fam, canon)

    # Loose boosts
    if "band" in token_set and ("tee" in token_set or "shirt" in token_set or "t" in token_set):
        fam_add("style", "vintage")
    if "graphic" in token_set:
        fam_add("pattern", "graphic")

    # Category single-selection
    if "category" in fam_matches and len(fam_matches["category"]) > 1:
        priority = ["dress", "jacket", "shirt", "pants", "skirt", "shoes"]
        for p in priority:
            if p in fam_matches["category"]:
                fam_matches["category"] = {p}
                break

    for fam, vals in fam_matches.items():
        for v in sorted(vals):
            add(fam, v)
    return out


def classify_basic_cached(description: str) -> dict[str, list[str]]:
    global _CLASSIFY_HITS, _CLASSIFY_MISSES
    key = description.strip().lower()
    cached = _CLASSIFY_CACHE.get(key)
    if cached is not None:
        _CLASSIFY_HITS += 1
        return cached
    _CLASSIFY_MISSES += 1
    result = classify_basic(description)
    if len(_CLASSIFY_CACHE) > 2048:  # simple size bound
        _CLASSIFY_CACHE.clear()
        _CLASSIFY_HITS = 0
        _CLASSIFY_MISSES = 0
    _CLASSIFY_CACHE[key] = result
    return result


def classify_cache_stats() -> dict[str, float | int]:
    total = _CLASSIFY_HITS + _CLASSIFY_MISSES
    hit_rate = (_CLASSIFY_HITS / total) if total else 0.0
    return {
        "size": len(_CLASSIFY_CACHE),
        "hits": _CLASSIFY_HITS,
        "misses": _CLASSIFY_MISSES,
        "hit_rate": round(hit_rate, 4),
    }


def clear_classify_cache() -> None:
    global _CLASSIFY_HITS, _CLASSIFY_MISSES
    _CLASSIFY_CACHE.clear()
    _CLASSIFY_HITS = 0
    _CLASSIFY_MISSES = 0


def attribute_confidences(
    description: str, attrs: dict[str, list[str]]
) -> dict[tuple[str, str], float]:
    """Assign heuristic confidences to extracted attributes.

    Scoring (capped at 0.95): base 0.55; +0.2 if first mention < token 30; +0.1 repeated;
    +0.05 if family in strong-cue set.
    """
    text = description.lower()
    tokens = re.findall(r"[a-zA-Z]+(?:'[a-z]+)?", text)
    conf: dict[tuple[str, str], float] = {}
    for fam, values in attrs.items():
        for v in values:
            base = 0.55
            occurrences = [i for i, t in enumerate(tokens) if t == v]
            if occurrences and occurrences[0] < 30:
                base += 0.2
            if len(occurrences) > 1:
                base += 0.1
            if fam in {"pattern", "style", "color_primary"}:
                base += 0.05
            if base > 0.95:
                base = 0.95
            conf[(fam, v)] = round(base, 3)
    return conf
