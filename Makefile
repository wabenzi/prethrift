# Makefile for Prethrift project (macOS/Linux)
# Usage examples:
#   make install            # create venv + install deps
#   make update             # upgrade deps to latest versions in constraints
#   make lint               # ruff checks
#   make format             # apply formatting
#   make type               # mypy type checking
#   make test               # run pytest
#   make dev                # run uvicorn with reload
#   make run                # run uvicorn (no reload)
#   make transcribe FILE=path/to/audio.mp3  # run transcription CLI
#   make clean              # remove venv + caches
#   make ci                 # lint + type + test (like CI pipeline)

PYTHON ?= python3
BACKEND_DIR := backend
APP_MODULE := backend.app.main:app
VENV_DIR := $(BACKEND_DIR)/.venv
REQ := $(BACKEND_DIR)/requirements.txt
ACTIVATE := . $(VENV_DIR)/bin/activate
PYTHONPATH := .

# Colors
BLUE=\033[34m
GREEN=\033[32m
YELLOW=\033[33m
RESET=\033[0m

.PHONY: install update lint format type test dev run transcribe clean ci help
 .PHONY: openapi diagram diagrams

$(VENV_DIR): $(REQ)
	@echo "$(BLUE)[venv]$(RESET) Creating virtual environment"
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(ACTIVATE) && pip install --upgrade pip
	@$(ACTIVATE) && pip install -r $(REQ)
	@echo "$(GREEN)[venv ready]$(RESET)"

install: $(VENV_DIR)
	@echo "$(GREEN)Dependencies installed.$(RESET)"

update: $(REQ) | $(VENV_DIR)
	@echo "$(BLUE)[update]$(RESET) Upgrading installed packages"
	@$(ACTIVATE) && pip install --upgrade -r $(REQ)

lint: | $(VENV_DIR)
	@echo "$(BLUE)[ruff]$(RESET) Linting"
	@$(ACTIVATE) && (cd $(BACKEND_DIR) && ruff check . && ruff format --check .)

format: | $(VENV_DIR)
	@echo "$(BLUE)[ruff fmt]$(RESET) Formatting"
	@$(ACTIVATE) && (cd $(BACKEND_DIR) && ruff format .)

type: | $(VENV_DIR)
	@echo "$(BLUE)[mypy]$(RESET) Type checking"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && mypy backend/app

test: | $(VENV_DIR)
	@echo "$(BLUE)[pytest]$(RESET) Running tests"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && pytest -q --cov=backend/app --cov-report=term-missing:skip-covered --cov-report=json:backend/coverage.json --cov-report=xml:backend/coverage.xml backend/tests

coverage: | $(VENV_DIR)
	@echo "$(BLUE)[coverage]$(RESET) Re-running tests with coverage (HTML)"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && pytest -q --cov=backend/app --cov-report=html:backend/htmlcov backend/tests

run: | $(VENV_DIR)
	@echo "$(BLUE)[uvicorn]$(RESET) Starting (no reload)"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && uvicorn $(APP_MODULE)

dev: | $(VENV_DIR)
	@echo "$(BLUE)[uvicorn]$(RESET) Dev server with reload"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && uvicorn $(APP_MODULE) --reload

transcribe: | $(VENV_DIR)
	@if [ -z "$(FILE)" ]; then echo "Usage: make transcribe FILE=path/to/audio.mp3"; exit 1; fi
	@echo "$(BLUE)[transcribe]$(RESET) $(FILE)"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && python backend/app/transcribe-troy.py $(FILE)

extract-prefs: | $(VENV_DIR)
	@if [ -z "$(TEXT)" ]; then echo 'Usage: make extract-prefs TEXT="conversation text"'; exit 1; fi
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && python -c "from backend.app.openai_extractor import extract_preferences;import json;print(json.dumps(extract_preferences(\"$(TEXT)\"), indent=2))"

describe-images: | $(VENV_DIR)
	@echo "$(BLUE)[describe]$(RESET) Generating garment descriptions"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && python -m backend.app.describe_images --images-dir design/images --out-dir design/text $(ARGS)

ci: lint type test
	@echo "$(GREEN)[ci] All checks passed.$(RESET)"

metrics: | $(VENV_DIR)
	@echo "$(BLUE)[metrics]$(RESET) Computing project metrics (backend/app + frontend/web/src)"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && python backend/scripts/project_metrics.py --root backend/app --top 10
	@if [ -d frontend/web/src ]; then \
	  PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && python backend/scripts/project_metrics.py --root frontend/web/src --top 10; \
	fi

openapi: | $(VENV_DIR)
	@echo "$(BLUE)[openapi]$(RESET) Generating OpenAPI spec"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && PYTHONPATH=. python backend/scripts/generate_openapi.py --out-dir backend/architecture

types: openapi
	@echo "$(BLUE)[types]$(RESET) Generating TypeScript API types & client"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && PYTHONPATH=. python backend/scripts/generate_typescript_client.py

diagram diagrams: | $(VENV_DIR)
	@echo "$(BLUE)[plantuml]$(RESET) (Optional) Render .puml -> .png/.svg if plantuml installed"
	@if command -v plantuml >/dev/null 2>&1; then \
	  plantuml backend/architecture/*.puml; \
	else \
	  echo "PlantUML not installed; skipping render (files in backend/architecture)"; \
	fi

clean:
	@echo "$(YELLOW)[clean]$(RESET) Removing venv and caches"
	@rm -rf $(VENV_DIR) backend/.mypy_cache backend/.ruff_cache backend/__pycache__ backend/app/__pycache__

help:
	@grep -E '^# |^[a-zA-Z_-]+:' Makefile | sed -e 's/:.*//' -e 's/^# //'
