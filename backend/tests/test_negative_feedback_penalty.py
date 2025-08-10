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
    """Seed two garments so one can be disliked and penalty observed on re-rank."""
    with Session(engine) as session:
        av_color_black = AttributeValue(family="color", value="black")
        av_style_band = AttributeValue(family="style", value="band")
        session.add_all([av_color_black, av_style_band])
        session.flush()
        g1 = Garment(
            external_id="g-like",
            title="Black Band Tee",
            description="Black band graphic tee",
            description_embedding=[0.2, 0.1, 0.05],
        )
        g2 = Garment(
            external_id="g-dislike",
            title="Black Band Hoodie",
            description="Black band graphic hoodie",
            description_embedding=[0.19, 0.11, 0.045],
        )
        session.add_all([g1, g2])
        session.flush()
        # attach same attributes so text/profile effects dominate penalty difference
        for g in (g1, g2):
            session.add_all(
                [
                    GarmentAttribute(
                        garment_id=g.id,
                        attribute_value_id=av_color_black.id,
                        confidence=1.0,
                    ),
                    GarmentAttribute(
                        garment_id=g.id,
                        attribute_value_id=av_style_band.id,
                        confidence=1.0,
                    ),
                ]
            )
        session.commit()
        return g1.id, g2.id


def test_dislike_adds_negative_penalty(monkeypatch):
    engine = setup_env(monkeypatch)
    gid_like, gid_dislike = seed(engine)

    from backend.app import query_pipeline as qp

    # Stable embedding for query that matches both garments roughly equally
    def fake_embed_text(client, text):  # noqa: ARG001
        return [0.205, 0.105, 0.048]

    def fake_extract_preferences(conversation: str, model: str):  # noqa: ARG001
        return {"families": {"color": ["black"], "style": ["band"]}}

    monkeypatch.setattr(qp, "embed_text", fake_embed_text)
    monkeypatch.setattr(
        qp.openai_extractor,
        "extract_preferences",
        fake_extract_preferences,
    )

    c = TestClient(app)

    # Initial search (no negative profile yet)
    r1 = c.post("/search", json={"query": "black band top", "user_id": "u_neg"})
    assert r1.status_code == 200
    results_initial = {r["garment_id"]: r for r in r1.json()["results"]}
    score_before = results_initial[gid_dislike]["score"]

    # Dislike one garment
    fb = c.post(
        "/feedback",
        json={"user_id": "u_neg", "garment_id": gid_dislike, "action": "dislike"},
    )
    assert fb.status_code == 200

    # Re-run search; disliked garment should now have lower score
    r2 = c.post("/search", json={"query": "black band top", "user_id": "u_neg"})
    assert r2.status_code == 200
    results_after = {r["garment_id"]: r for r in r2.json()["results"]}
    score_after = results_after[gid_dislike]["score"]

    assert score_after < score_before, (score_before, score_after)
    # Ensure penalty component registered
    explanation = results_after[gid_dislike]["explanation"]
    assert explanation["components"]["negative_profile_penalty"] >= 0
    assert explanation["contributions"]["negative_profile_penalty"] <= 0
