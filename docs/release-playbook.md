# Release Playbook

## Release Gate (must pass)

Run locally before tagging:

```bash
bash scripts/release_gate.sh
```

This gate enforces:
- preflight (`ruff`, `mypy`, `pytest`, quality gate)
- SDK/MCP contract checks
- baseline memory health command

## Tag and Publish

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

Release workflow is triggered by the tag and publishes to PyPI after gate success.

## Rollback Guide

If a release is bad:

1. Stop adoption:
   - mark GitHub Release as pre-release or add rollback notice.
2. Publish a hotfix version:
   - fix on `main`, run `scripts/release_gate.sh`, publish `vX.Y.(Z+1)`.
3. Pin consumers:
   - update Hermes/OpenClaw install docs to pin the last known-good version.
4. Postmortem:
   - record incident cause and prevention actions in `CHANGELOG.md`.
