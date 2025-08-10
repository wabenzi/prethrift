"""Generate and write the OpenAPI spec (JSON + YAML) for the FastAPI app.

Usage:
  python backend/scripts/generate_openapi.py [--out-dir backend/architecture]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    import importlib

    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="backend/architecture", help="Output directory")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Lazy import app
    app_mod = importlib.import_module("backend.app.main")
    app = app_mod.app
    spec = app.openapi()
    (out_dir / "openapi.json").write_text(json.dumps(spec, indent=2) + "\n")
    try:  # optional YAML
        import yaml  # type: ignore

        (out_dir / "openapi.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
    except Exception:  # pragma: no cover - yaml optional
        pass
    print(f"Wrote OpenAPI spec to {out_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
