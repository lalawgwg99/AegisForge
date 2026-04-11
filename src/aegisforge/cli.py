from __future__ import annotations

import argparse
import json
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
from .causal_lane import distill_causal_lanes, preflight_guardrails
from .log_import import import_agent_log
from .llm_extract import distill_with_llm
from .quality import quality_check
from .safety_gate import replay_safety_decision, safety_check
from .benchmark_pack import run_benchmark_pack
from .dream_mode import complete_action, generate_dream_report, list_actions


def _parse_bool_flag(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected boolean value: true/false/yes/no/1/0")


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
    rf.add_argument(
        "--success",
        type=_parse_bool_flag,
        required=True,
        help="recovery success (true/false, yes/no, 1/0)",
    )

    rr = sub.add_parser("recover-report", help="show learned recovery stats")
    rr.add_argument("--failure-class", default="")

    rb = sub.add_parser("benchmark-recovery", help="simulate adaptive-vs-static recovery")
    rb.add_argument("--rounds", type=int, default=200)
    rb.add_argument("--seed", type=int, default=42)

    qc = sub.add_parser("quality-check", help="run default 9.0 quality gate")
    qc.add_argument("--rounds", type=int, default=300)

    cd = sub.add_parser("causal-distill", help="build causal lanes from historical failures")
    cd.add_argument("--max-lanes", type=int, default=8)
    cd.add_argument("--min-support", type=int, default=2)

    pf = sub.add_parser("preflight", help="inject guardrails before execution")
    pf.add_argument("--action", required=True)
    pf.add_argument("--content", default="")
    pf.add_argument("--top-k", type=int, default=4)

    sg = sub.add_parser("safety-check", help="evaluate action with verifiable safety gate")
    sg.add_argument("--action", required=True)
    sg.add_argument("--content", default="")
    sg.add_argument("--profile", choices=["strict", "balanced", "dev"], default="balanced")

    sr = sub.add_parser("safety-replay", help="replay a logged safety decision by id")
    sr.add_argument("--decision-id", required=True)

    bp = sub.add_parser("benchmark-pack", help="run scenario benchmark pack and generate report")
    bp.add_argument("--rounds", type=int, default=300)
    bp.add_argument("--report-path", default="")

    dr = sub.add_parser("dream-report", help="dream mode orchestration (dream primary + AegisForge repo signal secondary)")
    dr.add_argument("--repo-path", default=".", help="target repo path for auxiliary health signals")
    dr.add_argument("--output-dir", default="", help="optional output directory for dream markdown")
    dr.add_argument("--top-k", type=int, default=3)

    da = sub.add_parser("dream-actions", help="list dream action ledger items")
    da.add_argument("--status", choices=["pending", "completed", "all"], default="pending")
    da.add_argument("--limit", type=int, default=20)

    dc = sub.add_parser("dream-complete", help="mark dream action as completed by id")
    dc.add_argument("--id", required=True, dest="action_id")

    il = sub.add_parser("import-log", help="import external agent log and extract failures")
    il.add_argument("--path", required=True, help="path to the log file (JSONL or text)")
    il.add_argument("--format", choices=["auto", "jsonl", "text"], default="auto", dest="log_format")
    il.add_argument("--field-map", default="", help='JSON field mapping, e.g. \'{"message":"msg","error_type":"level"}\'')

    dl = sub.add_parser("distill-llm", help="distill lessons using LLM extraction")
    dl.add_argument("--max", type=int, default=3)
    dl.add_argument("--api-url", default="", help="OpenAI-compatible API URL")
    dl.add_argument("--api-key", default="", help="API key")
    dl.add_argument("--model", default="", help="model name")

    sub.add_parser("health", help="memory quality report")
    return p


def _print_result(value: object) -> None:
    if isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    print(value)


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
        _print_result(r)
        return

    if args.cmd == "policy":
        r = policy_decision(action=args.action, content=args.content, profile=args.profile)
        _print_result(r)
        return

    if args.cmd == "recover-plan":
        r = propose_recovery_plan(
            root,
            failure_class=args.failure_class,
            strategies=args.strategies,
            explore_rate=args.explore_rate,
        )
        _print_result(r)
        return

    if args.cmd == "recover-feedback":
        r = record_recovery_outcome(
            root,
            failure_class=args.failure_class,
            strategy=args.strategy,
            success=args.success,
        )
        _print_result(r)
        return

    if args.cmd == "recover-report":
        r = recovery_report(root, failure_class=(args.failure_class or None))
        _print_result(r)
        return

    if args.cmd == "benchmark-recovery":
        r = benchmark_recovery_learning(root, rounds=args.rounds, seed=args.seed)
        _print_result(r)
        return

    if args.cmd == "quality-check":
        r = quality_check(root, rounds=args.rounds)
        _print_result(r)
        return

    if args.cmd == "causal-distill":
        r = distill_causal_lanes(root, max_lanes=args.max_lanes, min_support=args.min_support)
        _print_result(r)
        return

    if args.cmd == "preflight":
        r = preflight_guardrails(root, action=args.action, content=args.content, top_k=args.top_k)
        _print_result(r)
        return

    if args.cmd == "safety-check":
        r = safety_check(root, action=args.action, content=args.content, profile=args.profile)
        _print_result(r)
        return

    if args.cmd == "safety-replay":
        r = replay_safety_decision(root, decision_id=args.decision_id)
        _print_result(r)
        return

    if args.cmd == "benchmark-pack":
        r = run_benchmark_pack(root, rounds=args.rounds, report_path=args.report_path)
        _print_result(r)
        return

    if args.cmd == "dream-report":
        output_dir = Path(args.output_dir) if args.output_dir else None
        r = generate_dream_report(
            root,
            repo_path=Path(args.repo_path),
            output_dir=output_dir,
            top_k=args.top_k,
        )
        _print_result(r)
        return

    if args.cmd == "dream-actions":
        status = "all" if args.status == "all" else args.status
        r = list_actions(root, status=status, limit=args.limit)
        _print_result(r)
        return

    if args.cmd == "dream-complete":
        r = complete_action(root, action_id=args.action_id)
        _print_result(r)
        return

    if args.cmd == "import-log":
        field_map = None
        if args.field_map:
            import json as _json
            field_map = _json.loads(args.field_map)
        r = import_agent_log(root, path=Path(args.path), fmt=args.log_format, field_map=field_map)
        _print_result(r)
        return

    if args.cmd == "distill-llm":
        lessons = distill_with_llm(
            root, max_lessons=args.max,
            api_url=args.api_url, api_key=args.api_key, model=args.model,
        )
        print(f"distilled (LLM): {len(lessons)} lesson(s)")
        for l in lessons:
            print(f"- {l['text']}")
        return

    if args.cmd == "health":
        r = health_report(root)
        _print_result(r)
        return


if __name__ == "__main__":
    main()
