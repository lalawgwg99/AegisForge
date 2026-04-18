"""LLM-based lesson extraction from error events.

Falls back to template-based extraction if LLM is unavailable.
Supports any OpenAI-compatible API (OpenAI, Ollama, vLLM, LiteLLM, etc.).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .core import _find_semantic_duplicate, ts
from .retry_policy import (
    RetryPolicy,
    backoff_for_attempt,
    classify_http_status,
    classify_url_error,
    normalize_backoff_seconds,
    should_retry_http_status,
    should_retry_url_error,
)
from .storage import ensure_root, read_jsonl, write_jsonl

_SYSTEM_PROMPT = """\
You are an expert at extracting actionable lessons from software failure events.

Given a list of error events, produce concise, actionable lessons that an AI agent \
can use to avoid repeating the same mistakes.

Rules:
- Each lesson MUST start with an action verb (Use, Verify, Check, Limit, Validate, etc.)
- Each lesson MUST be one sentence, under 120 characters
- Focus on prevention, not description
- Deduplicate: merge similar errors into one lesson
- Output valid JSON array of strings, nothing else

Example input:
[{"error_type": "timeout", "message": "request timeout after 30s on api call"}]

Example output:
["Use retry with exponential backoff and set explicit timeout of 15s before API calls."]
"""


@dataclass(frozen=True)
class LLMCallMeta:
    attempts: int
    retries: int
    error_counts: dict[str, int]
    succeeded: bool
    fallback_used: bool = False
    fallback_reason: str = ""


@dataclass(frozen=True)
class LLMCallResult:
    content: str | None
    meta: LLMCallMeta


def _accumulate_error(error_counts: dict[str, int], key: str) -> dict[str, int]:
    updated = dict(error_counts)
    updated[key] = updated.get(key, 0) + 1
    return updated


def _record_llm_extract_stats(root: Path, meta: LLMCallMeta) -> None:
    stats_path = root / "reports" / "llm-extract-stats.json"
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            stats = {}
    else:
        stats = {}

    totals = stats.get("totals", {})
    requests = int(totals.get("requests", 0)) + 1
    llm_success = int(totals.get("llm_success", 0)) + int(meta.succeeded and not meta.fallback_used)
    fallbacks = int(totals.get("fallbacks", 0)) + int(meta.fallback_used)
    retries = int(totals.get("retries", 0)) + meta.retries
    attempts = int(totals.get("attempts", 0)) + meta.attempts

    error_classifications = stats.get("error_classifications", {})
    merged_errors: dict[str, int] = {
        str(key): int(value)
        for key, value in error_classifications.items()
    }
    for key, value in meta.error_counts.items():
        merged_errors[key] = merged_errors.get(key, 0) + int(value)

    fallback_reasons = stats.get("fallback_reasons", {})
    merged_fallback_reasons: dict[str, int] = {
        str(key): int(value)
        for key, value in fallback_reasons.items()
    }
    if meta.fallback_used:
        reason = meta.fallback_reason or "unknown"
        merged_fallback_reasons[reason] = merged_fallback_reasons.get(reason, 0) + 1

    output = {
        "updated_at": ts(),
        "totals": {
            "requests": requests,
            "llm_success": llm_success,
            "fallbacks": fallbacks,
            "fallback_ratio": round(fallbacks / requests, 4),
            "retries": retries,
            "attempts": attempts,
            "avg_attempts_per_request": round(attempts / requests, 4),
        },
        "error_classifications": dict(sorted(merged_errors.items())),
        "fallback_reasons": dict(sorted(merged_fallback_reasons.items())),
    }
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


def _call_llm_with_meta(
    messages: list[dict[str, str]],
    api_url: str,
    api_key: str,
    model: str,
    policy: RetryPolicy,
) -> LLMCallResult:
    url = api_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = url.rstrip("/") + "/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 512,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    retries = 0
    attempts = 0
    error_counts: dict[str, int] = {}

    for attempt in range(policy.attempts):
        attempts += 1
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                return LLMCallResult(
                    content=content,
                    meta=LLMCallMeta(
                        attempts=attempts,
                        retries=retries,
                        error_counts=error_counts,
                        succeeded=True,
                    ),
                )
        except urllib.error.HTTPError as error:
            error_counts = _accumulate_error(error_counts, classify_http_status(error.code))
            if error.code in {401, 403}:
                return LLMCallResult(
                    content=None,
                    meta=LLMCallMeta(
                        attempts=attempts,
                        retries=retries,
                        error_counts=error_counts,
                        succeeded=False,
                        fallback_used=True,
                        fallback_reason="auth",
                    ),
                )
            if should_retry_http_status(error.code, policy) and attempt < policy.attempts - 1:
                retries += 1
                time.sleep(backoff_for_attempt(policy.backoff_seconds, attempt))
                continue
            return LLMCallResult(
                content=None,
                meta=LLMCallMeta(
                    attempts=attempts,
                    retries=retries,
                    error_counts=error_counts,
                    succeeded=False,
                    fallback_used=True,
                    fallback_reason=classify_http_status(error.code),
                ),
            )
        except urllib.error.URLError as error:
            reason = getattr(error, "reason", None)
            error_counts = _accumulate_error(error_counts, classify_url_error(reason))
            if should_retry_url_error(reason) and attempt < policy.attempts - 1:
                retries += 1
                time.sleep(backoff_for_attempt(policy.backoff_seconds, attempt))
                continue
            return LLMCallResult(
                content=None,
                meta=LLMCallMeta(
                    attempts=attempts,
                    retries=retries,
                    error_counts=error_counts,
                    succeeded=False,
                    fallback_used=True,
                    fallback_reason=classify_url_error(reason),
                ),
            )
        except TimeoutError:
            error_counts = _accumulate_error(error_counts, "timeout")
            if attempt < policy.attempts - 1:
                retries += 1
                time.sleep(backoff_for_attempt(policy.backoff_seconds, attempt))
                continue
            return LLMCallResult(
                content=None,
                meta=LLMCallMeta(
                    attempts=attempts,
                    retries=retries,
                    error_counts=error_counts,
                    succeeded=False,
                    fallback_used=True,
                    fallback_reason="timeout",
                ),
            )
        except (KeyError, json.JSONDecodeError):
            error_counts = _accumulate_error(error_counts, "malformed_response")
            return LLMCallResult(
                content=None,
                meta=LLMCallMeta(
                    attempts=attempts,
                    retries=retries,
                    error_counts=error_counts,
                    succeeded=False,
                    fallback_used=True,
                    fallback_reason="malformed_response",
                ),
            )

    return LLMCallResult(
        content=None,
        meta=LLMCallMeta(
            attempts=attempts,
            retries=retries,
            error_counts=error_counts,
            succeeded=False,
            fallback_used=True,
            fallback_reason="exhausted_retries",
        ),
    )


def _call_llm(
    messages: list[dict[str, str]],
    api_url: str,
    api_key: str,
    model: str,
    max_retries: int = 3,
    backoff_seconds: tuple[float, ...] = (1.0, 2.0, 4.0),
) -> str | None:
    """Call an OpenAI-compatible chat completions API with retry/backoff."""
    policy = RetryPolicy(
        max_retries=max_retries,
        backoff_seconds=normalize_backoff_seconds(backoff_seconds),
    )
    result = _call_llm_with_meta(messages, api_url=api_url, api_key=api_key, model=model, policy=policy)
    return result.content


def _extract_json_array(text: str) -> list[str] | None:
    """Extract a JSON array from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            return parsed
    except json.JSONDecodeError:
        pass
    return None


