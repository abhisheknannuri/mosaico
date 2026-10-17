#!/usr/bin/env bash
# Format check, lint, type check and tests. Run from mosaico-dashboard/.
set -euo pipefail

echo ">> ruff format --check"
poetry run ruff format --check .

echo ">> ruff check"
poetry run ruff check .

echo ">> pyright"
poetry run pyright

echo ">> pytest"
poetry run pytest
