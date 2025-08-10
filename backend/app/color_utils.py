"""Map mean RGB triples to canonical color names.

Implements a simple Euclidean nearest-neighbor over a compact palette. Favor
clarity and determinism over exhaustive coverage.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

_PALETTE: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "navy": (10, 30, 80),
    "olive": (85, 90, 30),
    "brown": (110, 70, 40),
    "gray": (128, 128, 128),
    "red": (200, 40, 40),
    "blue": (40, 90, 210),
    "green": (40, 160, 70),
    "beige": (225, 210, 170),
}


def _dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def map_rgb_to_color_name(rgb: Sequence[float] | Sequence[int]) -> str:
    """Return closest palette color name for given mean RGB triple."""
    if not rgb or len(rgb) < 3:
        return "black"
    r, g, b = (float(rgb[0]), float(rgb[1]), float(rgb[2]))
    cand = (int(r), int(g), int(b))
    best_name = "black"
    best_d = 1e9
    for name, ref in _PALETTE.items():
        d = _dist(cand, ref)
        if d < best_d:
            best_d = d
            best_name = name
    return best_name
