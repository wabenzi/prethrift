"""Generate detailed garment descriptions for images using OpenAI vision-capable model.

Usage:
  python -m backend.app.describe_images \
      --images-dir design/images \
      --out-dir design/text \
      --model gpt-4o-mini \
      [--overwrite] [--limit 3]

Environment:
  OPENAI_API_KEY must be set for real calls. If absent (or API call fails), a placeholder
  description file is written so downstream steps have deterministic artifacts.

Behavior:
  - Scans the images directory for .jpg/.jpeg/.png files.
  - For each image, creates a text file named <basename>.txt in the output directory.
  - Skips existing files unless --overwrite is provided.
  - Uses base64 inline image in a chat completion request with a strict prompt.
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png"}
DEFAULT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
SYSTEM_PROMPT = (
    "You are a fashion product describer. Provide a concise yet detailed standalone description "
    "of ONLY the primary garment in the image: include garment type, silhouette/cut, primary and "
    "secondary colors, dominant pattern (if any), material or plausible material categories, key "
    "design details (neckline, sleeves, closures, embellishments), style vibe (e.g., casual, "
    "streetwear, boho, formal), and likely occasions/seasonal suitability. Avoid mentioning the "
    "model, background, lighting, or camera. Use neutral, factual tone, no marketing fluff, no "
    "brand assumptions unless logo is explicit. 120-180 words max."
)


def iter_images(images_dir: Path) -> Iterable[Path]:
    for p in sorted(images_dir.iterdir()):
        if p.suffix.lower() in SUPPORTED_EXTS and p.is_file():
            yield p


def describe_image(client, path: Path, model: str) -> str:  # type: ignore[no-untyped-def]
    data_uri = (
        f"data:image/{path.suffix.lstrip('.').lower()};base64,"
        + base64.b64encode(path.read_bytes()).decode()
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this garment."},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content  # type: ignore[attr-defined]
    if not content:
        raise RuntimeError("Empty description from model")
    return content.strip()


def embed_text(client, text: str) -> list[float]:  # type: ignore[no-untyped-def]
    try:
        emb = client.embeddings.create(model=EMBED_MODEL, input=text)
        return list(emb.data[0].embedding)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return []


def compute_image_hash(path: Path) -> str:
    import hashlib

    h = hashlib.sha1(path.read_bytes()).hexdigest()
    return h


@dataclass
class CacheEntry:
    image_hash: str
    description: str
    embedding: list[float]


def load_cache(path: Path) -> dict[str, CacheEntry]:
    if not path.exists():
        return {}
    try:
        import json

        raw: dict[str, Any] = json.loads(path.read_text())
        out: dict[str, CacheEntry] = {}
        for k, v in raw.items():
            if isinstance(v, dict) and {"image_hash", "description", "embedding"} <= set(v):
                out[k] = CacheEntry(
                    image_hash=v["image_hash"],
                    description=v["description"],
                    embedding=v.get("embedding") or [],
                )
        return out
    except Exception:  # noqa: BLE001
        return {}


def save_cache(path: Path, cache: dict[str, CacheEntry]) -> None:
    import json

    serial = {
        k: {"image_hash": v.image_hash, "description": v.description, "embedding": v.embedding}
        for k, v in cache.items()
    }
    path.write_text(json.dumps(serial, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate garment descriptions from images")
    parser.add_argument("--images-dir", default="design/images")
    parser.add_argument("--out-dir", default="design/text")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .txt files")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N images if >0")
    parser.add_argument("--dry-run", action="store_true", help="List actions without calling API")
    parser.add_argument("--cache-file", default="design/text/_image_desc_cache.json")
    parser.add_argument(
        "--store-db",
        action="store_true",
        help="Persist descriptions and embeddings in DB",
    )
    args = parser.parse_args()

    images_dir = Path(args.images_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not images_dir.exists():
        print(f"Images dir not found: {images_dir}", file=sys.stderr)
        return 1

    api_key = os.getenv("OPENAI_API_KEY")
    client = None  # OpenAI client instance or None
    if api_key and not args.dry_run and OpenAI is not None:
        try:
            client = OpenAI()
        except Exception as e:  # noqa: BLE001
            print(f"Failed to init OpenAI client: {e}", file=sys.stderr)

    cache_path = Path(args.cache_file)
    cache = load_cache(cache_path)

    # Optional DB setup
    session = None
    if args.store_db:
        # runtime imports for optional DB persistence
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from .db_models import Base, Garment

        engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
        Base.metadata.create_all(engine)
        session = Session(engine)

    count = 0
    for img in iter_images(images_dir):
        if args.limit and count >= args.limit:
            break
        out_file = out_dir / (img.stem + ".txt")
        img_hash = compute_image_hash(img)
        cache_entry = cache.get(img.stem)
        # Reuse cached description if hash matches
        if cache_entry and cache_entry.image_hash == img_hash and not args.overwrite:
            if not out_file.exists():
                out_file.write_text(cache_entry.description + "\n")
            if session:
                from sqlalchemy import select

                g = session.scalars(select(Garment).where(Garment.image_path == str(img))).first()
                if g and (g.description is None or args.overwrite):
                    g.description = cache_entry.description
                    if cache_entry.embedding:
                        g.description_embedding = cache_entry.embedding
                    session.commit()
            count += 1
            continue
        if out_file.exists() and not args.overwrite:
            # Skip existing
            count += 1
            continue
        if args.dry_run or client is None:
            placeholder = f"[PLACEHOLDER] Description for {img.name} (dry-run or API unavailable)."
            out_file.write_text(placeholder + "\n")
            print(f"Wrote placeholder: {out_file}")
            cache[img.stem] = CacheEntry(image_hash=img_hash, description=placeholder, embedding=[])
        else:
            try:
                text = describe_image(client, img, args.model)
                out_file.write_text(text + "\n")
                print(f"Wrote description: {out_file}")
                embedding = embed_text(client, text)
                cache[img.stem] = CacheEntry(
                    image_hash=img_hash, description=text, embedding=embedding
                )
                if session:
                    # Upsert garment by image_path if exists
                    g = session.scalars(
                        select(Garment).where(Garment.image_path == str(img))
                    ).first()
                    if g:
                        g.description = text
                        if embedding:
                            g.description_embedding = embedding
                        session.commit()
            except Exception as e:  # noqa: BLE001
                err_text = f"[ERROR] Failed to describe {img.name}: {e}"
                out_file.write_text(err_text + "\n")
                print(err_text, file=sys.stderr)
                cache[img.stem] = CacheEntry(
                    image_hash=img_hash, description=err_text, embedding=[]
                )
        count += 1
    # Persist cache
    save_cache(cache_path, cache)
    if session:
        session.close()
    print(f"Processed {count} image(s). Output dir: {out_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
