# Security Policy

## Supported Versions

AegisForge uses semantic versioning. Security fixes are provided only for actively maintained minor versions.

| Version | Supported |
| --- | --- |
| 0.4.x | Yes |
| < 0.4.0 | No |

If a critical issue is found, maintainers may ship an out-of-band patch release.

## Reporting a Vulnerability

Please do **not** open public issues for security vulnerabilities.

Use one of these channels:
1. GitHub Security Advisory (preferred):
   - Go to the repository `Security` tab
   - Click `Report a vulnerability`
2. If Advisory is unavailable, contact the maintainer privately and include:
   - Affected version
   - Reproduction steps or PoC
   - Impact assessment
   - Suggested mitigation (optional)

## Response Targets

- Initial acknowledgement: within 72 hours
- Triage and severity assessment: within 7 days
- Patch timeline:
  - Critical/High: target within 14 days
  - Medium/Low: next scheduled patch release

## Disclosure Process

1. Confirm and reproduce the issue.
2. Prepare a fix and regression test.
3. Publish patched release and release notes.
4. Publicly disclose details after users can upgrade.
