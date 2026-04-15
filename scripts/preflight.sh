#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD="gtimeout"
else
  TIMEOUT_CMD=""
fi

run_step() {
  local step_name="$1"
  local timeout_seconds="$2"
  shift 2

  echo "==> ${step_name}"
  if [[ -n "$TIMEOUT_CMD" ]]; then
    "$TIMEOUT_CMD" "${timeout_seconds}" "$@"
  else
    "$@"
  fi
}

if [[ -d "src" ]]; then
  export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
fi

run_step "Lint (ruff)" 120 ruff check src tests examples
run_step "Type Check (mypy)" 120 mypy
run_step "Tests (pytest)" 180 pytest -q
run_step "Quality Gate" 180 python -m aegisforge.cli quality-check --rounds 200

echo "Preflight checks passed."
