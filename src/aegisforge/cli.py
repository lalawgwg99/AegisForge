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

    if args.cmd == "health":
        r = health_report(root)
        print(r)
        return


if __name__ == "__main__":
    main()
