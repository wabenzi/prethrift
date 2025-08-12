"""Test local computer vision garment analysis."""

import os
import sys
import tempfile
from pathlib import Path

# Ensure backend/app importable
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))


def _create_test_image():
    """Create a simple test image for testing."""
    try:
        import io

        from PIL import Image  # type: ignore

        # Create a simple colored rectangle that might look like clothing
        im = Image.new("RGB", (224, 224), (70, 130, 180))  # Steel blue
        # Add some texture/pattern
        for x in range(0, 224, 20):
            for y in range(0, 224, 20):
                if (x + y) % 40 == 0:
                    im.putpixel((x, y), (255, 255, 255))
        return im
    except ImportError:
        return None


def test_local_cv_analyzer(tmp_path, monkeypatch):
    """Test local CV analyzer with and without dependencies."""
    monkeypatch.setenv("USE_LOCAL_CV", "true")

    # Create test image
    img_path = tmp_path / "test_shirt.jpg"
    test_img = _create_test_image()
    if test_img:
        test_img.save(img_path, "JPEG")
    else:
        # Create dummy file if PIL not available
        img_path.write_bytes(b"dummy_image_data")

    try:
        from app.local_cv import analyze_garments_local, get_local_analyzer

        # Test analyzer availability
        analyzer = get_local_analyzer()
        if analyzer is None:
            print("CLIP not available, testing fallback")
            results = analyze_garments_local(str(img_path))
            assert len(results) == 1
            assert "not available" in results[0]["description"]
            return

        # Test actual analysis if CLIP available
        results = analyze_garments_local(str(img_path))
        assert len(results) >= 1
        assert isinstance(results[0]["description"], str)
        assert isinstance(results[0]["key_attributes"], dict)
        assert "confidence" in results[0]
        print(f"Local CV analysis result: {results[0]['description']}")

    except ImportError:
        print("Local CV module not available (expected if CLIP not installed)")
        # Test that inventory processing handles this gracefully
        from app.inventory_processing import describe_inventory_image_multi

        results = describe_inventory_image_multi(None, str(img_path), None)
        assert len(results) == 1
        assert "Placeholder description" in results[0]["description"]


def test_inventory_processing_local_cv_integration(tmp_path, monkeypatch):
    """Test that inventory processing correctly uses local CV when configured."""
    monkeypatch.setenv("USE_LOCAL_CV", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    img_path = tmp_path / "test_garment.jpg"
    test_img = _create_test_image()
    if test_img:
        test_img.save(img_path, "JPEG")
    else:
        img_path.write_bytes(b"dummy_image_data")

    from app.inventory_processing import describe_inventory_image_multi

    # Should attempt local CV first
    results = describe_inventory_image_multi(None, str(img_path), None)
    assert len(results) >= 1
    assert isinstance(results[0]["description"], str)

    # Test fallback to OpenAI path when local CV disabled
    monkeypatch.setenv("USE_LOCAL_CV", "false")
    results = describe_inventory_image_multi(None, str(img_path), None)
    assert len(results) == 1
    assert "Placeholder description" in results[0]["description"]


if __name__ == "__main__":
    # Quick manual test
    import tempfile

    class MockMonkeypatch:
        def __init__(self):
            self._env = {}

        def setenv(self, key, value):
            self._env[key] = value
            os.environ[key] = value

        def delenv(self, key, raising=True):
            if key in os.environ:
                del os.environ[key]

    with tempfile.TemporaryDirectory() as tmp:
        mp = MockMonkeypatch()
        test_local_cv_analyzer(Path(tmp), mp)
        test_inventory_processing_local_cv_integration(Path(tmp), mp)
        print("✅ Local CV tests completed")
