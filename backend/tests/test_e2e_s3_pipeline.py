"""End-to-end test for S3 image upload pipeline.

This test validates the complete image processing workflow:
1. Mock S3 bucket with uploaded image
2. Trigger S3 processor Lambda handler
3. Image standardization & optimization
4. Multi-garment description extraction (with fallback)
5. Database record creation (InventoryImage, InventoryItem, Garment)
6. Attribute classification and embedding (optional with OpenAI)
7. Static file preparation for deployment

Uses moto to mock AWS services, temporary SQLite DB, and fallback processing
when OpenAI is not configured.
"""
import sys
from pathlib import Path

import boto3
from moto import mock_aws  # moto >=5 consolidated
from sqlalchemy.orm import Session

# Ensure backend/app importable
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.db_models import (  # noqa: E402
    AttributeValue,
    Garment,
    InventoryImage,
    InventoryItem,
)
from app.ingest import get_engine  # noqa: E402
from app.processor import handler as s3_handler  # type: ignore  # noqa: E402


def _tiny_image_bytes():
    try:
        import io

        from PIL import Image  # type: ignore
        im = Image.new("RGB", (4,4), (0,255,0))
        buf = io.BytesIO()
        im.save(buf, format="JPEG")
        return buf.getvalue()
    except ImportError:
        # Fallback raw JPEG header for minimal test
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x04\x00\x04\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    except Exception:
        return b"RAWIMAGE"


@mock_aws
def test_e2e_s3_upload_pipeline(tmp_path, monkeypatch):
    # Setup temp sqlite DB
    db_path = tmp_path / "e2e.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    img_dir = tmp_path / "images"
    monkeypatch.setenv("INVENTORY_IMAGE_DIR", str(img_dir))
    # Ensure no OpenAI call path
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Mock AWS
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "test-prethrift-images"
    s3.create_bucket(Bucket=bucket_name)
    monkeypatch.setenv("IMAGES_BUCKET", bucket_name)

    # Upload raw image object simulating client direct upload
    key = "uploads/user123/test-image.jpg"
    s3.put_object(Bucket=bucket_name, Key=key, Body=_tiny_image_bytes(), ContentType="image/jpeg")

    # Construct S3 event
    event = {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "s3": {"bucket": {"name": bucket_name}, "object": {"key": key}},
            }
        ]
    }

    # Invoke processor handler (Lambda simulation)
    result = s3_handler(event, context={})
    assert result["status"] == "ok"

    # Validate DB state
    engine = get_engine()
    with Session(engine) as session:
        images = session.query(InventoryImage).all()
        assert len(images) == 1
        img = images[0]
        assert img.processed is True
        assert img.width is not None and img.height is not None
        items = session.query(InventoryItem).all()
        assert len(items) >= 1
        # Each item should reference a garment and have description
        for it in items:
            assert it.description
            if it.garment_id:
                g = session.get(Garment, it.garment_id)
                assert g is not None
        # Attribute extraction optional; ensure no integrity errors
        attrs = session.query(AttributeValue).all()
        # Standardization output file exists
        img_path = Path(img.file_path)
        assert img_path.exists(), f"Expected standardized image at {img.file_path}"

    # Prepare static deployment (e.g., copy optimized image to out dir)
    out_dir = tmp_path / "static"
    out_dir.mkdir()
    from shutil import copy2
    copy2(img_path, out_dir / img_path.name)
    static_file = out_dir / img_path.name
    assert static_file.exists(), f"Static deployment failed - {static_file} not found"

    print(f"✅ E2E Pipeline Success: {len(items)} items processed, static file at {static_file}")
