from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import re
import uuid

from .storage import append_jsonl, ensure_root, read_jsonl, write_json

ACTION_WORDS = ["use", "verify", "check", "retry", "limit", "validate", "sanitize", "avoid"]


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def capture_failure(root: Path, source: str, error_type: str, message: str) -> dict:
    ensure_root(root)
    row = {
        "id": str(uuid.uuid4()),
        "timestamp": ts(),
        "source": source,
        "error_type": error_type,
        "message": message.strip(),
    }
    append_jsonl(root / "events" / "error-seeds.jsonl", row)
    return row


def _make_lesson_text(error: str) -> str:
    low = error.lower()
    if "timeout" in low:
        return "Use retry with backoff and set explicit timeout boundaries before rerun."
    if "permission" in low or "unauthorized" in low:
        return "Verify credentials and required scopes before executing protected operations."
    if "not found" in low:
        return "Validate file/path/resource existence before running dependent steps."
    if "rate limit" in low:
        return "Throttle requests and implement jittered backoff when rate limits are hit."
    return "Validate inputs and add pre-checks before executing the same workflow again."


def distill_lessons(root: Path, max_lessons: int = 3) -> list[dict]:
    ensure_root(root)
    errors = read_jsonl(root / "events" / "error-seeds.jsonl")
    if not errors:
        return []

    by_type = Counter(e.get("error_type", "unknown") for e in errors)
    top_types = [k for k, _ in by_type.most_common(max_lessons)]

    existing = read_jsonl(root / "lessons" / "active.jsonl")
    existing_text = {x.get("text", "") for x in existing}

    created: list[dict] = []
    for t in top_types:
        sample = next((e for e in errors if e.get("error_type") == t), None)
        if not sample:
            continue
        text = _make_lesson_text(sample.get("message", ""))
        if text in existing_text:
            continue
        lesson = {
            "id": str(uuid.uuid4()),
            "created_at": ts(),
            "error_type": t,
            "text": text,
            "hits": 0,
            "last_used": None,
            "confidence": 0.7,
            "source_errors": by_type[t],
            "tags": [t],
        }
        append_jsonl(root / "lessons" / "active.jsonl", lesson)
        created.append(lesson)

    return created


def inject_lessons(root: Path, top_k: int = 3) -> list[dict]:
    lessons = read_jsonl(root / "lessons" / "active.jsonl")
    lessons.sort(key=lambda x: (x.get("hits", 0), x.get("source_errors", 0)), reverse=True)
    picked = lessons[:top_k]
    for p in picked:
        p["hits"] = int(p.get("hits", 0)) + 1
        p["last_used"] = ts()
    if lessons:
        write_json(root / "lessons" / "snapshot.json", lessons)
    return picked


def health_report(root: Path) -> dict:
    errors = read_jsonl(root / "events" / "error-seeds.jsonl")
    lessons = read_jsonl(root / "lessons" / "active.jsonl")

    duplicates = 0
    seen = set()
    for l in lessons:
        t = re.sub(r"\s+", " ", l.get("text", "").strip().lower())
        if t in seen:
            duplicates += 1
        seen.add(t)

    weak = 0
    for l in lessons:
        txt = l.get("text", "").lower()
        if not any(w in txt for w in ACTION_WORDS):
            weak += 1

    return {
        "errors": len(errors),
        "lessons": len(lessons),
        "duplicates": duplicates,
        "weak_lessons": weak,
    }
