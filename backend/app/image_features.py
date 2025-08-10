"""Lightweight placeholder image feature extraction.

Current implementation returns a deterministic zero vector (length 512) for any image path.
This keeps the ingestion & ranking pipeline type-safe without introducing heavyweight
torch / torchvision dependencies during early development. A future implementation can
replace this with a proper CNN (e.g., ResNet18 penultimate features) guarded by optional
imports, while preserving the function signature.
"""

from __future__ import annotations

import numpy as np

FEATURE_DIM = 512
_ZERO = np.zeros(FEATURE_DIM, dtype="float32")


def image_to_feature(_path: str, _device: str = "cpu") -> np.ndarray:  # noqa: D401
    # Arguments kept for future real implementation; currently unused.
    return _ZERO.copy()
