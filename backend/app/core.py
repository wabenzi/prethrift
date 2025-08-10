from __future__ import annotations

import os

from openai import OpenAI

from .describe_images import embed_text

client: OpenAI | None = None
_EMBED_TEXT_CACHE: dict[str, list[float]] = {}


def get_client() -> OpenAI:
    global client
    if client is None:
        if "OPENAI_API_KEY" not in os.environ:
            raise RuntimeError("OPENAI_API_KEY not set")
        client = OpenAI()
    return client


def embed_text_cached(text: str) -> list[float]:
    key = text.strip()
    if key in _EMBED_TEXT_CACHE:
        return _EMBED_TEXT_CACHE[key]
    c = get_client()
    vec = embed_text(c, text)
    if len(_EMBED_TEXT_CACHE) > 2048:
        _EMBED_TEXT_CACHE.clear()
    _EMBED_TEXT_CACHE[key] = vec
    return vec


def clear_embedding_cache() -> int:
    size = len(_EMBED_TEXT_CACHE)
    _EMBED_TEXT_CACHE.clear()
    return size
