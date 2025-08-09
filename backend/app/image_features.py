"""Image feature extraction using a pretrained ResNet (torchvision)."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

PREPROCESS = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


@lru_cache(maxsize=1)
def _resnet() -> tuple[nn.Module, int]:
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.eval()
    # Remove final classification layer -> use penultimate layer features
    feature_dim = model.fc.in_features  # type: ignore[attr-defined]
    model.fc = nn.Identity()  # type: ignore[assignment]
    return model, feature_dim


def image_to_feature(path: str, device: str = "cpu") -> np.ndarray:
    model, _ = _resnet()
    img = Image.open(path).convert("RGB")
    tensor = PREPROCESS(img).unsqueeze(0)
    if device != "cpu":
        tensor = tensor.to(device)
        model.to(device)
    with torch.no_grad():
        feats = model(tensor)
    arr = feats.cpu().numpy().astype("float32")[0]
    # L2 normalize
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr
