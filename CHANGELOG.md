# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

### Added
- GitHub Actions CI workflow for tests and quality gate.
- Executable examples under `examples/` for SDK loop, log import, and MCP setup.
- `SECURITY.md` with vulnerability reporting and supported-version policy.
- Release workflow for PyPI publish and GitHub tag release notes.
- PR template and issue templates (bug report, feature request, security contact link).
- Hermes/OpenClaw integration checklist and minimal MCP config examples.
- `scripts/preflight.sh` for one-command local quality checks.
- Retry policy module (`retry_policy.py`) with transient HTTP/network classification.
- LLM observability metrics at `.aegisforge/reports/llm-extract-stats.json`.
- CLI command `aegisforge llm-stats` and MCP tool `aegis_llm_stats`.
- SDK/MCP contract tests (`tests/test_contracts.py`).
- Hermes install integration smoke test (`tests/test_hermes_integration.py`).
- Release gate script (`scripts/release_gate.sh`) and rollback playbook (`docs/release-playbook.md`).

### Changed
- README now links to examples and changelog for faster onboarding.
- CI now includes lint (`ruff`) and type checks (`mypy`) before tests and quality gate.
- `llm_extract.py` now retries transient LLM failures with backoff and fails fast on 401/403.
- `llm_extract.py` retry now covers `429` and common transient network errors, with guarded empty-backoff handling.
- CI adds a dedicated Hermes install + MCP/CLI smoke job.
- Release workflow now enforces release gate before publish.
- Ruff lint policy restores full `E` rules with scoped test-file ignore.

## [0.4.0] - 2026-04-11

### Added
- Python SDK (`AegisForge`) with typed result models.
- MCP Tool Server (`aegisforge-mcp`) for IDE/agent integration.
- LLM-based lesson extraction with template fallback.
- External log importer (`import-log`) with field mapping.
- Causal lane distillation and preflight guardrails.
- Verifiable safety gate with decision replay.
- Benchmark pack and quality-check commands.
- Dream mode reporting and action ledger.

### Changed
- Improved reliability benchmark reporting and recovery tracking.
- Updated README with SDK/CLI/MCP usage flow.

## [0.3.0] - 2026-04-08

### Added
- Causal lanes, safety gate, and benchmark pack baseline.

## [0.2.0] - 2026-04-08

### Added
- Adaptive recovery graph, semantic dedup, forgetting engine, policy gate CLI.

## [0.1.0] - 2026-04-08

### Added
- Initial MVP reliability loop: capture, distill, inject, health.
