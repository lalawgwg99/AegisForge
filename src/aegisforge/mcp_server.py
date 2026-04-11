"""AegisForge MCP Tool Server.

Exposes AegisForge capabilities as MCP tools for AI agents (Claude Code, etc.).

Usage:
    python -m aegisforge.mcp_server
    # or via entry point:
    aegisforge-mcp

Configuration in Claude Code (~/.claude/settings.json):
    {
      "mcpServers": {
        "aegisforge": {
          "command": "python",
          "args": ["-m", "aegisforge.mcp_server"],
          "env": {
            "AEGISFORGE_ROOT": ".aegisforge"
          }
        }
      }
    }
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print(
        "Error: MCP server requires the 'mcp' package.\n"
        "Install with: pip install 'aegisforge[mcp]'\n"
        "  or: pip install mcp",
        file=sys.stderr,
    )
    sys.exit(1)

from .causal_lane import distill_causal_lanes, preflight_guardrails
from .core import (
    apply_forgetting,
    capture_failure,
    distill_lessons,
    health_report,
    inject_lessons,
)
from .log_import import import_agent_log
from .recovery_graph import (
    propose_recovery_plan,
    record_recovery_outcome,
    recovery_report,
)
from .safety_gate import replay_safety_decision, safety_check

mcp = FastMCP(
    "aegisforge",
    description="Agent Reliability OS: safety gate, causal memory, recovery learning",
)


def _root() -> Path:
    return Path(os.environ.get("AEGISFORGE_ROOT", ".aegisforge"))


# ── Safety ───────────────────────────────────────────────


@mcp.tool()
def aegis_safety_check(
    action: str,
    content: str = "",
    profile: str = "balanced",
) -> dict:
    """Evaluate an action for safety risks before execution.

    Returns decision (allow/ask/block), evidence, and risk score.
    Use this before any destructive or sensitive operation.

    Args:
        action: Description of the action (e.g. "delete production table").
        content: The content/payload being acted on.
        profile: Risk profile — "strict", "balanced", or "dev".
    """
    return safety_check(_root(), action=action, content=content, profile=profile)


@mcp.tool()
def aegis_safety_replay(decision_id: str) -> dict:
    """Replay and verify a previous safety decision by its ID.

    Recomputes the decision from the original inputs and checks
    if the result is consistent (verified: true/false).
    """
    return replay_safety_decision(_root(), decision_id=decision_id)


# ── Preflight ────────────────────────────────────────────


@mcp.tool()
def aegis_preflight(
    action: str,
    content: str = "",
    top_k: int = 4,
) -> dict:
    """Get preflight guardrails before executing an action.

    Returns relevant guardrails from causal memory and lessons
    that should be considered before proceeding.

    Args:
        action: The action about to be executed.
        content: Context or payload for the action.
        top_k: Maximum number of guardrails to return.
    """
    return preflight_guardrails(_root(), action=action, content=content, top_k=top_k)


# ── Capture / Learn ─────────────────────────────────────


@mcp.tool()
def aegis_capture(source: str, error_type: str, message: str) -> dict:
    """Capture a failure event for learning.

    Args:
        source: Where the error originated (e.g. "tool", "api", "agent").
        error_type: Category of error (e.g. "timeout", "unauthorized").
        message: The error message.
    """
    return capture_failure(_root(), source=source, error_type=error_type, message=message)


@mcp.tool()
def aegis_distill(max_lessons: int = 3) -> list[dict]:
    """Distill lessons from captured failure events.

    Analyzes error patterns and generates actionable lessons.
    """
    return distill_lessons(_root(), max_lessons=max_lessons)


@mcp.tool()
def aegis_inject(top_k: int = 3) -> list[dict]:
    """Get top-k lessons for injection into agent context.

    Returns the most relevant lessons sorted by usage and error frequency.
    """
    return inject_lessons(_root(), top_k=top_k)


# ── Recovery ─────────────────────────────────────────────


@mcp.tool()
def aegis_recover(
    failure_class: str,
    strategies: list[str],
    explore_rate: float = 0.15,
) -> dict:
    """Propose a recovery strategy using Thompson Sampling.

    Given a failure type and candidate strategies, returns the best
    strategy based on historical success rates.

    Args:
        failure_class: Type of failure (e.g. "timeout").
        strategies: List of candidate recovery strategies.
        explore_rate: Probability of exploring non-optimal strategies.
    """
    return propose_recovery_plan(
        _root(), failure_class=failure_class, strategies=strategies, explore_rate=explore_rate,
    )


@mcp.tool()
def aegis_record_outcome(
    failure_class: str,
    strategy: str,
    success: bool,
) -> dict:
    """Record whether a recovery strategy succeeded or failed.

    This feedback improves future strategy recommendations.
    """
    return record_recovery_outcome(_root(), failure_class=failure_class, strategy=strategy, success=success)


@mcp.tool()
def aegis_recovery_stats(failure_class: str = "") -> dict:
    """Show recovery statistics for a failure class (or all classes)."""
    return recovery_report(_root(), failure_class=failure_class or None)


# ── Causal Memory ────────────────────────────────────────


@mcp.tool()
def aegis_causal_distill(max_lanes: int = 8, min_support: int = 2) -> dict:
    """Build causal lanes from historical failure events.

    Identifies recurring failure patterns and creates guardrails.
    """
    return distill_causal_lanes(_root(), max_lanes=max_lanes, min_support=min_support)


# ── Health / Maintenance ─────────────────────────────────


@mcp.tool()
def aegis_health() -> dict:
    """Get memory quality report.

    Returns counts of errors, lessons, duplicates, and weak lessons.
    """
    return health_report(_root())


@mcp.tool()
def aegis_forget(max_lessons: int = 50, stale_days: int = 30) -> dict:
    """Apply forgetting curve to prune stale/unused lessons."""
    return apply_forgetting(_root(), max_lessons=max_lessons, stale_days=stale_days)


# ── Log Import ───────────────────────────────────────────


@mcp.tool()
def aegis_import_log(path: str, field_map: dict | None = None) -> dict:
    """Import an external agent log file and extract failures.

    Supports JSONL and plain text logs. Automatically detects error lines.

    Args:
        path: Path to the log file.
        field_map: Optional mapping of field names.
            Example: {"error_type": "level", "message": "msg"}
    """
    return import_agent_log(_root(), path=Path(path), field_map=field_map)


# ── Entry point ──────────────────────────────────────────


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
