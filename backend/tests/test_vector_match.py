import numpy as np
from backend.app.vector_match import build_nn_index, cosine_similarity, query_nn


def test_cosine_similarity_basic():
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    assert cosine_similarity(a, b) == 1.0


def test_nn_query():
    vectors = np.eye(3)
    nn = build_nn_index(vectors)
    res = query_nn(nn, np.array([1.0, 0.0, 0.0]), k=2)
    assert res[0][0] == 0
    assert 0.99 <= res[0][1] <= 1.01
