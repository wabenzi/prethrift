import json
from pathlib import Path

import numpy as np
import pytest
from backend.app.image_features import image_to_feature

IMAGES_DIR = Path(__file__).resolve().parents[2] / "design" / "images"
OUTPUT_FILE = (
    Path(__file__).resolve().parents[2] / "design" / "images" / "_features_test_output.json"
)


def _collect_images():
    exts = {".jpg", ".jpeg", ".png"}
    return sorted([p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in exts])


@pytest.mark.integration
@pytest.mark.skipif(not IMAGES_DIR.exists(), reason="images directory missing")
def test_extract_and_persist_image_features():
    images = _collect_images()
    assert images, "No images found for integration test"

    features_dict: dict[str, list[float]] = {}
    for img_path in images:
        vec = image_to_feature(str(img_path))
        assert isinstance(vec, np.ndarray)
        assert vec.shape[0] == 512  # expected embedding size (dummy or real)
        # Store only first few components now (rest will be filled later if needed)
        features_dict[img_path.name] = vec[:16].tolist()

    with OUTPUT_FILE.open("w") as f:
        json.dump(features_dict, f, indent=2)

    assert OUTPUT_FILE.exists()
    # Minimal shape validation of stored data
    stored = json.loads(OUTPUT_FILE.read_text())
    for _name, partial_vec in stored.items():
        assert isinstance(partial_vec, list)
        assert len(partial_vec) == 16
        assert all(isinstance(x, float) for x in partial_vec)
