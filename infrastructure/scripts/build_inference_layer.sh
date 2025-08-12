#!/usr/bin/env bash
set -euo pipefail
# Build the inference lambda layer into ./layers/inference/dist
# Usage: ./scripts/build_inference_layer.sh [python_version]
# Default python_version=python3.11
PY_BIN=${1:-python3.11}
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)
LAYER_DIR="$ROOT_DIR/layers/inference"
DIST_DIR="$LAYER_DIR/dist"
REQ_FILE="$LAYER_DIR/python/requirements.txt"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "Requirements file not found: $REQ_FILE" >&2
  exit 1
fi

rm -rf "$DIST_DIR" && mkdir -p "$DIST_DIR/python"
# Use a temp venv to ensure clean build
TMP_VENV=$(mktemp -d)
trap 'rm -rf "$TMP_VENV"' EXIT
$PY_BIN -m venv "$TMP_VENV"
source "$TMP_VENV/bin/activate"
python -m pip install --upgrade pip
pip install -r "$REQ_FILE" -t "$DIST_DIR/python"
# Clean up cache & tests to shrink layer
find "$DIST_DIR/python" -type d -name "__pycache__" -prune -exec rm -rf {} + || true
find "$DIST_DIR/python" -type d -name "tests" -prune -exec rm -rf {} + || true

echo "Layer build complete at $DIST_DIR"
