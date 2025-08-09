"""JSON schema definition for conversation preference extraction."""

from __future__ import annotations

PREFERENCE_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "PreferenceExtraction",
    "type": "object",
    "required": ["likes", "dislikes", "constraints", "uncertain"],
    "properties": {
        "likes": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "category": {"type": "array", "items": {"type": "string"}},
                "fit": {"type": "array", "items": {"type": "string"}},
                "material": {"type": "array", "items": {"type": "string"}},
                "color_primary": {"type": "array", "items": {"type": "string"}},
                "pattern": {"type": "array", "items": {"type": "string"}},
                "style": {"type": "array", "items": {"type": "string"}},
                "season": {"type": "array", "items": {"type": "string"}},
                "occasion": {"type": "array", "items": {"type": "string"}},
            },
        },
        "dislikes": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "category": {"type": "array", "items": {"type": "string"}},
                "fit": {"type": "array", "items": {"type": "string"}},
                "material": {"type": "array", "items": {"type": "string"}},
                "color_primary": {"type": "array", "items": {"type": "string"}},
                "pattern": {"type": "array", "items": {"type": "string"}},
                "style": {"type": "array", "items": {"type": "string"}},
            },
        },
        "constraints": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "price_max": {"type": "number"},
                "sustainability": {"type": "boolean"},
            },
        },
        "uncertain": {"type": "array", "items": {"type": "string"}},
        "meta": {"type": "object"},
    },
    "additionalProperties": False,
}
