import base64
import math
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

try:  # allow import when executed inside backend directory or repo root
    from app.db_models import Garment
    from app.main import app  # type: ignore
except Exception:  # pragma: no cover
    from backend.app.db_models import Garment  # type: ignore
    from backend.app.main import app  # type: ignore


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or not os.getenv("RUN_OPENAI_E2E"),
    reason="Requires real OpenAI key and RUN_OPENAI_E2E=1 to run",
)
def test_e2e_openai_search_ranks_target_image_first():
    """End-to-end test using ONLY image-derived attributes + descriptions.

    Steps:
      1. Ingest images with no manual attributes.
      2. Generate description + embedding + inferred attributes for each.
      3. Clear embedding caches.
      4. Submit natural language query and assert target ranks first.
    """
    # Guard inside test too (pytest skip marker should handle but be defensive)
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("RUN_OPENAI_E2E"):
        pytest.skip("Missing OPENAI_API_KEY or RUN_OPENAI_E2E")
    # Ephemeral DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"

    client = TestClient(app)

    def _ingest_image(external_id: str, file_name: str) -> int:
        img_path = Path("design/images") / file_name
        assert img_path.exists(), f"Missing image {file_name}"
        img_b64 = base64.b64encode(img_path.read_bytes()).decode()
        resp = client.post(
            "/garments/ingest",
            json={"external_id": external_id, "image_base64": img_b64},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["garment_id"]

    gid_band = _ingest_image("queen-band-tee", "queen-tshirt.jpeg")
    _ingest_image("orange-dress", "orange-pattern-dress.jpeg")
    _ingest_image("baggy-jeans", "baggy-jeans.jpeg")

    # Refresh descriptions for ALL garments (primary + distractors)
    all_ids = []
    # We just set DATABASE_URL above; use direct access to satisfy type checker
    db_url = os.environ["DATABASE_URL"]
    engine = create_engine(db_url, future=True)
    with Session(engine) as session:
        all_ids = [g.id for g in session.query(Garment).all()]
    for gid in all_ids:
        resp = client.post(
            "/user/garments/refresh-description",
            json={"garment_id": gid, "overwrite": True},
        )
        assert resp.status_code == 200, resp.text
        desc = resp.json()["description"]
        assert desc, "Description missing"
        print(f"REFRESH gid={gid} len={len(desc)} desc={desc[:120]!r}")

    # After refresh, capture descriptions for verification
    with Session(engine) as session:
        garments = session.query(Garment).all()
        desc_map = {g.id: g.description or "" for g in garments}
        # Gather inferred attribute summary
        attr_summary: dict[int, dict[str, list[str]]] = {}
        for g in garments:
            fam_map: dict[str, list[str]] = {}
            for ga in g.attributes:
                fam = ga.attribute.family
                val = ga.attribute.value
                fam_map.setdefault(fam, [])
                if val not in fam_map[fam]:
                    fam_map[fam].append(val)
            attr_summary[g.id] = fam_map
        for gid, fam_map in attr_summary.items():
            print(f"ATTR gid={gid} -> {fam_map}")
        # Assert ontology-driven inference produced key families for target
        target_attrs = attr_summary[gid_band]
        assert any(fam in target_attrs for fam in ("category", "pattern", "style")), target_attrs
        # Ensure at least 2 distinct families inferred for target
        assert len(target_attrs.keys()) >= 2, target_attrs
    # Basic sanity: all descriptions non-empty
    assert all(desc_map[g] for g in all_ids)
    # Target should mention queen or band
    tgt_desc_l = desc_map[gid_band].lower()
    assert ("queen" in tgt_desc_l) or ("band" in tgt_desc_l), tgt_desc_l

    cache_clear = client.post("/admin/cache/clear")
    assert cache_clear.status_code == 200

    query_text = "I'm hunting for a vintage band t-shirt, something rock, graphic, and worn."
    search_resp = client.post("/search", json={"query": query_text})
    assert search_resp.status_code == 200, search_resp.text
    data = search_resp.json()
    assert data["results"], "No results returned"
    # Compute softmax probabilities over scores
    scores = [r["score"] for r in data["results"]]
    max_s = max(scores)
    exp_scores = [math.exp(s - max_s) for s in scores]
    total = sum(exp_scores)
    probs = [e / total for e in exp_scores]
    # Log ranking details
    for idx, (r, p) in enumerate(zip(data["results"], probs), start=1):
        rid = r["garment_id"]
        desc_l = (r.get("description") or "").lower()
        print(
            "RANK {idx} gid={gid} score={score:.4f} prob={prob:.3f} "
            "queen={has_q} band={has_b}".format(
                idx=idx,
                gid=rid,
                score=r["score"],
                prob=p,
                has_q="queen" in desc_l,
                has_b="band" in desc_l,
            )
        )
    top = data["results"][0]
    text_blob = (top.get("title") or "") + " " + (top.get("description") or "")
    # Stricter: top must be target AND contain at least one key token
    assert top["garment_id"] == gid_band, (
        top,
        [(r["garment_id"], r["score"]) for r in data["results"][:3]],
    )
    assert ("queen" in text_blob.lower()) or ("band" in text_blob.lower())
    # Ensure a reasonable winning margin if there is more than one result
    if len(data["results"]) > 1:
        second = data["results"][1]
        score_margin = top["score"] - second["score"]
        prob_margin = probs[0] - probs[1]
        print(
            "MARGINS: score_margin={sm:.4f} prob_margin={pm:.3f} "
            "top_score={ts:.4f} second_score={ss:.4f}".format(
                sm=score_margin,
                pm=prob_margin,
                ts=top["score"],
                ss=second["score"],
            )
        )
        assert score_margin > 0, "Top score not strictly greater than second"
        # Soft margin thresholds (avoid flakiness on model drift but still assert separation)
        assert prob_margin >= 0.02 or score_margin >= 0.01, (
            "Insufficient separation between top 2 results",
            score_margin,
            prob_margin,
        )
    # Ensure distractors (if their descriptions exist) don't both outperform containing both tokens
    for r in data["results"][1:]:
        d_l = (r.get("description") or "").lower()
        assert not ("queen" in d_l and "band" in d_l), d_l

    # Secondary query incorporating color/style tokens to exercise attribute overlap
    secondary_query = "vintage beige graphic band tee"
    search_resp2 = client.post("/search", json={"query": secondary_query})
    assert search_resp2.status_code == 200
    data2 = search_resp2.json()
    assert data2["results"], "No results second query"
    top2 = data2["results"][0]
    print("SECOND QUERY TOP", top2["garment_id"], top2.get("description", "")[:100])
    # Expect target still top given overlapping tokens
    assert top2["garment_id"] == gid_band

    # Ablation: remove pattern/style attributes for target and ensure score on secondary query drops
    with Session(engine) as session:
        t = session.get(Garment, gid_band)
        removed_ids: list[int] = []
        if t is not None:
            for ga in list(t.attributes):
                fam = ga.attribute.family
                if fam in {"pattern", "style"}:
                    removed_ids.append(ga.id)
                    session.delete(ga)
            session.commit()
    if removed_ids:  # only perform comparison if we actually removed something
        cache_clear2 = client.post("/admin/cache/clear")
        assert cache_clear2.status_code == 200
        search_resp3 = client.post("/search", json={"query": secondary_query})
        assert search_resp3.status_code == 200
        data3 = search_resp3.json()
        # Find target result scores pre/post
        orig_score = next(r["score"] for r in data2["results"] if r["garment_id"] == gid_band)
        new_score = next(r["score"] for r in data3["results"] if r["garment_id"] == gid_band)
        print(
            f"ABLATION removed={len(removed_ids)} "
            f"score_before={orig_score:.4f} after={new_score:.4f}"
        )
        # Assert score decreased or stayed (should not improve after removing helpful attrs)
        assert new_score <= orig_score + 1e-6
