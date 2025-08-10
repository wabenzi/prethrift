# Vintage Vault

[![CI](https://github.com/wabenzi/prethrift/actions/workflows/ci.yml/badge.svg)](https://github.com/wabenzi/prethrift/actions/workflows/ci.yml)

Multi-platform commerce app with ML-powered search.

## Structure
- backend: FastAPI, Postgres, vector DB
- frontend/web: React + TypeScript
- frontend/ios: SwiftUI
- design: wireframes, logo, app icon

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
