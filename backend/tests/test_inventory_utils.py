import base64
import tempfile
from pathlib import Path

from backend.app.db_models import AttributeValue, Base, Garment, GarmentAttribute
from backend.app.inventory_utils import persist_inventory_image_file, safe_add_garment_attribute
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_persist_inventory_image_file(tmp_path, monkeypatch):
    # Create sample bytes
    data = b"test-bytes"
    b64 = base64.b64encode(data).decode()
    monkeypatch.setenv("INVENTORY_IMAGE_DIR", str(tmp_path / "inv"))
    out_path = persist_inventory_image_file("sample.png", b64)
    p = Path(out_path)
    assert p.exists()
    assert p.read_bytes() == data
    # Ensure digest prefix present
    assert p.name.endswith("-sample.png")
    assert len(p.name.split("-")[0]) == 12


def test_safe_add_garment_attribute_idempotent():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        url = f"sqlite:///{tmp.name}"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        av = AttributeValue(family="color", value="black")
        g = Garment(external_id="g1")
        session.add_all([av, g])
        session.commit()
        safe_add_garment_attribute(session, g.id, av.id, 0.9)
        safe_add_garment_attribute(session, g.id, av.id, 0.8)  # duplicate should not raise
        session.commit()
        attrs = session.query(GarmentAttribute).all()
        assert len(attrs) == 1
        assert attrs[0].confidence == 0.9  # original preserved
