import tempfile
from pathlib import Path
from typing import Any

import pytest
from backend.app.db_models import Base, Garment
from backend.app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def setup_db():
    # use a unique temporary sqlite file each time to avoid cross-test UNIQUE collisions
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        url = f"sqlite:///{tmp.name}"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return engine, url


@pytest.fixture()
def client(monkeypatch):
    engine, db_url = setup_db()

    # Insert a garment with an image path
    img_path = Path("design/logo/logo.svg")  # existing small file
    with Session(engine) as session:
        g = Garment(external_id="ext1", image_path=str(img_path))
        session.add(g)
        session.commit()
        garment_id = g.id

    # Monkeypatch DB url env so endpoint uses this test DB
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Monkeypatch OpenAI client functions
    class DummyClient:
        def responses(self):  # pragma: no cover - shouldn't be called
            raise RuntimeError

    dummy_client = DummyClient()

    def fake_get_client():
        return dummy_client

    # patch module level get_client
    from backend.app import main as main_mod

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main_mod, "get_client", fake_get_client)

    # monkeypatch describe_image & embed_text
    def fake_describe_image(_client, _path, _model):  # noqa: D401
        return "A test description"

    def fake_embed_text(_client, _text):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(main_mod, "describe_image", fake_describe_image)
    monkeypatch.setattr(main_mod, "embed_text", fake_embed_text)

    c = TestClient(app)
    return c, garment_id


def test_refresh_description_first_call(client):
    c, garment_id = client
    r = c.post("/garments/refresh-description", json={"garment_id": garment_id})
    assert r.status_code == 200, r.text
    data: dict[str, Any] = r.json()
    assert data["garment_id"] == garment_id
    assert data["description"] == "A test description"
    assert data["cached"] is False

    # Second call should now be cached
    r2 = c.post("/garments/refresh-description", json={"garment_id": garment_id})
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["cached"] is True


def test_refresh_description_overwrite(client):
    c, garment_id = client
    # initial
    c.post("/garments/refresh-description", json={"garment_id": garment_id})
    # overwrite
    r = c.post(
        "/garments/refresh-description",
        json={"garment_id": garment_id, "overwrite": True},
    )
    assert r.status_code == 200
    assert r.json()["cached"] is False
