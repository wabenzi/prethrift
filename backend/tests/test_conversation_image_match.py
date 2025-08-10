import base64
import os
import tempfile
from pathlib import Path

from backend.app.db_models import Base
from backend.app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

CONVERSATION = (
    "I'm a sporty person that wears subdued colors and am looking for a t-shirt "
    "for my brand conscious closet. Something minimalist like a grey Calvin Klein tee."
)


def setup_env(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_url = f"sqlite:///{tmp.name}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    return engine


def test_conversation_matches_grey_brand_tshirt(monkeypatch, tmp_path):
    """Full flow: ingest an image garment, simulate conversation -> search ranking picks it."""
    setup_env(monkeypatch)

    from backend.app import query_pipeline as qp

    def fake_extract_preferences(conversation: str, model: str):  # noqa: ARG001
        assert "sporty" in conversation.lower()
        return {
            "families": {
                "category": ["t-shirt"],
                "style": ["sporty"],
                "color_primary": ["grey"],
            }
        }

    monkeypatch.setattr(qp.openai_extractor, "extract_preferences", fake_extract_preferences)

    def fake_embed_text(client, text):  # noqa: ARG001
        return [0.31, 0.09, 0.05]

    monkeypatch.setattr(qp, "embed_text", fake_embed_text)

    import numpy as np
    from backend.app import image_features

    monkeypatch.setattr(
        image_features,
        "image_to_feature",
        lambda *_: np.zeros((512,), dtype=float),
    )

    monkeypatch.setenv("IMAGE_STORAGE_DIR", str(tmp_path / "imgs"))

    img_path = Path("design/images/test-blue-and-grey-shirts.jpg")
    assert img_path.exists(), "Design image missing for test"
    img_b64 = base64.b64encode(img_path.read_bytes()).decode()

    client = TestClient(app)
    resp = client.post(
        "/garments/ingest",
        json={
            "external_id": "calvin-grey-tee",
            "image_base64": img_b64,
            "attributes": {
                "category": ["t-shirt"],
                "style": ["sporty"],
                "color_primary": ["grey"],
            },
            "title": "Grey Calvin Klein Sporty T-Shirt",
            "brand": "Calvin Klein",
            "price": 39.0,
            "currency": "USD",
        },
    )
    assert resp.status_code == 200, resp.text
    gid = resp.json()["garment_id"]

    from backend.app.db_models import Garment
    from sqlalchemy.orm import Session

    db_url = os.getenv("DATABASE_URL")
    assert db_url is not None
    engine = create_engine(db_url, future=True)
    with Session(engine) as session:
        g = session.get(Garment, gid)
        assert g is not None, "Garment missing after ingest"
        g.description = "Minimalist grey sporty Calvin Klein branded t-shirt"
        g.description_embedding = [0.32, 0.085, 0.052]
        session.commit()

    search_resp = client.post(
        "/search",
        json={"query": CONVERSATION, "user_id": "user_conv"},
    )
    assert search_resp.status_code == 200, search_resp.text
    results = search_resp.json()["results"]
    assert results, "Expected at least one result"
    top = results[0]
    assert top["garment_id"] == gid, f"Expected grey tee garment first, got {top}"
    expl = top["explanation"]
    assert "attribute_overlap" in expl["components"]
    assert "text_similarity" in expl["components"]
