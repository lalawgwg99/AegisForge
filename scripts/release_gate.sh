#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -d "src" ]]; then
  export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
fi

echo "==> Release gate: preflight"
bash scripts/preflight.sh

echo "==> Release gate: contract tests"
pytest -q tests/test_contracts.py

echo "==> Release gate: memory health baseline"
python -m aegisforge.cli health
