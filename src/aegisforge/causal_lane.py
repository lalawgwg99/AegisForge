from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .storage import ensure_root, read_jsonl, write_json

STOP = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "have",
    "will",
    "been",
    "when",
    "before",
    "after",
    "into",
    "same",
    "again",
    "should",
    "must",
    "error",
    "failed",
}


def _lane_path(root: Path) -> Path:
    return root / "causal" / "lanes.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP]


def _guardrail_text(error_type: str) -> str:
    low = error_type.lower()
    if "timeout" in low:
        return "執行前先檢查 timeout 與 retry backoff 參數，避免直接重跑。"
    if "unauthorized" in low or "permission" in low:
        return "執行前先驗證 token/權限 scope，避免無效請求重試。"
    if "rate" in low:
        return "執行前先做節流與 jitter backoff，避免被限流。"
    if "not" in low and "found" in low:
        return "執行前先確認目標資源存在（檔案、路徑、ID）。"
    return "執行前先做輸入與前置條件檢查，避免重複同型失敗。"


def distill_causal_lanes(root: Path, max_lanes: int = 8, min_support: int = 2) -> dict:
    ensure_root(root)
    events = read_jsonl(root / "events" / "error-seeds.jsonl")
    if not events:
        payload: dict[str, Any] = {"generated_at": _now(), "lanes": []}
        write_json(_lane_path(root), payload)
        return payload

    by_type: dict[str, list[dict]] = {}
    for e in events:
        t = str(e.get("error_type", "unknown")).strip() or "unknown"
        by_type.setdefault(t, []).append(e)

    lanes = []
    for error_type, rows in by_type.items():
        support = len(rows)
        if support < min_support:
            continue

        token_counter: Counter[str] = Counter()
        for r in rows:
            token_counter.update(_tokenize(str(r.get("message", ""))))
        top_token = token_counter.most_common(1)[0][0] if token_counter else error_type.lower()

        lanes.append(
            {
                "id": str(uuid.uuid4()),
                "failure_class": error_type,
                "trigger_token": top_token,
                "support": support,
                "guardrail": _guardrail_text(error_type),
                "updated_at": _now(),
            }
        )

    lanes.sort(key=lambda x: (x["support"], x["failure_class"]), reverse=True)
    lanes = lanes[:max_lanes]

    payload = {"generated_at": _now(), "lanes": lanes}
    write_json(_lane_path(root), payload)
    return payload


def preflight_guardrails(root: Path, action: str, content: str = "", top_k: int = 4) -> dict:
    action_low = action.lower()
    content_low = (content or "").lower()

    lane_payload: dict[str, Any] = {"lanes": []}
    lane_file = _lane_path(root)
    if lane_file.exists():
        import json

        lane_payload = json.loads(lane_file.read_text(encoding="utf-8"))

    lanes = lane_payload.get("lanes", [])
    scored = []
    for lane in lanes:
        fc = str(lane.get("failure_class", "")).lower()
        token = str(lane.get("trigger_token", "")).lower()
        score = 0
        if fc and (fc in action_low or fc in content_low):
            score += 3
        if token and token in content_low:
            score += 2
        score += min(int(lane.get("support", 0)), 5)
        if score > 0:
            scored.append({"score": score, **lane})

    scored.sort(key=lambda x: (x["score"], x.get("support", 0)), reverse=True)

    lessons = read_jsonl(root / "lessons" / "active.jsonl")
    lessons.sort(key=lambda x: (int(x.get("hits", 0)), int(x.get("source_errors", 0))), reverse=True)

    picked_lanes = scored[:top_k]
    picked_lessons = lessons[: max(0, top_k - len(picked_lanes))]

    injected = []
    for l in picked_lanes:
        injected.append(
            {
                "source": "causal_lane",
                "failure_class": l.get("failure_class"),
                "guardrail": l.get("guardrail"),
                "support": l.get("support", 0),
            }
        )
    for lesson in picked_lessons:
        injected.append(
            {
                "source": "lesson",
                "failure_class": lesson.get("error_type"),
                "guardrail": lesson.get("text"),
                "support": lesson.get("source_errors", 0),
            }
        )

    return {
        "action": action,
        "content": content,
        "injected_guardrails": injected,
        "preflight_brief": "\n".join(f"- {x['guardrail']}" for x in injected),
    }
