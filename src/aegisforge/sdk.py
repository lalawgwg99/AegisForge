"""AegisForge Python SDK — programmatic API for AI agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    benchmark_recovery_learning,
    propose_recovery_plan,
    record_recovery_outcome,
    recovery_report,
)
from .safety_gate import safety_check as _safety_check


@dataclass(frozen=True)
class SafetyResult:
    """Result of a safety evaluation."""

    decision: str
    reason: str
    profile: str
    risk_score: int
    evidence: list[dict[str, Any]]
    decision_id: str | None = None
    input_fingerprint: str | None = None

    @property
    def blocked(self) -> bool:
        return self.decision == "block"

    @property
    def needs_approval(self) -> bool:
        return self.decision == "ask"

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "profile": self.profile,
            "risk_score": self.risk_score,
            "evidence": self.evidence,
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class PreflightResult:
    """Result of a preflight guardrail check."""

    action: str
    content: str
    guardrails: list[dict[str, Any]]
    brief: str

    @property
    def has_guardrails(self) -> bool:
        return len(self.guardrails) > 0

    @property
    def count(self) -> int:
        return len(self.guardrails)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "guardrails": self.guardrails,
            "brief": self.brief,
        }


@dataclass(frozen=True)
class RecoveryPlan:
    """Ranked recovery strategy plan."""

    failure_class: str
    chosen_strategy: str
    mode: str
    ranked: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_class": self.failure_class,
            "chosen_strategy": self.chosen_strategy,
            "mode": self.mode,
            "ranked": self.ranked,
        }


@dataclass
class LLMConfig:
    """Configuration for LLM-based lesson extraction."""

    api_url: str = "http://localhost:11434/v1/chat/completions"
    api_key: str = ""
    model: str = "gemma4:e4b"
    enabled: bool = False


class AegisForge:
    """Main SDK entry point.

    Usage::

        from aegisforge import AegisForge

        af = AegisForge(".aegisforge")

        # Safety gate
        result = af.safety_check("delete table", "DROP TABLE users")
        if result.blocked:
            raise RuntimeError(f"Blocked: {result.reason}")

        # Preflight guardrails
        guard = af.preflight("run sync", "api timeout config")
        print(guard.brief)

        # Capture errors and learn
        af.capture("tool", "timeout", "request timeout 30s")
        af.distill()
        lessons = af.inject(top_k=3)
    """

    def __init__(
        self,
        root: str | Path = ".aegisforge",
        llm: LLMConfig | None = None,
    ) -> None:
        self.root = Path(root)
        self.llm = llm or LLMConfig()

    # ── Safety ───────────────────────────────────────────

    def safety_check(
        self,
        action: str,
        content: str = "",
        profile: str = "balanced",
    ) -> SafetyResult:
        """Evaluate an action for safety risks.

        Returns a SafetyResult with decision (allow/ask/block), evidence, and risk score.
        """
        raw = _safety_check(self.root, action=action, content=content, profile=profile)
        return SafetyResult(
            decision=raw["decision"],
            reason=raw["reason"],
            profile=raw["profile"],
            risk_score=raw["risk_score"],
            evidence=raw["evidence"],
            decision_id=raw.get("decision_id"),
            input_fingerprint=raw.get("input_fingerprint"),
        )

    # ── Preflight ────────────────────────────────────────

    def preflight(
        self,
        action: str,
        content: str = "",
        top_k: int = 4,
    ) -> PreflightResult:
        """Get preflight guardrails for an action based on historical failures."""
        raw = preflight_guardrails(self.root, action=action, content=content, top_k=top_k)
        return PreflightResult(
            action=raw["action"],
            content=raw["content"],
            guardrails=raw["injected_guardrails"],
            brief=raw["preflight_brief"],
        )

    # ── Capture / Distill / Inject ───────────────────────

    def capture(self, source: str, error_type: str, message: str) -> dict[str, Any]:
        """Capture a failure event."""
        return capture_failure(self.root, source, error_type, message)

    def distill(self, max_lessons: int = 3) -> list[dict[str, Any]]:
        """Distill lessons from captured failure events.

        If LLM is configured, uses LLM-based extraction for richer lessons.
        """
        if self.llm.enabled:
            from .llm_extract import distill_with_llm

            return distill_with_llm(
                self.root,
                max_lessons=max_lessons,
                api_url=self.llm.api_url,
                api_key=self.llm.api_key,
                model=self.llm.model,
            )
        return distill_lessons(self.root, max_lessons=max_lessons)

    def inject(self, top_k: int = 3) -> list[dict[str, Any]]:
        """Pick top-k lessons for injection into agent context."""
        return inject_lessons(self.root, top_k=top_k)

    # ── Recovery ─────────────────────────────────────────

    def recover(
        self,
        failure_class: str,
        strategies: list[str],
        explore_rate: float = 0.15,
    ) -> RecoveryPlan:
        """Propose a recovery strategy using Thompson Sampling."""
        raw = propose_recovery_plan(
            self.root,
            failure_class=failure_class,
            strategies=strategies,
            explore_rate=explore_rate,
        )
        return RecoveryPlan(
            failure_class=raw["failure_class"],
            chosen_strategy=raw["chosen_strategy"],
            mode=raw["mode"],
            ranked=raw["ranked_strategies"],
        )

    def record_outcome(
        self,
        failure_class: str,
        strategy: str,
        success: bool,
    ) -> dict[str, Any]:
        """Record whether a recovery strategy succeeded."""
        return record_recovery_outcome(self.root, failure_class, strategy, success)

    def recovery_stats(self, failure_class: str | None = None) -> dict[str, Any]:
        """Get recovery statistics."""
        return recovery_report(self.root, failure_class=failure_class)

    # ── Causal Lanes ─────────────────────────────────────

    def causal_distill(
        self,
        max_lanes: int = 8,
        min_support: int = 2,
    ) -> dict[str, Any]:
        """Build causal lanes from historical failures."""
        return distill_causal_lanes(self.root, max_lanes=max_lanes, min_support=min_support)

    # ── Health / Forget ──────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Get memory quality report."""
        return health_report(self.root)

    def forget(self, max_lessons: int = 50, stale_days: int = 30) -> dict[str, Any]:
        """Apply forgetting curve to lessons."""
        return apply_forgetting(self.root, max_lessons=max_lessons, stale_days=stale_days)

    # ── Benchmark ────────────────────────────────────────

    def benchmark(self, rounds: int = 300, seed: int = 42) -> dict[str, Any]:
        """Run recovery benchmark."""
        return benchmark_recovery_learning(self.root, rounds=rounds, seed=seed)

    # ── Log Import ───────────────────────────────────────

    def import_log(
        self,
        path: str | Path,
        format: str = "auto",
        field_map: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Import external agent logs and extract failures.

        Supports JSONL agent logs. Use field_map to map custom fields::

            af.import_log("agent.log", field_map={
                "error_type": "level",
                "message": "msg",
                "source": "component",
            })
        """
        return import_agent_log(
            self.root,
            path=Path(path),
            fmt=format,
            field_map=field_map,
        )
