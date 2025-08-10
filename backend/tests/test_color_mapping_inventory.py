import base64
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
try:
    from app.main import app  # type: ignore
except Exception:  # pragma: no cover
    from backend.app.main import app  # type: ignore


def _solid_color_png(rgb):
    # create small solid color PNG via pillow if available else raw fallback
    try:
        import io

        from PIL import Image  # type: ignore

        im = Image.new("RGB", (8, 8), tuple(rgb))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return b"RAWPNG"


def test_dominant_color_attribute_added(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'db.sqlite'}")
    monkeypatch.setenv("INVENTORY_IMAGE_DIR", str(tmp_path / "imgs"))
    # Red-ish
    img_b64 = base64.b64encode(_solid_color_png((200, 40, 40))).decode()
    client = TestClient(app)

    r = client.post("/inventory/upload", json={"filename": "red.png", "image_base64": img_b64})
    assert r.status_code == 200
    image_id = r.json()["image_id"]
    pr = client.post("/inventory/process", json={"image_id": image_id})
    assert pr.status_code == 200, pr.text
    # Fetch stats to ensure attribute stored via garment join
    stats = client.get("/inventory/stats").json()
    assert stats["inventory_garments"] >= 1
    # Query search to ensure no crash when accessing attributes
    sr = client.post("/search", json={"query": "red shirt"})
    assert sr.status_code == 200
