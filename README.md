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
