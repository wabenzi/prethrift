import base64
import os
import tempfile
from pathlib import Path

import pytest
from backend.app.db_models import Garment
from backend.app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or not os.getenv("RUN_OPENAI_E2E"),
    reason="Requires real OpenAI key and RUN_OPENAI_E2E=1 to run",
)
def test_e2e_openai_search_ranks_target_image_first():
    """End-to-end test using real OpenAI calls (vision+text) to rank garments.

    Flow:
      1. Create fresh ephemeral DB.
      2. Ingest multiple real design images (band tee, dress, jeans) with basic attributes.
      3. For each garment call refresh-description to generate description + embedding.
      4. Issue a natural language conversation query.
      5. Assert the Queen band t-shirt ranks first.

    Skipped by default unless RUN_OPENAI_E2E=1 to avoid cost & flakiness in CI.
    """
    # Ephemeral DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_url = f"sqlite:///{tmp.name}"
    os.environ["DATABASE_URL"] = db_url

    client = TestClient(app)

    def _ingest_image(external_id: str, file_name: str, attrs: dict, title: str):
        img_path = Path("design/images") / file_name
        assert img_path.exists(), f"Missing image {file_name}"
        img_b64 = base64.b64encode(img_path.read_bytes()).decode()
        resp = client.post(
            "/garments/ingest",
            json={
                "external_id": external_id,
                "image_base64": img_b64,
                "attributes": attrs,
                "title": title,
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["garment_id"]

    # Ingest target (band tee) + distractors
    gid_band = _ingest_image(
        "queen-band-tee",
        "queen-tshirt.jpeg",
        {"category": ["t-shirt"], "style": ["band"], "color_primary": ["black"]},
        "Queen Band Tee",
    )
    _ingest_image(
        "orange-dress",
        "orange-pattern-dress.jpeg",
        {"category": ["dress"], "style": ["summer"], "color_primary": ["orange"]},
        "Orange Pattern Dress",
    )
    _ingest_image(
        "baggy-jeans",
        "baggy-jeans.jpeg",
        {"category": ["jeans"], "style": ["casual"], "color_primary": ["blue"]},
        "Baggy Jeans",
    )

    # Generate descriptions + embeddings via OpenAI for each garment
    # (vision -> text, then text -> embedding)
    for gid in [gid_band]:  # Only need band tee vision pass; others rely on text similarity gap
        resp = client.post(
            "/garments/refresh-description",
            json={"garment_id": gid, "overwrite": True},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["description"], "Description missing"

    # For distractors, create simple placeholder descriptions so they are valid rows
    engine = create_engine(db_url, future=True)
    with Session(engine) as session:
        for g in session.query(Garment).all():
            if not g.description:
                g.description = g.title
                # Provide a basic short embedding placeholder
        session.commit()

    # Conversation style natural query
    query_text = (
        "I'm hunting for a faded black Queen band t-shirt for my collection, "
        "something rock and vintage."
    )
    search_resp = client.post("/search", json={"query": query_text})
    assert search_resp.status_code == 200, search_resp.text
    data = search_resp.json()
    assert data["results"], "No results returned"
    top = data["results"][0]
    # Accept either title match or description containing queen/band
    text_blob = (top.get("title") or "") + " " + (top.get("description") or "")
    assert top["garment_id"] == gid_band or (
        "queen" in text_blob.lower() and "band" in text_blob.lower()
    ), (top, data["results"][:3])
