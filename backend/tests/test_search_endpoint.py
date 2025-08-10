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
            title="Vintage Band Tee",
            description="Faded black vintage Queen band t-shirt",
            description_embedding=[0.1, 0.2, 0.3],
        )
        g2 = Garment(
            external_id="g2",
            title="Red Dress",
            description="Bright vibrant red summer dress",
            description_embedding=[0.05, 0.1, 0.2],
        )
        session.add_all([g1, g2])
        session.commit()
    return engine, db_url


def test_search_basic(monkeypatch):
    engine, db_url = _seed_db()
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    # monkeypatch embed_text to deterministic small vector near g1
    from backend.app import main as main_mod
    from backend.app import query_pipeline as qp

    def fake_embed_text(client, text):  # noqa: ARG001
        return [0.11, 0.21, 0.29]

    monkeypatch.setattr(qp, "embed_text", fake_embed_text)
    monkeypatch.setattr(main_mod, "get_client", lambda: None)

    # monkeypatch extractor to supply attributes
    def fake_extract_preferences(conversation: str, model: str):  # noqa: ARG001
        return {"families": {}}

    monkeypatch.setattr(qp.openai_extractor, "extract_preferences", fake_extract_preferences)

    c = TestClient(app)
    resp = c.post("/search", json={"query": "vintage black band tee"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["results"], "Should return results"
    # First result should be g1
    assert data["results"][0]["title"].startswith("Vintage")
