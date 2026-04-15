from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .storage import append_jsonl, read_jsonl

SECRET_PATTERNS = [
    ("secret.sk", r"sk-[a-zA-Z0-9]{20,}"),
    ("secret.password", r"(?i)password\s*[:=]\s*\S{6,}"),
    ("secret.token", r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+"),
]
INJECTION_PATTERNS = [("prompt_injection", r"(?i)ignore\s+previous|system\s*:|you\s+are\s+now")]
DANGEROUS_CMDS = ["rm -rf", "curl | bash", "mkfs", "dd if="]
DESTRUCTIVE_ACTION_WORDS = ["delete", "remove", "drop", "truncate", "format", "exec"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def evaluate_safety(action: str, content: str, profile: str = "balanced") -> dict:
    action_low = _normalize(action or "").lower()
    text = _normalize(content or "")
    low = text.lower()

    evidence = []

    for key, pat in SECRET_PATTERNS:
        m = re.search(pat, text)
        if m:
            evidence.append({"signal": key, "match": m.group(0)[:80], "severity": "critical"})

    for key, pat in INJECTION_PATTERNS:
        m = re.search(pat, text)
        if m:
            evidence.append({"signal": key, "match": m.group(0)[:80], "severity": "critical"})

    cmd_hits = [k for k in DANGEROUS_CMDS if k in low]
    if cmd_hits:
        evidence.append({"signal": "dangerous_command", "match": ",".join(cmd_hits), "severity": "high"})

    action_hits = [k for k in DESTRUCTIVE_ACTION_WORDS if k in action_low]
    if action_hits:
        evidence.append({"signal": "destructive_action", "match": ",".join(action_hits), "severity": "high"})

    decision = "allow"
    reason = "no_risk_signal"

    if any(e["signal"].startswith("secret") for e in evidence):
        decision, reason = "block", "secret_detected"
    elif any(e["signal"] == "prompt_injection" for e in evidence):
        decision, reason = "block", "prompt_injection_pattern"
    elif any(e["signal"] in {"dangerous_command", "destructive_action"} for e in evidence):
        if profile == "strict":
            decision, reason = "block", "destructive_action_in_strict"
        elif profile == "balanced":
            decision, reason = "ask", "destructive_action_requires_approval"
        else:
            decision, reason = "allow", "dev_profile_override"

    risk_score = 0
    for e in evidence:
        if e["severity"] == "critical":
            risk_score += 4
        elif e["severity"] == "high":
            risk_score += 2
        else:
            risk_score += 1

    return {
        "decision": decision,
        "reason": reason,
        "profile": profile,
        "risk_score": risk_score,
        "evidence": evidence,
    }


def _decision_log_path(root: Path) -> Path:
    return root / "policy" / "decisions.jsonl"


def safety_check(root: Path, action: str, content: str, profile: str = "balanced") -> dict:
    evaluated = evaluate_safety(action=action, content=content, profile=profile)
    decision_id = str(uuid.uuid4())
    input_fingerprint = hashlib.sha256(f"{profile}\n{action}\n{content}".encode()).hexdigest()

    row = {
        "decision_id": decision_id,
        "timestamp": _utc_now(),
        "profile": profile,
        "action": action,
        "content": content,
        "input_fingerprint": input_fingerprint,
        "result": evaluated,
    }
    append_jsonl(_decision_log_path(root), row)

    return {
        "decision_id": decision_id,
        "input_fingerprint": input_fingerprint,
        **evaluated,
    }


def replay_safety_decision(root: Path, decision_id: str) -> dict:
    rows = read_jsonl(_decision_log_path(root))
    row = next((r for r in rows if r.get("decision_id") == decision_id), None)
    if not row:
        return {"decision_id": decision_id, "found": False, "verified": False, "reason": "decision_not_found"}

    recomputed = evaluate_safety(
        action=str(row.get("action", "")),
        content=str(row.get("content", "")),
        profile=str(row.get("profile", "balanced")),
    )

    logged = row.get("result", {})
    same = (
        recomputed.get("decision") == logged.get("decision")
        and recomputed.get("reason") == logged.get("reason")
        and recomputed.get("risk_score") == logged.get("risk_score")
        and [e.get("signal") for e in recomputed.get("evidence", [])]
        == [e.get("signal") for e in logged.get("evidence", [])]
    )

    return {
        "decision_id": decision_id,
        "found": True,
        "verified": same,
        "logged_result": logged,
        "recomputed_result": recomputed,
    }
