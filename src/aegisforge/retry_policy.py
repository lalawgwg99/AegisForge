from __future__ import annotations

import errno
from dataclasses import dataclass

DEFAULT_BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)
DEFAULT_RETRY_HTTP_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for transient retry behavior."""

    max_retries: int = 3
    backoff_seconds: tuple[float, ...] = DEFAULT_BACKOFF_SECONDS
    retry_http_statuses: frozenset[int] = DEFAULT_RETRY_HTTP_STATUS

    @property
    def attempts(self) -> int:
        return max(1, self.max_retries)


def normalize_backoff_seconds(backoff_seconds: tuple[float, ...]) -> tuple[float, ...]:
    """Ensure backoff settings are always valid and non-empty."""
    if not backoff_seconds:
        return DEFAULT_BACKOFF_SECONDS

    sanitized = tuple(max(0.0, float(value)) for value in backoff_seconds)
    if not sanitized:
        return DEFAULT_BACKOFF_SECONDS
    return sanitized


def backoff_for_attempt(backoff_seconds: tuple[float, ...], attempt: int) -> float:
    """Get backoff duration for the current retry attempt."""
    normalized = normalize_backoff_seconds(backoff_seconds)
    index = min(max(0, attempt), len(normalized) - 1)
    return normalized[index]


def should_retry_http_status(status_code: int, policy: RetryPolicy) -> bool:
    """Return true when an HTTP status should be treated as transient."""
    return status_code in policy.retry_http_statuses


def classify_http_status(status_code: int) -> str:
    return f"http_{status_code}"


def should_retry_url_error(reason: object) -> bool:
    """Return true when a URLError reason is likely transient."""
    if isinstance(reason, (TimeoutError, ConnectionError, BrokenPipeError)):
        return True
    if isinstance(reason, OSError):
        transient_errno = {
            errno.ETIMEDOUT,
            errno.ECONNRESET,
            errno.ECONNABORTED,
            errno.ECONNREFUSED,
            errno.EHOSTUNREACH,
            errno.ENETUNREACH,
            errno.ENETDOWN,
        }
        return reason.errno in transient_errno
    return False


def classify_url_error(reason: object) -> str:
    if isinstance(reason, TimeoutError):
        return "timeout"
    if isinstance(reason, ConnectionResetError):
        return "connection_reset"
    if isinstance(reason, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(reason, ConnectionAbortedError):
        return "connection_aborted"
    if isinstance(reason, ConnectionError):
        return "connection_error"
    if isinstance(reason, OSError) and reason.errno is not None:
        return f"oserror_{reason.errno}"
    return "url_error"
