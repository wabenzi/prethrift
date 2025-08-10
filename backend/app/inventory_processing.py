"""Inventory image processing helpers.

Centralizes image persistence, optimization, color statistics, and multi-garment
description prompting previously scattered across modules.
"""

from __future__ import annotations

import base64 as _b64
import hashlib
import json as _json
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .describe_images import describe_image
from .ontology import families as ontology_families


def persist_raw_image(filename: str, image_b64: str) -> str:
    """Persist base64 image to disk under INVENTORY_IMAGE_DIR with hash prefix."""
    storage_dir = os.getenv("INVENTORY_IMAGE_DIR", "data/inventory")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)
    try:
        raw = _b64.b64decode(image_b64, validate=True)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid base64: {e}") from e
    digest = hashlib.sha1(raw).hexdigest()[:12]
    out = Path(storage_dir) / f"{digest}-{filename}"
    out.write_bytes(raw)
    return str(out)


def standardize_and_optimize(path: str) -> tuple[str, int, int, str]:
    """Resize & convert image to optimized JPEG; returns (path, w, h, fmt)."""
    from PIL import Image

    max_dim = int(os.getenv("INVENTORY_MAX_DIM", "1024"))
    p = Path(path)
    with Image.open(p) as im:
        im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            im = im.resize((int(w * scale), int(h * scale)))
            w, h = im.size
        optimized_path = p.with_suffix(".jpg")
        im.save(optimized_path, format="JPEG", quality=88, optimize=True)
        return str(optimized_path), w, h, "jpg"


def multi_garment_prompt(ontology_families_list: list[str] | None = None) -> str:
    fams = ", ".join(sorted(ontology_families_list or ontology_families()))
    parts = [
        "You are a fashion product extraction assistant.",
        "Analyze the image and output JSON with key 'garments' whose value is an array.",
        "Each element must describe ONE garment (ignore people, faces, background, props).",
        "If garments overlap (e.g., top + pants) produce one entry per distinct garment type.",
        "Fields: index (int, from 0), description (120-180 words, factual, exclude people/bg),",
        "key_attributes (object mapping ontology families you can infer to candidate values).",
        f"Ontology families: {fams}.",
        "Include only confident families. Do NOT fabricate brand names.",
    "Return ONLY valid JSON.",
    ]
    return " ".join(parts)


def describe_inventory_image_multi(client, path: str, model: str | None) -> list[dict[str, Any]]:
    """Obtain structured multi-garment description from model; fallback to single description."""
    if not client or "OPENAI_API_KEY" not in os.environ:
        p = Path(path)
        return [
            {
                "index": 0,
                "description": f"Placeholder description for {p.name}.",
                "key_attributes": {},
            }
        ]
    p = Path(path)
    data_uri = (
        f"data:image/{p.suffix.lstrip('.').lower()};base64,"
        + _b64.b64encode(p.read_bytes()).decode()
    )
    prompt = multi_garment_prompt()
    try:
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract structured garments."},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                },
            ],
            temperature=0.2,
        )
        content = getattr(resp.choices[0].message, "content", None)
        if isinstance(content, str):
            try:
                parsed = _json.loads(content)
                if isinstance(parsed, dict) and isinstance(parsed.get("garments"), list):
                    out: list[dict[str, Any]] = []
                    for g in parsed["garments"]:
                        if not isinstance(g, dict):
                            continue
                        idx = g.get("index") if isinstance(g.get("index"), int) else len(out)
                        desc = str(g.get("description") or "").strip()
                        if not desc:
                            continue
                        key_attrs = (
                            g.get("key_attributes")
                            if isinstance(g.get("key_attributes"), dict)
                            else {}
                        )
                        out.append(
                            {
                                "index": idx,
                                "description": desc,
                                "key_attributes": key_attrs,
                            }
                        )
                    if out:
                        for i, g in enumerate(out):
                            g["index"] = i
                        return out
            except Exception:  # noqa: BLE001
                pass
        # fallback single
        single = describe_image(client, p, model or "gpt-4o-mini")
        return [{"index": 0, "description": single, "key_attributes": {}}]
    except Exception:  # noqa: BLE001
        return [
            {
                "index": 0,
                "description": f"Fallback description for {p.name}.",
                "key_attributes": {},
            }
        ]


def color_stats(path: str) -> dict[str, Any]:
    """Compute mean RGB + small KMeans (adaptive) cluster summary for an image."""
    import numpy as _np
    from PIL import Image as _Image

    try:
        with _Image.open(path) as im:
            im = im.convert("RGB")
            arr = _np.array(im)
            if arr.shape[0] * arr.shape[1] > 400_000:
                arr = arr[::2, ::2, :]
            flat = arr.reshape(-1, 3)
            mean = flat.mean(axis=0).tolist()
            from sklearn.cluster import KMeans  # type: ignore[import-untyped]

            sample = flat[_np.random.choice(flat.shape[0], min(5000, flat.shape[0]), replace=False)]
            uniq = _np.unique(sample, axis=0)
            k = min(3, uniq.shape[0])
            if k >= 2:
                km = KMeans(n_clusters=k, n_init=3, random_state=42)
                km.fit(sample)
                centers = km.cluster_centers_.tolist()
                import numpy as _np2

                counts = _np2.bincount(km.labels_, minlength=k).astype(float)
                weights = (counts / counts.sum()).round(4).tolist()
            else:
                centers = [uniq[0].astype(float).tolist()] if uniq.shape[0] == 1 else []
                weights = [1.0] if centers else []
                k = len(centers)
            return {
                "mean_rgb": [round(float(x), 2) for x in mean],
                "clusters": centers,
                "cluster_count": k,
                "cluster_weights": weights,
            }
    except Exception:  # noqa: BLE001
        return {}
