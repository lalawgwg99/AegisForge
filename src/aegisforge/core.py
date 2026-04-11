from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import uuid

from .storage import append_jsonl, ensure_root, read_jsonl, write_json, write_jsonl

ACTION_WORDS = ["use", "verify", "check", "retry", "limit", "validate", "sanitize", "avoid"]
STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "will", "been", "when", "before",
    "after", "always", "instead", "using", "avoid", "your", "into", "same", "again", "should", "must",
}


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(raw: str | None) -> datetime:
    if not raw:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return {w for w in words if w not in STOP_WORDS}


def _similarity(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _find_semantic_duplicate(text: str, lessons: list[dict], threshold: float = 0.62) -> dict | None:
    for l in lessons:
        score = _similarity(text, l.get("text", ""))
        if score >= threshold:
            return l
    return None


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

    created: list[dict] = []
    for t in top_types:
        sample = next((e for e in errors if e.get("error_type") == t), None)
        if not sample:
            continue
        text = _make_lesson_text(sample.get("message", ""))

        dup = _find_semantic_duplicate(text, existing, threshold=0.62)
        if dup:
            dup["source_errors"] = int(dup.get("source_errors", 0)) + int(by_type[t])
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
        existing.append(lesson)
        created.append(lesson)

    if existing:
        write_jsonl(root / "lessons" / "active.jsonl", existing)

    return created


def inject_lessons(root: Path, top_k: int = 3) -> list[dict]:
    lessons = read_jsonl(root / "lessons" / "active.jsonl")
    lessons.sort(key=lambda x: (x.get("hits", 0), x.get("source_errors", 0)), reverse=True)
    picked = lessons[:top_k]
    now = ts()
    picked_ids = {p.get("id") for p in picked}

    for l in lessons:
        if l.get("id") in picked_ids:
            l["hits"] = int(l.get("hits", 0)) + 1
            l["last_used"] = now

    if lessons:
        write_jsonl(root / "lessons" / "active.jsonl", lessons)
        write_json(root / "lessons" / "snapshot.json", lessons)
    return picked


def apply_forgetting(root: Path, max_lessons: int = 50, stale_days: int = 30) -> dict:
    lessons = read_jsonl(root / "lessons" / "active.jsonl")
    if not lessons:
        return {"before": 0, "stale_removed": 0, "lru_removed": 0, "after": 0}

    before = len(lessons)
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)

    kept: list[dict] = []
    stale_removed = 0
    for l in lessons:
        last_touch = _parse_ts(l.get("last_used") or l.get("created_at"))
        if last_touch < cutoff and int(l.get("hits", 0)) <= 0:
            stale_removed += 1
            continue
        kept.append(l)

    kept.sort(key=lambda x: _parse_ts(x.get("last_used") or x.get("created_at")), reverse=True)
    lru_removed = 0
    if len(kept) > max_lessons:
        lru_removed = len(kept) - max_lessons
        kept = kept[:max_lessons]

    write_jsonl(root / "lessons" / "active.jsonl", kept)
    write_json(root / "lessons" / "snapshot.json", kept)

    return {
        "before": before,
        "stale_removed": stale_removed,
        "lru_removed": lru_removed,
        "after": len(kept),
    }


def policy_decision(action: str, content: str, profile: str = "balanced") -> dict:
    from .safety_gate import evaluate_safety

    result = evaluate_safety(action=action, content=content, profile=profile)
    return {"decision": result["decision"], "reason": result["reason"], "profile": result["profile"]}


def health_report(root: Path) -> dict:
    errors = read_jsonl(root / "events" / "error-seeds.jsonl")
    lessons = read_jsonl(root / "lessons" / "active.jsonl")

    exact_duplicates = 0
    seen = set()
    for l in lessons:
        t = re.sub(r"\s+", " ", l.get("text", "").strip().lower())
        if t in seen:
            exact_duplicates += 1
        seen.add(t)

    semantic_duplicates = 0
    for i in range(len(lessons)):
        for j in range(i + 1, len(lessons)):
            if _similarity(lessons[i].get("text", ""), lessons[j].get("text", "")) >= 0.72:
                semantic_duplicates += 1

    weak = 0
    for l in lessons:
        txt = l.get("text", "").lower()
        if not any(w in txt for w in ACTION_WORDS):
            weak += 1

    return {
        "errors": len(errors),
        "lessons": len(lessons),
        "duplicates_exact": exact_duplicates,
        "duplicates_semantic_pairs": semantic_duplicates,
        "weak_lessons": weak,
    }
