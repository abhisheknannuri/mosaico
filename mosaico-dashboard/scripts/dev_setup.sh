#!/usr/bin/env bash
# Development environment setup. Run from mosaico-dashboard/.
set -euo pipefail

echo ">> Starting development environment setup using Python 3.12"
poetry env use 3.12

echo ">> Installing dashboard dependencies (poetry install)"
poetry install

echo ">> Installing Mosaico SDK (editable) from ../mosaico-sdk-py"
poetry run pip install --quiet -e ../mosaico-sdk-py

echo ">> Checking dependency consistency (pip check)"
poetry run pip check

echo ">> Done. SDK imported from:"
poetry run python -c "import mosaicolabs; print('   ', mosaicolabs.__file__)"
