"""In-memory ontology and utilities for garment attributes.

Defines controlled vocabularies and synonym normalization.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttributeValue:
    family: str
    value: str
    canonical: str


# Core ontology families
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
}

# Synonym map lowers -> canonical
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
}


def normalize(family: str, raw: str) -> str | None:
    """Normalize a raw value into ontology canonical or return None."""
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
