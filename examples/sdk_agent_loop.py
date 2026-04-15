from __future__ import annotations

from aegisforge import AegisForge


def main() -> None:
    af = AegisForge(".aegisforge")

    action = "run sync"
    content = "sync user profile with upstream api"

    safety = af.safety_check(action, content, profile="balanced")
    if safety.blocked:
        print(f"blocked: {safety.reason}")
        return
    if safety.needs_approval:
        print(f"needs approval: {safety.reason}")

    guard = af.preflight(action, content, top_k=3)
    if guard.has_guardrails:
        print("preflight guardrails:")
        print(guard.brief)

    try:
        raise TimeoutError("request timeout after 30s on /sync")
    except TimeoutError as error:
        af.capture("agent", "timeout", str(error))
        af.distill(max_lessons=3)
        plan = af.recover("timeout", ["retry_backoff", "restart_worker", "escalate_human"])
        print(f"recovery plan: {plan.chosen_strategy} ({plan.mode})")
        af.record_outcome("timeout", plan.chosen_strategy, success=True)


if __name__ == "__main__":
    main()
