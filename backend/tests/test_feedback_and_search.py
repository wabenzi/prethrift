import tempfile

from backend.app.db_models import AttributeValue, Base, Garment, GarmentAttribute
from backend.app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def setup_env(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_url = f"sqlite:///{tmp.name}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    return engine


def seed(engine):
    with Session(engine) as session:
        # attribute values
        av_band = AttributeValue(family="style", value="band")
        av_black = AttributeValue(family="color", value="black")
        session.add_all([av_band, av_black])
        session.flush()
        g = Garment(
            external_id="g-band",
            title="Black Band Tee",
            description="Black band graphic tee",
            description_embedding=[0.2, 0.1, 0.05],
        )
        session.add(g)
        session.flush()
        session.add_all(
            [
                GarmentAttribute(garment_id=g.id, attribute_value_id=av_band.id, confidence=1.0),
                GarmentAttribute(garment_id=g.id, attribute_value_id=av_black.id, confidence=1.0),
            ]
        )
        session.commit()
        return g.id


def test_feedback_updates_preferences(monkeypatch):
    engine = setup_env(monkeypatch)
    gid = seed(engine)

    # monkeypatch query pipeline embedding + extractor
    from backend.app import query_pipeline as qp

    def fake_embed_text(client, text):  # noqa: ARG001
        return [0.21, 0.09, 0.05]

    def fake_extract_preferences(conversation: str, model: str):  # noqa: ARG001
        return {"families": {"color": ["black"], "style": ["band"]}}

    monkeypatch.setattr(qp, "embed_text", fake_embed_text)
    monkeypatch.setattr(qp.openai_extractor, "extract_preferences", fake_extract_preferences)

    c = TestClient(app)
    # initial search (no prefs)
    r1 = c.post("/search", json={"query": "black band tee", "user_id": "u1"})
    assert r1.status_code == 200
    base_score = r1.json()["results"][0]["score"]

    # send like feedback
    fb = c.post(
        "/feedback", json={"user_id": "u1", "garment_id": gid, "action": "like", "weight": 2}
    )
    assert fb.status_code == 200

    r2 = c.post("/search", json={"query": "black band tee", "user_id": "u1"})
    assert r2.status_code == 200
    new_score = r2.json()["results"][0]["score"]
    assert new_score > base_score, (base_score, new_score)
