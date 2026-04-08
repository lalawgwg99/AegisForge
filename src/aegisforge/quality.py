from __future__ import annotations

from pathlib import Path

from .core import health_report
from .recovery_graph import benchmark_recovery_learning


def quality_check(
    root: Path,
    rounds: int = 300,
    seeds: tuple[int, ...] = (1, 7, 42),
    min_recovery_success_rate: float = 0.75,
    min_relative_lift_pct: float = 20.0,
    min_score: float = 9.0,
) -> dict:
    bench_rows = []
    for seed in seeds:
        bench_root = root / "benchmarks" / f"seed-{seed}"
        row = benchmark_recovery_learning(bench_root, rounds=rounds, seed=seed)
        bench_rows.append(row)

    avg_adaptive = sum(r["adaptive_success_rate"] for r in bench_rows) / len(bench_rows)
    avg_lift_pct = sum(r["relative_lift_pct"] for r in bench_rows) / len(bench_rows)

    health = health_report(root)

    checks = [
        {
            "name": "adaptive_success_rate",
            "value": round(avg_adaptive, 4),
            "threshold": f">= {min_recovery_success_rate}",
            "pass": avg_adaptive >= min_recovery_success_rate,
        },
        {
            "name": "relative_lift_pct",
            "value": round(avg_lift_pct, 2),
            "threshold": f">= {min_relative_lift_pct}",
            "pass": avg_lift_pct >= min_relative_lift_pct,
        },
        {
            "name": "weak_lessons",
            "value": health.get("weak_lessons", 0),
            "threshold": "== 0",
            "pass": health.get("weak_lessons", 0) == 0,
        },
    ]

    score = 10.0
    for c in checks:
        if not c["pass"]:
            if c["name"] == "adaptive_success_rate":
                score -= 1.0
            elif c["name"] == "relative_lift_pct":
                score -= 1.0
            else:
                score -= 0.2

    score = round(max(0.0, score), 2)
    all_checks_pass = all(c["pass"] for c in checks)

    return {
        "score": score,
        "target": min_score,
        "pass_90": score >= min_score and all_checks_pass,
        "rounds": rounds,
        "seeds": list(seeds),
        "benchmark_runs": bench_rows,
        "checks": checks,
        "health": health,
        "summary": (
            "達標：已達 9.0+ 且核心檢查全通過"
            if (score >= min_score and all_checks_pass)
            else "未達標：請先提升 recovery 成功率或策略增益"
        ),
    }
