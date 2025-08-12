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

.PHONY: help venv clean backend frontend test test-unit test-integration test-e2e test-e2e-s3 test-local-cv demo-local-cv test-grok-vs-local-cv test-grok-vs-local-cv-pytest test-cv-comparison lint format check sync-from-prod backup-db start-dev infrastructure-build build-inference-layer test-synth bundle-sizes

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

# --- Database Migrations (Alembic) ---
migrate: | $(VENV_DIR)
	@echo "$(BLUE)[alembic]$(RESET) upgrade head"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && alembic -c backend/alembic.ini upgrade head

revision: | $(VENV_DIR)
	@if [ -z "$(MSG)" ]; then echo 'Usage: make revision MSG="message"'; exit 1; fi
	@echo "$(BLUE)[alembic]$(RESET) new revision: $(MSG)"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && alembic -c backend/alembic.ini revision -m "$(MSG)"

# --- Infrastructure (CDK) ---
cdk-bootstrap:
	@echo "$(BLUE)[cdk]$(RESET) bootstrap"
	cd infrastructure && pip install -r requirements.txt && cdk bootstrap

cdk-synth:
	@echo "$(BLUE)[cdk]$(RESET) synth"
	cd infrastructure && cdk synth

cdk-deploy:
	@echo "$(BLUE)[cdk]$(RESET) deploy"
	cd infrastructure && cdk deploy PrethriftStack

# Build inference layer (installs layer requirements into dist directory)
layer-build:
	@echo "$(BLUE)[layer]$(RESET) building inference layer"
	bash infrastructure/scripts/build_inference_layer.sh

# Create a trimmed Lambda source bundle directory (excludes large deps moved to layer)
lambda-package: | $(VENV_DIR)
	@echo "$(BLUE)[lambda]$(RESET) preparing trimmed lambda source package"
	rm -rf lambda_build && mkdir -p lambda_build
	rs="torch torchvision pillow scikit-learn"; \
	for d in $$rs; do echo "Excluding $$d (provided by layer)"; done
	rs_in_site=$$(python -c 'import sys,site,inspect,os; print("\n".join(site.getsitepackages()))'); \
	cp -R backend/app lambda_build/; \
	# (Optional) prune caches
	find lambda_build -type d -name '__pycache__' -prune -exec rm -rf {} +

# End-to-end: build layer, synth, deploy
deploy-all: layer-build cdk-synth cdk-deploy
	@echo "$(GREEN)[deploy] complete$(RESET)"

# Report bundle sizes (layer + function code) after synth (uses cdk.out)
bundle-sizes:
	@echo "$(BLUE)[sizes]$(RESET) Reporting asset bundle sizes"
	@if [ ! -d cdk.out ]; then echo "Run make cdk-synth first"; exit 1; fi
	@find cdk.out -maxdepth 1 -type f -name '*.zip' -print0 | while IFS= read -r -d '' f; do printf '%8.1f KB  %s\n' $$(echo "scale=1; $$(stat -f%z $$f)/1024" | bc) $$f; done | sort -n
	@if [ -d infrastructure/layers/inference/dist/python ]; then du -sh infrastructure/layers/inference/dist | sed 's/^/Layer dir: /'; fi

# E2E test for S3 upload pipeline (mocks S3, tests processor handler)
test-e2e-s3: | $(VENV_DIR)
	@echo "$(BLUE)[e2e-s3]$(RESET) Testing S3 upload pipeline end-to-end"
	@PYTHONPATH=$(PYTHONPATH) $(ACTIVATE) && pytest backend/tests/test_e2e_s3_pipeline.py::test_e2e_s3_upload_pipeline -v

# Test local computer vision garment analysis
test-local-cv: backend/.venv
	@echo "[local-cv] Testing local computer vision garment analysis"
	cd backend && .venv/bin/pytest tests/test_local_cv.py -v

demo-local-cv: backend/.venv
	@echo "[demo-local-cv] Demonstrating local computer vision system"
	cd backend && .venv/bin/python demo_local_cv.py

test-grok-vs-local-cv: backend/.venv
	@echo "[grok-vs-local-cv] Comparing Grok descriptions with local CV analysis"
	cd backend && PYTHONPATH=. .venv/bin/python tests/test_grok_vs_local_cv.py

test-grok-vs-local-cv-pytest: backend/.venv
	@echo "[grok-vs-local-cv-pytest] Running Grok vs Local CV comparison as pytest"
	cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_grok_vs_local_cv.py -v -s

test-cv-comparison: backend/.venv
	@echo "[cv-comparison] Comparing OpenAI vs Local CV systems"
	cd backend && .venv/bin/python tests/test_cv_comparison.py

# --- Frontend Build (placeholder for S3/CloudFront deploy) ---
frontend-build:
	@echo "$(BLUE)[frontend]$(RESET) build web app"
	cd frontend/web && npm install && npm run build

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
