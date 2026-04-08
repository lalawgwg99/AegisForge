from __future__ import annotations

import argparse
from pathlib import Path

from .core import (
    apply_forgetting,
    capture_failure,
    distill_lessons,
    health_report,
    inject_lessons,
    policy_decision,
)
from .recovery_graph import (
    benchmark_recovery_learning,
    propose_recovery_plan,
    record_recovery_outcome,
    recovery_report,
)
from .quality import quality_check


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aegisforge", description="AegisForge MVP CLI")
    p.add_argument("--root", default=".aegisforge", help="data root path")

    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture", help="capture one failure event")
    c.add_argument("--source", required=True)
    c.add_argument("--type", required=True, dest="error_type")
    c.add_argument("--message", required=True)

    d = sub.add_parser("distill", help="distill lessons from failures")
    d.add_argument("--max", type=int, default=3)

    i = sub.add_parser("inject", help="pick top-k lessons")
    i.add_argument("--top-k", type=int, default=3)

    f = sub.add_parser("forget", help="apply staleness + LRU forgetting")
    f.add_argument("--max-lessons", type=int, default=50)
    f.add_argument("--stale-days", type=int, default=30)

    pol = sub.add_parser("policy", help="evaluate risk policy for an action")
    pol.add_argument("--action", required=True)
    pol.add_argument("--content", default="")
    pol.add_argument("--profile", choices=["strict", "balanced", "dev"], default="balanced")

    rp = sub.add_parser("recover-plan", help="rank candidate recovery strategies")
    rp.add_argument("--failure-class", required=True)
    rp.add_argument("--strategies", nargs="+", required=True)
    rp.add_argument("--explore-rate", type=float, default=0.15)

    rf = sub.add_parser("recover-feedback", help="record recovery outcome")
    rf.add_argument("--failure-class", required=True)
    rf.add_argument("--strategy", required=True)
    rf.add_argument("--success", choices=["true", "false"], required=True)

    rr = sub.add_parser("recover-report", help="show learned recovery stats")
    rr.add_argument("--failure-class", default="")

    rb = sub.add_parser("benchmark-recovery", help="simulate adaptive-vs-static recovery")
    rb.add_argument("--rounds", type=int, default=200)
    rb.add_argument("--seed", type=int, default=42)

    qc = sub.add_parser("quality-check", help="run default 9.0 quality gate")
    qc.add_argument("--rounds", type=int, default=300)

    sub.add_parser("health", help="memory quality report")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    root = Path(args.root)

    if args.cmd == "capture":
        row = capture_failure(root, args.source, args.error_type, args.message)
        print(f"captured: {row['id']} ({row['error_type']})")
        return

    if args.cmd == "distill":
        lessons = distill_lessons(root, max_lessons=args.max)
        print(f"distilled: {len(lessons)} lesson(s)")
        for l in lessons:
            print(f"- {l['text']}")
        return

    if args.cmd == "inject":
        items = inject_lessons(root, top_k=args.top_k)
        print(f"injected: {len(items)} lesson(s)")
        for l in items:
            print(f"- {l['text']}")
        return

    if args.cmd == "forget":
        r = apply_forgetting(root, max_lessons=args.max_lessons, stale_days=args.stale_days)
        print(r)
        return

    if args.cmd == "policy":
        r = policy_decision(action=args.action, content=args.content, profile=args.profile)
        print(r)
        return

    if args.cmd == "recover-plan":
        r = propose_recovery_plan(
            root,
            failure_class=args.failure_class,
            strategies=args.strategies,
            explore_rate=args.explore_rate,
        )
        print(r)
        return

    if args.cmd == "recover-feedback":
        r = record_recovery_outcome(
            root,
            failure_class=args.failure_class,
            strategy=args.strategy,
            success=args.success == "true",
        )
        print(r)
        return

    if args.cmd == "recover-report":
        r = recovery_report(root, failure_class=(args.failure_class or None))
        print(r)
        return

    if args.cmd == "benchmark-recovery":
        r = benchmark_recovery_learning(root, rounds=args.rounds, seed=args.seed)
        print(r)
        return

    if args.cmd == "quality-check":
        r = quality_check(root, rounds=args.rounds)
        print(r)
        return

    if args.cmd == "health":
        r = health_report(root)
        print(r)
        return


if __name__ == "__main__":
    main()
