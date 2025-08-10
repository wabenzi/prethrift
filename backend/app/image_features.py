"""Lightweight image feature extraction with graceful zero fallback.

The original implementation optionally used torchvision ResNet18. To simplify
type-checking and avoid heavy optional dependencies during tests, this module
returns a deterministic pseudo-random (hash-based) vector per file path while
preserving the same public API (FEATURE_DIM, image_to_feature, cache helpers).
If you later want real CNN features, reintroduce a backbone inside `_compute`.
"""

from __future__ import annotations

from contextlib import suppress
from hashlib import blake2b
from pathlib import Path

import numpy as np

FEATURE_DIM = 512
_FEATURE_CACHE: dict[str, np.ndarray] = {}
_FEATURE_CACHE_ORDER: list[str] = []
_FEATURE_CACHE_MAX = 256
_FEATURE_CACHE_HITS = 0
_FEATURE_CACHE_MISSES = 0
_FEATURE_CACHE_EVICTIONS = 0


def _lru_touch(key: str, value: np.ndarray | None = None) -> None:
    if value is not None and key not in _FEATURE_CACHE:
        global _FEATURE_CACHE_MISSES
        _FEATURE_CACHE_MISSES += 1
    if value is not None:
        _FEATURE_CACHE[key] = value
    with suppress(ValueError):  # pragma: no cover
        _FEATURE_CACHE_ORDER.remove(key)
    _FEATURE_CACHE_ORDER.append(key)
    global _FEATURE_CACHE_EVICTIONS
    if len(_FEATURE_CACHE_ORDER) > _FEATURE_CACHE_MAX:
        old = _FEATURE_CACHE_ORDER.pop(0)
        _FEATURE_CACHE.pop(old, None)
        _FEATURE_CACHE_EVICTIONS += 1


def _hash_bytes(data: bytes) -> np.ndarray:
    # Derive deterministic 512-dim vector (32-byte digest expanded/repeated)
    h = blake2b(data, digest_size=32).digest()
    rep = (FEATURE_DIM + len(h) - 1) // len(h)
    raw = (h * rep)[:FEATURE_DIM]
    arr = np.frombuffer(raw, dtype=np.uint8).astype("float32")
    # Normalize to unit length (avoid divide by zero)
    norm = float(np.linalg.norm(arr)) or 1.0
    return (arr / norm).astype("float32")


def _compute(path: Path) -> np.ndarray:
    try:
        data = path.read_bytes()
    except Exception:  # pragma: no cover
        data = path.name.encode("utf-8")
    return _hash_bytes(data[:4096])  # cap to first 4KB for stability


def image_to_feature(path: str, device: str = "cpu") -> np.ndarray:  # noqa: D401
    del device  # unused in lightweight implementation
    cached = _FEATURE_CACHE.get(path)
    if cached is not None:
        global _FEATURE_CACHE_HITS
        _FEATURE_CACHE_HITS += 1
        _lru_touch(path)
        return cached.copy()
    p = Path(path)
    vec = _compute(p)
    _lru_touch(path, vec)
    return vec.copy()


def clear_feature_cache() -> None:
    _FEATURE_CACHE.clear()
    _FEATURE_CACHE_ORDER.clear()
    global _FEATURE_CACHE_HITS, _FEATURE_CACHE_MISSES, _FEATURE_CACHE_EVICTIONS
    _FEATURE_CACHE_HITS = 0
    _FEATURE_CACHE_MISSES = 0
    _FEATURE_CACHE_EVICTIONS = 0


def feature_cache_stats() -> dict[str, int | float]:
    total = _FEATURE_CACHE_HITS + _FEATURE_CACHE_MISSES
    hit_rate = _FEATURE_CACHE_HITS / total if total else 0.0
    return {
        "size": len(_FEATURE_CACHE_ORDER),
        "capacity": _FEATURE_CACHE_MAX,
        "hits": _FEATURE_CACHE_HITS,
        "misses": _FEATURE_CACHE_MISSES,
        "evictions": _FEATURE_CACHE_EVICTIONS,
        "hit_rate": round(hit_rate, 4),
    }
