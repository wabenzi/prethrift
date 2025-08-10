import base64

import numpy as np
from backend.app.main import app
from fastapi.testclient import TestClient


def _fake_png_bytes() -> bytes:
    # Minimal 1x1 transparent PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBgQYch58AAAAASUVORK5CYII="
    )


def test_ingest_requires_image():
    client = TestClient(app)
    resp = client.post("/garments/ingest", json={"external_id": "x", "image_base64": ""})
    assert resp.status_code == 400


def test_ingest_success(monkeypatch, tmp_path):
    client = TestClient(app)

    # Provide lightweight fake image_to_feature to bypass heavy torch import
    from backend.app import image_features

    monkeypatch.setattr(
        image_features,
        "image_to_feature",
        lambda *_args, **_kw: np.zeros((512,), dtype=float),
    )

    # Direct image storage to tmp
    monkeypatch.setenv("IMAGE_STORAGE_DIR", str(tmp_path / "imgs"))

    img_b64 = base64.b64encode(_fake_png_bytes()).decode()
    resp = client.post(
        "/garments/ingest",
        json={
            "external_id": "gar123",
            "image_base64": img_b64,
            "attributes": {"color_primary": ["Blue"], "category": ["Shirts"]},
            "title": "Blue Shirt",
            "brand": "TestBrand",
            "price": 19.99,
            "currency": "USD",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["external_id"] == "gar123"
    assert isinstance(data["garment_id"], int)

    # Re-ingest should return same id (idempotency)
    resp2 = client.post(
        "/garments/ingest",
        json={"external_id": "gar123", "image_base64": img_b64},
    )
    assert resp2.status_code == 200
    assert resp2.json()["garment_id"] == data["garment_id"]
