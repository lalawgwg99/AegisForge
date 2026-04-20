"""Import external agent logs and extract failures into AegisForge.

Supports:
  - Generic JSONL logs with configurable field mapping
  - Auto-detection of common error patterns
  - Claude Code / OpenAI / LangChain log formats
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .core import capture_failure
from .storage import ensure_root

_ERROR_KEYWORDS = re.compile(
    r"(?i)(error|fail|exception|timeout|unauthorized|denied|refused|"
    r"crash|panic|fatal|abort|reject|invalid|expired|rate.?limit|"
    r"not.?found|broken|unavailable|unreachable)",
)

_DEFAULT_FIELD_MAP = {
    "error_type": "error_type",
    "message": "message",
    "source": "source",
}

_COMMON_MESSAGE_FIELDS = ["message", "msg", "error", "error_message", "detail", "text", "content"]
_COMMON_TYPE_FIELDS = ["error_type", "type", "level", "severity", "error_code", "code", "kind"]
_COMMON_SOURCE_FIELDS = ["source", "component", "module", "service", "tool", "origin", "logger"]


def _detect_field(row: dict, candidates: list[str], fallback: str = "") -> str:
    """Try multiple candidate field names, return the first non-empty match."""
    for key in candidates:
        val = row.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return fallback


def _classify_error_type(message: str) -> str:
    """Infer error type from message text if not explicitly provided."""
    low = message.lower()
    if "timeout" in low:
        return "timeout"
    if "unauthorized" in low or "401" in low or "403" in low or "permission" in low:
        return "unauthorized"
    if "rate limit" in low or "429" in low or "throttl" in low:
        return "rate_limit"
    if "not found" in low or "404" in low:
        return "not_found"
    if "connection" in low or "unreachable" in low or "refused" in low:
        return "connection_error"
    if "syntax" in low or "parse" in low or "invalid" in low:
        return "validation_error"
    return "unknown"


def _is_error_line(row: dict, field_map: dict[str, str]) -> bool:
    """Determine if a log line represents an error/failure event."""
    level = str(row.get("level", row.get("severity", ""))).lower()
    if level in {"error", "fatal", "critical", "panic"}:
        return True

    msg_field = field_map.get("message", "message")
    message = str(row.get(msg_field, ""))
    if _ERROR_KEYWORDS.search(message):
        return True

    if row.get("error") or row.get("exception") or row.get("traceback"):
        return True

    return False


def _parse_line(line: str) -> dict | None:
    """Parse a single log line. Supports JSON and plain text."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        pass
    # Plain text: treat as message
    if _ERROR_KEYWORDS.search(line):
        return {"message": line, "source": "log", "error_type": "unknown"}
    return None


def _parse_line_jsonl(line: str) -> dict | None:
    """Parse a single JSONL line only."""
    line = line.strip()
    if not line:
        return None
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        return None
    return row if isinstance(row, dict) else None


def _parse_line_text(line: str) -> dict | None:
    """Parse a single text line only."""
    line = line.strip()
    if not line:
        return None
    if _ERROR_KEYWORDS.search(line):
        return {"message": line, "source": "log", "error_type": "unknown"}
    return None


def import_agent_log(
    root: Path,
    path: Path,
    fmt: str = "auto",
    field_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Import an agent log file and extract failure events.

    Args:
        root: AegisForge data root.
        path: Path to the log file (JSONL or plain text).
        fmt: Format hint. "auto" detects automatically.
              "jsonl" forces JSON-lines parsing.
              "text" forces plain text parsing.
        field_map: Custom field name mapping.
            Keys: "error_type", "message", "source"
            Values: actual field names in your log.

    Returns:
        Summary dict with imported/skipped/total counts.
    """
    ensure_root(root)
    fmap = {**_DEFAULT_FIELD_MAP, **(field_map or {})}

    format_hint = str(fmt).strip().lower()
    if format_hint not in {"auto", "jsonl", "text"}:
        return {
            "error": f"invalid format: {fmt}. expected one of auto|jsonl|text",
            "imported": 0,
            "skipped": 0,
            "total": 0,
        }

    if not path.exists():
        return {"error": f"file not found: {path}", "imported": 0, "skipped": 0, "total": 0}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    imported = 0
    skipped = 0

    for line in lines:
        if format_hint == "jsonl":
            row = _parse_line_jsonl(line)
        elif format_hint == "text":
            row = _parse_line_text(line)
        else:
            row = _parse_line(line)
        if row is None:
            skipped += 1
            continue

        if not _is_error_line(row, fmap):
            skipped += 1
            continue

        message = _detect_field(row, [fmap.get("message", "message")] + _COMMON_MESSAGE_FIELDS)
        if not message:
            skipped += 1
            continue

        error_type = _detect_field(row, [fmap.get("error_type", "error_type")] + _COMMON_TYPE_FIELDS)
        if not error_type or error_type in {"error", "fatal", "critical"}:
            error_type = _classify_error_type(message)

        source = _detect_field(
            row,
            [fmap.get("source", "source")] + _COMMON_SOURCE_FIELDS,
            fallback="imported_log",
        )

        capture_failure(root, source=source, error_type=error_type, message=message)
        imported += 1

    return {
        "path": str(path),
        "total": len(lines),
        "imported": imported,
        "skipped": skipped,
    }
