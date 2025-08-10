import tempfile

from backend.app.db_models import AttributeValue, Base, Garment, GarmentAttribute
from backend.app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def setup_env():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        url = f"sqlite:///{tmp.name}"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return engine, url


def seed(engine):
    with Session(engine) as session:
        av_color = AttributeValue(family="color", value="black")
        session.add(av_color)
        session.flush()
        g = Garment(
            external_id="g1",
            title="Test Garment",
            description="A test",
            description_embedding=[0.1, 0.2, 0.3],
        )
        session.add(g)
        session.flush()
        session.add(
            GarmentAttribute(garment_id=g.id, attribute_value_id=av_color.id, confidence=1.0)
        )
        session.commit()
        return g.id


def test_feedback_router_path(monkeypatch):
    engine, db_url = setup_env()
    gid = seed(engine)
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    c = TestClient(app)
    r = c.post("/feedback", json={"user_id": "userX", "garment_id": gid, "action": "view"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"
