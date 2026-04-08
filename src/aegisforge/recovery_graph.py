from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

from .storage import ensure_root, write_json


def _graph_path(root: Path) -> Path:
    return root / "recovery" / "graph.json"


def _load_graph(root: Path) -> dict:
    path = _graph_path(root)
    if not path.exists():
        return {"failure_classes": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"failure_classes": {}}


def _save_graph(root: Path, data: dict) -> None:
    write_json(_graph_path(root), data)


def _ensure_strategy_bucket(data: dict, failure_class: str, strategy: str) -> dict:
    classes = data.setdefault("failure_classes", {})
    fc = classes.setdefault(failure_class, {"strategies": {}, "updated_at": None})
    bucket = fc.setdefault("strategies", {}).setdefault(
        strategy,
        {"attempts": 0, "successes": 0, "failures": 0, "last_result": None},
    )
    return bucket


def _score(bucket: dict) -> float:
    # Beta posterior mean with prior Beta(1,1)
    return (int(bucket.get("successes", 0)) + 1) / (int(bucket.get("attempts", 0)) + 2)


def propose_recovery_plan(
    root: Path,
    failure_class: str,
    strategies: list[str],
    explore_rate: float = 0.15,
) -> dict:
    ensure_root(root)
    data = _load_graph(root)

    clean_strategies = [s.strip() for s in strategies if s.strip()]
    if not clean_strategies:
        raise ValueError("strategies must contain at least one non-empty strategy")

    for s in clean_strategies:
        _ensure_strategy_bucket(data, failure_class, s)

    buckets = data["failure_classes"][failure_class]["strategies"]
    ranked = []
    for s in clean_strategies:
        b = buckets[s]
        ranked.append(
            {
                "strategy": s,
                "score": round(_score(b), 4),
                "attempts": int(b.get("attempts", 0)),
                "successes": int(b.get("successes", 0)),
                "failures": int(b.get("failures", 0)),
            }
        )

    ranked.sort(key=lambda x: (x["score"], x["successes"], -x["failures"]), reverse=True)

    chosen = ranked[0]["strategy"]
    mode = "exploit"
    if len(ranked) > 1 and random.random() < explore_rate:
        chosen = random.choice(ranked[1:])["strategy"]
        mode = "explore"

    _save_graph(root, data)

    return {
        "failure_class": failure_class,
        "explore_rate": explore_rate,
        "mode": mode,
        "chosen_strategy": chosen,
        "ranked_strategies": ranked,
    }


def record_recovery_outcome(root: Path, failure_class: str, strategy: str, success: bool) -> dict:
    ensure_root(root)
    data = _load_graph(root)
    bucket = _ensure_strategy_bucket(data, failure_class, strategy)

    bucket["attempts"] = int(bucket.get("attempts", 0)) + 1
    if success:
        bucket["successes"] = int(bucket.get("successes", 0)) + 1
        bucket["last_result"] = "success"
    else:
        bucket["failures"] = int(bucket.get("failures", 0)) + 1
        bucket["last_result"] = "failure"

    data["failure_classes"][failure_class]["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save_graph(root, data)

    return {
        "failure_class": failure_class,
        "strategy": strategy,
        "success": success,
        "attempts": bucket["attempts"],
        "posterior_score": round(_score(bucket), 4),
    }


def recovery_report(root: Path, failure_class: str | None = None) -> dict:
    data = _load_graph(root)
    classes = data.get("failure_classes", {})

    def summarize(fc: str, payload: dict) -> dict:
        strategies = payload.get("strategies", {})
        rows = []
        for name, bucket in strategies.items():
            attempts = int(bucket.get("attempts", 0))
            successes = int(bucket.get("successes", 0))
            rows.append(
                {
                    "strategy": name,
                    "attempts": attempts,
                    "successes": successes,
                    "failures": int(bucket.get("failures", 0)),
                    "success_rate": round(successes / attempts, 4) if attempts else None,
                    "posterior_score": round(_score(bucket), 4),
                }
            )
        rows.sort(key=lambda x: (x["posterior_score"], x["attempts"]), reverse=True)
        total_attempts = sum(r["attempts"] for r in rows)
        total_successes = sum(r["successes"] for r in rows)
        return {
            "failure_class": fc,
            "total_attempts": total_attempts,
            "total_successes": total_successes,
            "overall_success_rate": round(total_successes / total_attempts, 4) if total_attempts else None,
            "strategies": rows,
        }

    if failure_class:
        payload = classes.get(failure_class, {"strategies": {}})
        return summarize(failure_class, payload)

    result = []
    for fc, payload in classes.items():
        result.append(summarize(fc, payload))
    result.sort(key=lambda x: x["total_attempts"], reverse=True)
    return {"failure_classes": result}


def benchmark_recovery_learning(root: Path, rounds: int = 200, seed: int = 42) -> dict:
    random.seed(seed)
    ensure_root(root)

    # Ground truth probabilities (unknown to planner)
    true_env = {
        "timeout": {
            "retry_backoff": 0.82,
            "restart_worker": 0.58,
            "escalate_human": 0.15,
        },
        "unauthorized": {
            "refresh_credentials": 0.8,
            "retry_backoff": 0.25,
            "escalate_human": 0.2,
        },
    }

    # Baseline: fixed first strategy always
    baseline_success = 0
    adaptive_success = 0

    for _ in range(rounds):
        failure_class = random.choice(list(true_env.keys()))
        strategies = list(true_env[failure_class].keys())

        # Baseline uses a single generic strategy (common real-world anti-pattern)
        baseline_strategy = "retry_backoff" if "retry_backoff" in strategies else strategies[0]
        if random.random() < true_env[failure_class][baseline_strategy]:
            baseline_success += 1

        plan = propose_recovery_plan(root, failure_class, strategies, explore_rate=0.08)
        picked = plan["chosen_strategy"]
        is_success = random.random() < true_env[failure_class][picked]
        if is_success:
            adaptive_success += 1
        record_recovery_outcome(root, failure_class, picked, is_success)

    baseline_rate = baseline_success / rounds if rounds else 0.0
    adaptive_rate = adaptive_success / rounds if rounds else 0.0

    return {
        "rounds": rounds,
        "seed": seed,
        "baseline_success_rate": round(baseline_rate, 4),
        "adaptive_success_rate": round(adaptive_rate, 4),
        "absolute_lift": round(adaptive_rate - baseline_rate, 4),
        "relative_lift_pct": round(((adaptive_rate - baseline_rate) / baseline_rate) * 100, 2)
        if baseline_rate > 0
        else None,
    }
