from backend.app.ontology import classify_basic


def test_classify_basic_core_extraction():
    desc = "A vintage graphic band tee in soft cream cotton with relaxed fit"
    attrs = classify_basic(desc)
    # Expect some core families
    assert "pattern" in attrs and "graphic" in attrs["pattern"]
    assert "style" in attrs and ("vintage" in attrs["style"])
    # category should resolve to shirt (not multiple categories)
    assert attrs.get("category") == ["shirt"]
    # color normalization cream->beige
    assert "color_primary" in attrs and "beige" in attrs["color_primary"]


def test_classify_basic_boundary_and_disambiguation():
    # Mention multiple categories; priority ordering selects dress before shirt
    desc = "A casual summer dress layered over a long sleeve shirt with a graphic print"
    attrs = classify_basic(desc)
    assert attrs.get("category") == ["dress"], attrs.get("category")
    # Ensure pattern recognized
    assert "pattern" in attrs and "graphic" in attrs["pattern"]


def test_classify_basic_avoids_false_positive_substrings():
    # 'skirt' is inside 'skirted' but should not match if only appearing as that substring
    desc = "An elegant skirted hem silhouette with tailored finish"
    attrs = classify_basic(desc)
    assert "category" not in attrs or "skirt" not in attrs.get("category", []), attrs.get(
        "category"
    )