def extract_lessons_from_errors(
    errors: list[dict],
    api_url: str,
    api_key: str,
    model: str,
    max_lessons: int = 5,
) -> list[str] | None:
    """Use LLM to extract lessons from error events. Returns None on failure."""
    if not errors:
        return None

    samples = errors[-20:]
    events_text = json.dumps(
        [{"error_type": e.get("error_type", ""), "message": e.get("message", "")} for e in samples],
        ensure_ascii=False,
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract up to {max_lessons} lessons from these errors:\n{events_text}"},
    ]

    policy = RetryPolicy(max_retries=3, backoff_seconds=normalize_backoff_seconds((1.0, 2.0, 4.0)))
    result = _call_llm_with_meta(messages, api_url=api_url, api_key=api_key, model=model, policy=policy)
    if result.content is None:
        return None
    return _extract_json_array(result.content)


def distill_with_llm(
    root: Path,
    max_lessons: int = 3,
    api_url: str = "",
    api_key: str = "",
    model: str = "",
) -> list[dict]:
    """Distill lessons using LLM extraction with template fallback.

    Environment variables used as fallback:
      - AEGISFORGE_LLM_URL
      - AEGISFORGE_LLM_KEY
      - AEGISFORGE_LLM_MODEL
    """
    api_url = api_url or os.environ.get("AEGISFORGE_LLM_URL", "http://localhost:11434/v1")
    api_key = api_key or os.environ.get("AEGISFORGE_LLM_KEY", "")
    model = model or os.environ.get("AEGISFORGE_LLM_MODEL", "gemma4:e4b")

    ensure_root(root)
    errors = read_jsonl(root / "events" / "error-seeds.jsonl")
    if not errors:
        return []

    existing = read_jsonl(root / "lessons" / "active.jsonl")

    call_result = _call_llm_with_meta(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Extract up to {max_lessons} lessons from these errors:\n"
                    + json.dumps(
                        [
                            {
                                "error_type": error.get("error_type", ""),
                                "message": error.get("message", ""),
                            }
                            for error in errors[-20:]
                        ],
                        ensure_ascii=False,
                    )
                ),
            },
        ],
        api_url=api_url,
        api_key=api_key,
        model=model,
        policy=RetryPolicy(max_retries=3, backoff_seconds=normalize_backoff_seconds((1.0, 2.0, 4.0))),
    )
    llm_lessons = _extract_json_array(call_result.content) if call_result.content else None

    if llm_lessons is None:
        _record_llm_extract_stats(root, call_result.meta)
        from .core import distill_lessons
        return distill_lessons(root, max_lessons=max_lessons)
    _record_llm_extract_stats(
        root,
        LLMCallMeta(
            attempts=call_result.meta.attempts,
            retries=call_result.meta.retries,
            error_counts=call_result.meta.error_counts,
            succeeded=True,
            fallback_used=False,
            fallback_reason="",
        ),
    )

    by_type = Counter(e.get("error_type", "unknown") for e in errors)
    created: list[dict] = []

    for text in llm_lessons[:max_lessons]:
        text = text.strip()
        if not text:
            continue

        dup = _find_semantic_duplicate(text, existing, threshold=0.62)
        if dup:
            dup["source_errors"] = int(dup.get("source_errors", 0)) + 1
            continue

        best_type = max(by_type, key=lambda error_type: by_type[error_type]) if by_type else "unknown"

        lesson = {
            "id": str(uuid.uuid4()),
            "created_at": ts(),
            "error_type": best_type,
            "text": text,
            "hits": 0,
            "last_used": None,
            "confidence": 0.8,
            "source_errors": by_type.get(best_type, 1),
            "tags": [best_type, "llm"],
            "extraction": "llm",
        }
        existing.append(lesson)
        created.append(lesson)

    if existing:
        write_jsonl(root / "lessons" / "active.jsonl", existing)

    return created


def read_llm_extract_stats(root: Path) -> dict:
    stats_path = root / "reports" / "llm-extract-stats.json"
    if not stats_path.exists():
        return {
            "updated_at": "",
            "totals": {
                "requests": 0,
                "llm_success": 0,
                "fallbacks": 0,
                "fallback_ratio": 0.0,
                "retries": 0,
                "attempts": 0,
                "avg_attempts_per_request": 0.0,
            },
            "error_classifications": {},
            "fallback_reasons": {},
        }
    try:
        return json.loads(stats_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "updated_at": ts(),
            "totals": {
                "requests": 0,
                "llm_success": 0,
                "fallbacks": 0,
                "fallback_ratio": 0.0,
                "retries": 0,
                "attempts": 0,
                "avg_attempts_per_request": 0.0,
            },
            "error_classifications": {},
            "fallback_reasons": {"malformed_stats_file": 1},
        }
