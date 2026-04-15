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
from pathlib import Path

from .core import _find_semantic_duplicate, ts
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


def _call_llm(
    messages: list[dict[str, str]],
    api_url: str,
    api_key: str,
    model: str,
    max_retries: int = 3,
    backoff_seconds: tuple[float, ...] = (1.0, 2.0, 4.0),
) -> str | None:
    """Call an OpenAI-compatible chat completions API with retry/backoff."""
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
    attempts = max(1, max_retries)

    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as error:
            # 401/403 should fail fast; retrying won't fix invalid auth/scope.
            if error.code in {401, 403}:
                return None
            if error.code >= 500 and attempt < attempts - 1:
                wait = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                time.sleep(wait)
                continue
            return None
        except urllib.error.URLError as error:
            reason = getattr(error, "reason", None)
            is_timeout = isinstance(reason, TimeoutError)
            if is_timeout and attempt < attempts - 1:
                wait = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                time.sleep(wait)
                continue
            return None
        except TimeoutError:
            if attempt < attempts - 1:
                wait = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                time.sleep(wait)
                continue
            return None
        except (KeyError, json.JSONDecodeError):
            return None
    return None


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

    raw = _call_llm(messages, api_url=api_url, api_key=api_key, model=model)
    if raw is None:
        return None

    return _extract_json_array(raw)


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

    llm_lessons = extract_lessons_from_errors(
        errors, api_url=api_url, api_key=api_key, model=model, max_lessons=max_lessons,
    )

    if llm_lessons is None:
        from .core import distill_lessons
        return distill_lessons(root, max_lessons=max_lessons)

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
