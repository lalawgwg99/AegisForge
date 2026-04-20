# Contributing

Thanks for contributing to Agent Fusion OS.

## How to contribute
1. Open an issue describing the pain point or proposal.
2. If accepted, submit a PR with:
   - clear problem statement
   - design notes
   - measurable impact (before/after)

## PR checklist
- keeps architecture modular
- includes tests/validation scripts when possible
- updates docs for behavior changes
- runs `bash scripts/preflight.sh`（含 pre-check、retry/backoff+timeout、credentials/scope gate）
- keeps SDK/MCP behavior contract stable (`pytest -q tests/test_contracts.py`)

## Principles
- reliability first
- measurable outcomes over claims
- model/provider neutrality
- security by default

## Release readiness
Before publishing a version tag, run:

```bash
bash scripts/release_gate.sh
```
