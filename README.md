# Vintage Vault

[![CI](https://github.com/wabenzi/prethrift/actions/workflows/ci.yml/badge.svg)](https://github.com/wabenzi/prethrift/actions/workflows/ci.yml)

Multi-platform commerce app with ML-powered search.

## High-Level Purpose
Prethrift ("Vintage Vault") is a fashion discovery & personalization platform. It enriches raw, long-tail or second‑hand apparel inventory with structured ontology attributes and semantic embeddings, then serves explainable, preference‑aware search and (future) recommendations. The system emphasizes: (1) hybrid precision + recall, (2) graceful degradation when external AI is unavailable, (3) user input quality controls (ambiguity / off‑topic), and (4) stable typed contracts for multiple frontends (web, iOS).

## Key Differentiators
* Ontology + Embeddings Hybrid: Attribute overlap + semantic similarity yields interpretable relevance.
* Deterministic Fallbacks: Hash-based image vectors & heuristics keep baseline search functional offline.
* Input Guardrails: Ambiguity clarification and off-topic filtering (with force override) reduce noise early.
* Explainable Path: Ranking pipeline designed so future re-rankers can surface contributing signals.
* Contract Discipline: OpenAPI generation + drift checks enable automated TypeScript client types.

## Implemented Features (Why They Matter)
| Feature | Value |
|---------|-------|
| Modular FastAPI routers | Clear ownership & test isolation |
| Ontology-driven attribute extraction | Human-auditable, stable semantics |
| Hybrid ranking (embeddings + attributes + preferences) | Balanced recall & precision, personalization |
| Ambiguity detection & clarification | Reduces wasted queries, improves intent capture |
| Off-topic heuristic filter + override | Protects result quality, allows power-user bypass |
| Deterministic image feature hashing | Zero external dependency baseline |
| OpenAPI spec + drift check | Prevents silent contract breakage |
| Pre-commit (Ruff, mypy) & pytest suites | Continuous code health |

## Roadmap Snapshot
Short-term: Clarification tests; metrics (ambiguity/off-topic rates); moderation schema fields; TS client generation pipeline.

Mid-term: Preference decay & diversity; pluggable vision encoder; vector index (FAISS / Qdrant) behind interface; multi-stage retrieval.

Long-term: Learned re-ranker; style clustering personas; advanced moderation tiers; experimentation framework; observability dashboards.

## Frontend Integration (TypeScript Web)
1. Generate OpenAPI JSON (script) → run openapi-typescript to produce `src/api/types.ts`.
2. Build a typed fetch wrapper with abort + debounce (search keystrokes).
3. Interpret response fields:
	 * `clarification` present → show inline prompt with Accept/Refine actions.
	 * `off_topic` true → show notice + "Search anyway" (resend with `force=true`).
4. Display results with attribute highlights & optional "Why shown" expandable explanation.
5. Persist lightweight analytics events (issued, clarified, forced, result_click) for tuning.

## Suggested Project Structure Enhancements
Backend (incremental refactor):
```
backend/app/
	api/            # routers
	schemas/        # pydantic models
	services/       # ontology, ranking, features, moderation
	repositories/   # DB access abstractions
	core/           # config, clients, logging
```
Frontend (web):
```
src/
	api/            # generated types + client
	features/search/
	components/
	models/
	lib/            # utilities (fetch, debounce)
	styles/
```

## Additional Feature Ideas
* Visual similarity search (upload / image-to-image) once pluggable encoder added.
* Explainability panel: show top contributing attributes & semantic score.
* Saved searches + delta alerts for newly matching items.
* Style profile clustering ("Casual Minimalist" tag) to drive curated carousels.
* Session-aware re-ranking (short-term vs long-term intent separation).

## Alternative / Complementary Search Approaches
* Attribute-first candidate filter + semantic re-rank (latency optimization).
* Sparse (BM25) + dense fusion via reciprocal rank fusion.
* Graph similarity (shared attribute / co-engagement edges) for related items.
* Learned gradient-boosted re-ranker with rich feature vector (token overlap, cosine, Jaccard, preference distance, freshness).

## UI / UX Notes (Search & Results)
* Chips for recognized attributes inside the search bar (removable tokens).
* Ambiguity banner: selectable interpretations (e.g., "blazer" vs "sport coat").
* Off-topic interstitial with refine or override path.
* Result cards: highlight matched color/material; mini "Why" toggle.
* Empty states: suggestions from ontology neighbors; clarify prompt gating before search.

## Moderation & Guardrails
Current: Heuristic ambiguity + off-topic detection; user force override for benign off-topic.
Planned: Moderation flags (e.g., `moderation_required`), layered classifier, disallowed category block (no override). Avoid trivializing harmful input; instead return a neutral guidance panel (never substituting with unrelated images that could be perceived as minimizing severity).

## Architecture Decision Records (ADRs)
Stored under `docs/adr`. See `0001-architecture-overview.md` for baseline architecture rationale and future evolution path.

## Contribution Quick Wins
* Add tests covering clarification flow.
* Introduce metrics counters (Prometheus) for query quality events.
* Refactor ranking components into `services/`.
* Generate TS types in CI and fail on drift.
* Implement pluggable vision encoder interface & stub.

---
This extended section documents the platform vision, current differentiators, and a pragmatic path toward a scalable, explainable fashion discovery engine.

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
make coverage    # run pytest with HTML coverage report (backend/htmlcov)
make lint        # ruff lint
make format      # ruff format write
make type        # mypy type check
make transcribe FILE=audio.mp3  # run transcription script
make ci          # lint + type + test
make metrics     # project metrics (SLOC, comments, coverage if present)
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
