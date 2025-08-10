"""Conversation preference extractor using OpenAI API + JSON Schema validation."""

from __future__ import annotations

import json
import os
from typing import Any

try:  # jsonschema might be optional
    from jsonschema import Draft7Validator, ValidationError
except Exception:  # pragma: no cover
    Draft7Validator = None  # type: ignore
    ValidationError = Exception  # type: ignore

from openai import OpenAI

from .extractor_schema import PREFERENCE_JSON_SCHEMA
from .ontology import normalize

_validator = Draft7Validator(PREFERENCE_JSON_SCHEMA) if Draft7Validator is not None else None

SYSTEM_PROMPT = (
    "You extract structured garment preference data. "
    "Return ONLY valid JSON matching the schema. No prose. "
    "Normalize obvious plurals to singular (e.g., 'shirts'->'shirt'). "
    "If a value is not recognized, omit it or put into 'uncertain'."
)

SCHEMA_FAMILIES = [
    "category",
    "fit",
    "material",
    "color_primary",
    "pattern",
    "style",
    "season",
    "occasion",
]


def _postprocess(payload: dict[str, Any]) -> dict[str, Any]:
    # Ensure required top-level keys exist
    for key in ["likes", "dislikes", "constraints", "uncertain"]:
        payload.setdefault(key, {} if key != "uncertain" else [])

    def clean_section(section: dict[str, list[str]]) -> dict[str, list[str]]:
        cleaned: dict[str, list[str]] = {}
        for family, vals in section.items():
            kept: list[str] = []
            for v in vals:
                n = normalize(family, v)
                if n and n not in kept:
                    kept.append(n)
            if kept:
                cleaned[family] = kept
        return cleaned

    payload["likes"] = clean_section(payload.get("likes", {}))
    payload["dislikes"] = clean_section(payload.get("dislikes", {}))

    # Filter uncertain duplicates
    uncertain = []
    seen = set()
    for v in payload.get("uncertain", []):
        if v not in seen:
            uncertain.append(v)
            seen.add(v)
    payload["uncertain"] = uncertain
    return payload


def extract_preferences(conversation: str, model: str = "gpt-4o-mini") -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI()

    user_prompt = (
        "Conversation:\n"
        + conversation.strip()
        + "\n---\n"
        + "Return JSON with keys: likes, dislikes, constraints (price_max if any), uncertain."
    )

    response: Any = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    content = getattr(response.choices[0].message, "content", None)
    if not content:
        raise ValueError("Empty response from model")

    # Attempt to isolate JSON block
    raw = content.strip()
    if raw.startswith("```"):
        # Remove leading & trailing markdown fences
        raw = raw.strip("`")
    if raw.startswith("json"):
        raw = raw[4:]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}: {raw[:120]}") from e

    # Validate
    if _validator is not None:
        errors = sorted(_validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            msgs = [f"{list(err.path)}: {err.message}" for err in errors]
            raise ValidationError("; ".join(msgs))

    return _postprocess(data)
