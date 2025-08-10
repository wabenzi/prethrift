"""Vector matching utilities using cosine similarity and nearest neighbors."""

from __future__ import annotations

import numpy as np
from sklearn.neighbors import NearestNeighbors  # type: ignore[import-untyped]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        raise ValueError("Shape mismatch")
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def build_nn_index(vectors: np.ndarray, metric: str = "cosine") -> NearestNeighbors:
    if metric == "cosine":
        # For cosine, sklearn uses brute-force with metric='cosine' effectively computing 1 - cosine
        nn = NearestNeighbors(metric="cosine", algorithm="brute")
    else:
        nn = NearestNeighbors(metric=metric)
    nn.fit(vectors)
    return nn


def query_nn(nn: NearestNeighbors, query: np.ndarray, k: int = 5) -> list[tuple[int, float]]:
    distances, indices = nn.kneighbors(query.reshape(1, -1), n_neighbors=k)
    # Convert cosine distance to similarity if metric was cosine
    results: list[tuple[int, float]] = []
    for idx, dist in zip(indices[0], distances[0]):
        sim = 1 - dist  # cosine distance -> similarity
        results.append((int(idx), float(sim)))
    return results
