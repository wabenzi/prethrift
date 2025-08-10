import tempfile

from backend.app.db_models import Base, Garment
from backend.app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def _seed_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_url = f"sqlite:///{tmp.name}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        g1 = Garment(
            external_id="g1",
            title="Vintage Denim Jacket",
            description="Classic blue vintage denim jacket with fading",
            description_embedding=[0.1, 0.2, 0.3],
        )
        session.add(g1)
        session.commit()
    return db_url


def _patch_embeddings(monkeypatch):
    # Patch embedding + preferences to avoid external calls
    from backend.app import main as main_mod
    from backend.app import query_pipeline as qp

    def fake_embed_text(client, text):  # noqa: ARG001
        return [0.11, 0.21, 0.29]

    def fake_extract_preferences(conversation: str, model: str):  # noqa: ARG001
        return {"families": {}}

    monkeypatch.setattr(qp, "embed_text", fake_embed_text)
    monkeypatch.setattr(qp.openai_extractor, "extract_preferences", fake_extract_preferences)
    monkeypatch.setattr(main_mod, "get_client", lambda: None)


def test_off_topic_rejected(monkeypatch):
    db_url = _seed_db()
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    _patch_embeddings(monkeypatch)

    client = TestClient(app)
    resp = client.post("/search", json={"query": "bitcoin price forecast"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("off_topic") is True
    assert data.get("results") == []
    assert "garment" in data.get("message", "").lower()
    assert data.get("off_topic_reason") in {
        "contains off-topic tokens",
        "no fashion tokens in multi-word query",
    }


def test_on_topic_not_flagged(monkeypatch):
    db_url = _seed_db()
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    _patch_embeddings(monkeypatch)

    client = TestClient(app)
    resp = client.post("/search", json={"query": "red vintage denim jacket"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("off_topic") is False
    assert data.get("results")  # should retrieve seeded jacket


def test_force_override_allows_off_topic(monkeypatch):
    db_url = _seed_db()
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    _patch_embeddings(monkeypatch)

    client = TestClient(app)
    resp = client.post("/search", json={"query": "weather forecast", "force": True})
    assert resp.status_code == 200
    data = resp.json()
    # Off-topic bypassed so flag is False
    assert data.get("off_topic") is False
    assert "results" in data


def test_short_generic_allowed(monkeypatch):
    db_url = _seed_db()
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    _patch_embeddings(monkeypatch)

    client = TestClient(app)
    resp = client.post("/search", json={"query": "dress"})
    assert resp.status_code == 200
    data = resp.json()
    # May be ambiguous but should not be off-topic
    assert data.get("off_topic") is False
