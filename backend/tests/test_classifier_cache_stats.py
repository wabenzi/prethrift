from backend.app.ontology import classify_basic_cached, classify_cache_stats, clear_classify_cache


def test_classifier_cache_stats_counts():
    clear_classify_cache()
    desc1 = "A vintage graphic tee"
    desc2 = "A floral dress"
    classify_basic_cached(desc1)  # miss
    classify_basic_cached(desc1)  # hit
    classify_basic_cached(desc2)  # miss
    stats = classify_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 2
    assert stats["size"] == 2
    assert 0 < stats["hit_rate"] < 1
