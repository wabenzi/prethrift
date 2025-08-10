# Vintage Vault

[![CI](https://github.com/wabenzi/prethrift/actions/workflows/ci.yml/badge.svg)](https://github.com/wabenzi/prethrift/actions/workflows/ci.yml)

Multi-platform commerce app with ML-powered search.

## Structure
Backend and frontend are modularized for clarity.

### Backend (FastAPI)
`backend/app` key modules:
* `main.py` – minimal bootstrap (creates FastAPI app, includes routers, root & cache admin only)
* `api/` – feature routers:
	* `search.py` – semantic search endpoint
	* `inventory.py` – inventory image upload, batch processing, stats
	* `ingest.py` – single garment ingest endpoint
	* `user_profile.py` – user preference extraction & garment description refresh
	* `feedback.py` – interaction feedback adjusting preference weights
* `refresh_description.py` – shared core logic for refreshing garment descriptions (used by routers)
* `inventory_processing.py` – image persistence, optimization, multi‑garment description helpers, color stats
* `inventory_utils.py` – utility helpers (safe attribute upsert, image file persistence)
* `describe_images.py` – OpenAI vision description + embedding utilities & CLI script
* `core.py` – OpenAI client + embedding cache helpers
* `ontology.py` (and related) – attribute classification & confidence scoring
* `db_models.py` – SQLAlchemy ORM models

Tests live in `backend/tests` and now target the new `/user/...` paths (legacy root paths removed).

### Frontend
* `frontend/web` – React + TypeScript (Vite)
* `frontend/ios` – SwiftUI app scaffold

### Design
Assets (logos, icons, wireframes) under `design/`.

## Architecture Diagrams
High-level diagrams (kept in `backend/architecture`):

### Component Overview
![Architecture](backend/architecture/architecture.puml)

### Sequence Flows
![Sequences](backend/architecture/sequences.puml)

These `.puml` sources render automatically in many IDE plugins. For GitHub rendering you can use a PlantUML action or manually export PNG/SVG and commit alongside if desired.

## Makefile Commands
Common developer tasks:

```
make install     # create venv + install backend deps
make dev         # run FastAPI with reload
make test        # run pytest
make lint        # ruff lint
make format      # ruff format write
make type        # mypy type check
make transcribe FILE=audio.mp3  # run transcription script
make ci          # lint + type + test
make clean       # remove venv & caches
```

## Developer Tooling
Nox sessions (optional):
```
nox -l           # list sessions
nox -s lint      # Ruff lint
nox -s typecheck # mypy
nox -s tests     # pytest
nox -s all       # run lint+type+tests
```

Pre-commit hooks:
```
pip install pre-commit  # (or use existing venv)
pre-commit install
```
Hooks: Ruff (fix & format), mypy, flake8 (extra eyes), basic hygiene checks.

## Optional OpenAI End-to-End Test
A cost-incurring integration test (`test_e2e_openai_search.py`) is skipped by default. Run it manually with real API access:
```
export OPENAI_API_KEY=sk-...
export RUN_OPENAI_E2E=1
pytest -q backend/tests/test_e2e_openai_search.py
```
Or trigger the manual workflow_dispatch job in GitHub Actions (requires `OPENAI_API_KEY` secret). See `backend/README-e2e.md` for details.

## Recent Refactors
* Consolidated refresh-description logic into `refresh_description.py`.
* Moved ingest endpoint out of `main.py` into `api/ingest.py`.
* Trimmed `main.py` to a minimal bootstrap; removed legacy compatibility routes.
* Added tests for `inventory_utils` and new `/feedback` router path.
* Updated tests to use `/user/garments/refresh-description` and `/user/preferences/extract` paths.

## Running Tests
```
make test
```
All current tests (excluding optional OpenAI E2E) should pass: see CI badge.
