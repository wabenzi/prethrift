"""In-memory caches for query embeddings and user profile embeddings.

These are ephemeral; suitable for a single process prototype.
"""

from __future__ import annotations

import math
from collections import OrderedDict

MAX_QUERY_CACHE = 256


class _LRU(OrderedDict):
    def __init__(self, maxsize: int):
        super().__init__()
        self.maxsize = maxsize

    def get_or_set(self, key, factory):
        if key in self:
            val = self.pop(key)
            self[key] = val
            return val
        val = factory()
        self[key] = val
        if len(self) > self.maxsize:
            self.popitem(last=False)
        return val


_query_embedding_cache = _LRU(MAX_QUERY_CACHE)
_user_embedding_cache: dict[str, list[float]] = {}


def cache_query_embedding(text: str, embed_fn) -> list[float] | None:
    text_norm = text.strip().lower()
    if not text_norm:
        return None

    def factory():
        return embed_fn(text)

    return _query_embedding_cache.get_or_set(text_norm, factory)


def set_user_embedding(user_id: str, emb: list[float] | None):
    if emb:
        _user_embedding_cache[user_id] = emb
    else:
        _user_embedding_cache.pop(user_id, None)


def get_user_embedding(user_id: str) -> list[float] | None:
    return _user_embedding_cache.get(user_id)


def combine_embeddings(vectors: list[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    length = min(len(v) for v in vectors)
    if length == 0:
        return None
    acc = [0.0] * length
    for v in vectors:
        for i in range(length):
            acc[i] += v[i]
    n = float(len(vectors))
    return [x / n for x in acc]


def decay_weight(age_days: float, half_life_days: float = 30.0) -> float:
    if age_days <= 0:
        return 1.0
    lam = math.log(2.0) / half_life_days
    return math.exp(-lam * age_days)
