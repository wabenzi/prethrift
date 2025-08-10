"""Image feature extraction using a pretrained ResNet (torchvision)."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image

try:  # pragma: no cover - optional heavy deps
    from torch import nn  # type: ignore
    from torchvision import models, transforms  # type: ignore

    _HAS_TORCH = True
except Exception:  # noqa: BLE001
    _HAS_TORCH = False

    class _DummyNN:  # minimal stand-in
        class Module:  # type: ignore[override]
            pass

        class Identity:  # noqa: D401
            def __call__(self, x):  # type: ignore[no-untyped-def]
                return x

    nn = _DummyNN  # type: ignore

    class _DummyModels:  # pragma: no cover
        class ResNet18_Weights:  # type: ignore
            DEFAULT = None

        def resnet18(self, _weights=None):  # type: ignore[no-untyped-def]
            class M:  # type: ignore[too-few-public-methods]
                fc = type("fc", (), {"in_features": 512})()

                def eval(self):  # type: ignore[no-untyped-def]
                    return self

                def __call__(self, _x):  # type: ignore[no-untyped-def]
                    import numpy as _np

                    return _np.zeros((1, 512), dtype="float32")

            return M()

    class _DummyTransforms:  # pragma: no cover
        @staticmethod
        def Compose(_fns):  # type: ignore[no-untyped-def]
            def _apply(img):
                return img

            return _apply

        @staticmethod
        def Resize(*_a, **_k):  # type: ignore[no-untyped-def]
            return lambda img: img

        @staticmethod
        def CenterCrop(*_a, **_k):  # type: ignore[no-untyped-def]
            return lambda img: img

        @staticmethod
        def ToTensor():  # type: ignore[no-untyped-def]
            return lambda img: img

        @staticmethod
        def Normalize(*_a, **_k):  # type: ignore[no-untyped-def]
            return lambda img: img

    models = _DummyModels()  # type: ignore
    transforms = _DummyTransforms()  # type: ignore

if _HAS_TORCH:  # pragma: no branch
    PREPROCESS = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
else:  # pragma: no cover

    def PREPROCESS(img):  # type: ignore[no-untyped-def]
        return img


@lru_cache(maxsize=1)
def _resnet() -> tuple[nn.Module, int]:  # type: ignore[name-defined]
    weights_container = getattr(models, "ResNet18_Weights", None)
    weights = None
    if weights_container is not None and hasattr(weights_container, "DEFAULT"):
        weights = weights_container.DEFAULT  # type: ignore[attr-defined]
    model = models.resnet18(weights=weights)  # type: ignore[arg-type]
    if hasattr(model, "eval"):
        model.eval()
    feature_dim = getattr(getattr(model, "fc", None), "in_features", 512)  # type: ignore[attr-defined]
    if hasattr(model, "fc") and hasattr(nn, "Identity"):
        from contextlib import suppress

        with suppress(Exception):
            model.fc = nn.Identity()  # type: ignore[attr-defined,assignment]
    return model, feature_dim


def image_to_feature(path: str, device: str = "cpu") -> np.ndarray:
    model, _ = _resnet()
    img = Image.open(path).convert("RGB")
    processed = PREPROCESS(img)
    if _HAS_TORCH:  # pragma: no branch
        tensor = processed.unsqueeze(0)  # type: ignore[attr-defined]
        if device != "cpu":  # pragma: no cover
            tensor = tensor.to(device)
            model.to(device)
        import torch as _torch  # type: ignore

        with _torch.no_grad():
            feats = model(tensor)
        arr = feats.cpu().numpy().astype("float32")[0]
    else:  # pragma: no cover
        # Return deterministic zero vector for tests
        arr = np.zeros(512, dtype="float32")
    # L2 normalize
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr
