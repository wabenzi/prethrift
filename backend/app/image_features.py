"""Enhanced image feature extraction using CLIP visual embeddings.

This module provides CLIP-powered visual embeddings for fashion images with
graceful fallback to hash-based features when CLIP is unavailable. The CLIP
embeddings provide much better semantic understanding of garment similarities
compared to simple hash-based features.

Features:
- CLIP visual embeddings (512-dimensional)
- Fallback to deterministic hash-based features
- LRU cache for performance
- Same public API for backward compatibility
"""

from __future__ import annotations

import logging
from contextlib import suppress
from hashlib import blake2b
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

# Try to import CLIP functionality
try:
    from .local_cv import LocalGarmentAnalyzer
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

logger = logging.getLogger(__name__)

FEATURE_DIM = 512
_FEATURE_CACHE: dict[str, np.ndarray] = {}
_FEATURE_CACHE_ORDER: list[str] = []
_FEATURE_CACHE_MAX = 256
_FEATURE_CACHE_HITS = 0
_FEATURE_CACHE_MISSES = 0
_FEATURE_CACHE_EVICTIONS = 0

# Global CLIP analyzer instance (lazy initialization)
_clip_analyzer: Optional[LocalGarmentAnalyzer] = None


def _get_clip_analyzer() -> Optional[LocalGarmentAnalyzer]:
    """Get or create the global CLIP analyzer instance."""
    global _clip_analyzer
    if not CLIP_AVAILABLE:
        return None

    if _clip_analyzer is None:
        try:
            _clip_analyzer = LocalGarmentAnalyzer()
            logger.info("CLIP analyzer initialized for image embeddings")
        except Exception as e:
            logger.warning(f"Failed to initialize CLIP analyzer: {e}")
            return None

    return _clip_analyzer


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
    """
    Compute image features using CLIP visual embeddings with hash fallback.

    Args:
        path: Path to the image file

    Returns:
        512-dimensional feature vector as numpy array
    """
    # Try CLIP visual embeddings first
    analyzer = _get_clip_analyzer()
    if analyzer is not None:
        try:
            # Load and process image
            image = Image.open(path)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Get CLIP visual embedding
            embedding = analyzer.get_image_embedding(image)
            if embedding is not None and len(embedding) == FEATURE_DIM:
                logger.debug(f"Generated CLIP embedding for {path.name}")
                return np.array(embedding, dtype="float32")
            else:
                logger.warning(f"CLIP embedding failed for {path.name}, falling back to hash")
        except Exception as e:
            logger.warning(f"CLIP processing failed for {path.name}: {e}, falling back to hash")

    # Fallback to hash-based features
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
