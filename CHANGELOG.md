# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

### Added
- GitHub Actions CI workflow for tests and quality gate.
- Executable examples under `examples/` for SDK loop, log import, and MCP setup.

### Changed
- README now links to examples and changelog for faster onboarding.

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
