#!/usr/bin/env bash
# Single local validation entrypoint (ADR-009). Mirrors what a reviewer runs.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== ruff lint =="
ruff check src tests

echo "== pytest =="
pytest -v

echo "== validate.sh: all checks passed =="
