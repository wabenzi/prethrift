from backend.app.ontology import attribute_confidences, classify_basic


def test_classify_basic_neckline_and_sleeve():
    desc = "A vintage graphic crew neckline short sleeve cotton tee in beige"
    attrs = classify_basic(desc)
    assert attrs.get("neckline") == ["crew"], attrs
    assert "sleeve_length" in attrs and attrs["sleeve_length"] == ["short"], attrs
    conf = attribute_confidences(desc, attrs)
    # Confidence should exist and be within range
    for key, c in conf.items():
        assert 0.5 <= c <= 0.95, (key, c)


def test_attribute_confidence_multiple_occurrences():
    desc = "A red red vintage tee with crew crew neckline"
    attrs = classify_basic(desc)
    conf = attribute_confidences(desc, attrs)
    # red and crew should get boost for multiple occurrences
    red_conf = conf.get(("color_primary", "red"))
    crew_conf = conf.get(("neckline", "crew"))
    assert red_conf is not None and crew_conf is not None
    assert red_conf >= 0.7
    assert crew_conf >= 0.7
