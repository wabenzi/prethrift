from backend.app.main import app
from fastapi.testclient import TestClient


def test_preferences_extract_empty():
    client = TestClient(app)
    resp = client.post("/preferences/extract", json={"conversation": "   "})
    assert resp.status_code == 400


def test_preferences_extract_success(monkeypatch):
    client = TestClient(app)

    def fake_extract(conversation: str, model: str = "gpt-4o-mini"):
        # ensure parameters used for lint
        assert model.startswith("gpt-")
        assert "shirt" in conversation.lower()
        return {
            "likes": {"category": ["shirt"]},
            "dislikes": {},
            "constraints": {},
            "uncertain": [],
        }

    # Patch the real extractor
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from backend.app import openai_extractor

    monkeypatch.setattr(openai_extractor, "extract_preferences", fake_extract)

    resp = client.post(
        "/preferences/extract",
        json={"conversation": "I really like casual shirt styles."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["likes"]["category"] == ["shirt"]
