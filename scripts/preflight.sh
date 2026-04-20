#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -d "src" ]]; then
  export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
fi

if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD="gtimeout"
else
  TIMEOUT_CMD=""
fi

RETRY_MAX="${PRECHECK_RETRY_MAX:-2}"
BACKOFF_BASE="${PRECHECK_BACKOFF_SECONDS:-2}"

TIMEOUT_LINT="${PRECHECK_TIMEOUT_LINT:-120}"
TIMEOUT_MYPY="${PRECHECK_TIMEOUT_MYPY:-120}"
TIMEOUT_TESTS="${PRECHECK_TIMEOUT_TESTS:-180}"
TIMEOUT_QUALITY="${PRECHECK_TIMEOUT_QUALITY:-180}"
TIMEOUT_SCOPE="${PRECHECK_TIMEOUT_SCOPE:-30}"

SKIP_LINT="${PRECHECK_SKIP_LINT:-0}"
SKIP_MYPY="${PRECHECK_SKIP_MYPY:-0}"
SKIP_TESTS="${PRECHECK_SKIP_TESTS:-0}"
SKIP_QUALITY="${PRECHECK_SKIP_QUALITY:-0}"

log() {
  echo "[preflight] $*"
}

run_with_timeout() {
  local timeout_seconds="$1"
  shift

  if [[ -n "$TIMEOUT_CMD" ]]; then
    "$TIMEOUT_CMD" "$timeout_seconds" "$@"
    return
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    log "warn: timeout/gtimeout/python3 都不存在，改為無 timeout 直接執行"
    "$@"
    return
  fi

  python3 - "$timeout_seconds" "$@" <<'PY'
import subprocess
import sys

timeout = int(sys.argv[1])
cmd = sys.argv[2:]

try:
    completed = subprocess.run(cmd, timeout=timeout, check=False)
except subprocess.TimeoutExpired:
    print(f"[preflight] timeout after {timeout}s: {' '.join(cmd)}", file=sys.stderr)
    sys.exit(124)

sys.exit(completed.returncode)
PY
}

require_paths() {
  local missing=()
  local required=(
    "pyproject.toml"
    "src/aegisforge"
    "tests"
  )

  for p in "${required[@]}"; do
    if [[ ! -e "$p" ]]; then
      missing+=("$p")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    log "error: 缺少必要路徑/檔案（not_found）: ${missing[*]}"
    exit 1
  fi
}

require_commands() {
  local missing=()
  local required=(python3 pytest ruff mypy)

  for c in "${required[@]}"; do
    if ! command -v "$c" >/dev/null 2>&1; then
      missing+=("$c")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    log "error: 缺少必要命令（pre-check）: ${missing[*]}"
    log "hint: 先安裝依賴再重跑 preflight。"
    exit 1
  fi
}

require_envs_if_configured() {
  local raw="${PRECHECK_REQUIRED_ENVS:-}"
  [[ -z "$raw" ]] && return 0

  local missing=()
  IFS=',' read -r -a envs <<< "$raw"
  for key in "${envs[@]}"; do
    key="${key//[[:space:]]/}"
    [[ -z "$key" ]] && continue
    if [[ -z "${!key:-}" ]]; then
      missing+=("$key")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    log "error: 缺少必要憑證環境變數（credentials gate）: ${missing[*]}"
    exit 1
  fi
}

run_scope_check_if_configured() {
  local cmd="${PRECHECK_SCOPE_CHECK_CMD:-}"
  [[ -z "$cmd" ]] && return 0

  run_step "Credential Scope Check" "$TIMEOUT_SCOPE" bash -lc "$cmd"
}

run_step() {
  local step_name="$1"
  local timeout_seconds="$2"
  shift 2

  local attempt=1
  local backoff="$BACKOFF_BASE"

  while true; do
    log "==> ${step_name} (attempt ${attempt}/${RETRY_MAX})"

    local rc=0
    if run_with_timeout "$timeout_seconds" "$@"; then
      rc=0
    else
      rc=$?
    fi

    if (( rc == 0 )); then
      return 0
    fi

    if (( attempt >= RETRY_MAX )); then
      log "error: ${step_name} failed after ${attempt} attempt(s), rc=${rc}"
      return "$rc"
    fi

    log "warn: ${step_name} failed (rc=${rc}), retry in ${backoff}s"
    sleep "$backoff"
    backoff=$(( backoff * 2 ))
    attempt=$(( attempt + 1 ))
  done
}

log "開始 Preflight Hard Gate"
require_paths
require_commands
require_envs_if_configured
run_scope_check_if_configured

if [[ "$SKIP_LINT" != "1" ]]; then
  run_step "Lint (ruff)" "$TIMEOUT_LINT" ruff check src tests examples
else
  log "skip: Lint (ruff)"
fi

if [[ "$SKIP_MYPY" != "1" ]]; then
  run_step "Type Check (mypy)" "$TIMEOUT_MYPY" mypy
else
  log "skip: Type Check (mypy)"
fi

if [[ "$SKIP_TESTS" != "1" ]]; then
  run_step "Tests (pytest)" "$TIMEOUT_TESTS" pytest -q
else
  log "skip: Tests (pytest)"
fi

if [[ "$SKIP_QUALITY" != "1" ]]; then
  run_step "Quality Gate" "$TIMEOUT_QUALITY" python3 -m aegisforge.cli quality-check --rounds 200
else
  log "skip: Quality Gate"
fi

log "Preflight checks passed."
