import base64
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure backend/app importable when running pytest from repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # type: ignore  # noqa: E402


def _tiny_image_bytes() -> bytes:
    # 2x2 red jpeg
    try:  # optional pillow
        import io

        from PIL import Image  # type: ignore

        im = Image.new("RGB", (2, 2), (255, 0, 0))
        buf = io.BytesIO()
        im.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception:
        return b"RAWIMAGE"


def test_inventory_upload_and_process(tmp_path, monkeypatch):
    # ensure database points to temp sqlite
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("INVENTORY_IMAGE_DIR", str(tmp_path / "images"))
    # Use no OPENAI key so processing uses fallback deterministic paths
    if "OPENAI_API_KEY" in os.environ:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = TestClient(app)

    img_b64 = base64.b64encode(_tiny_image_bytes()).decode()
    r = client.post("/inventory/upload", json={"filename": "red.jpg", "image_base64": img_b64})
    assert r.status_code == 200, r.text
    image_id = r.json()["image_id"]

    # process
    pr = client.post("/inventory/process", json={"image_id": image_id})
    assert pr.status_code == 200, pr.text
    data = pr.json()
    assert data["processed_count"] >= 1
    item = data["items"][0]
    assert item["image_id"] == image_id
    assert item["description_len"] > 0

    # stats endpoint should reflect counts
    stats = client.get("/inventory/stats").json()
    assert stats["total_images"] >= 1
    assert stats["processed_images"] >= 1
    assert stats["total_items"] >= 1

    # listing endpoints
    imgs = client.get("/inventory/images").json()
    assert imgs["count"] >= 1
    items = client.get("/inventory/items").json()
    assert items["count"] >= 1
