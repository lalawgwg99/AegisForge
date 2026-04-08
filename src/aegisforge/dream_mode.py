from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .core import health_report, inject_lessons
from .recovery_graph import recovery_report
from .storage import read_jsonl


@dataclass
class RepoSignal:
    exists: bool
    branch: str = ""
    dirty: bool = False
    recent_commits: list[str] | None = None


def _run_git(repo_path: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return (proc.stdout or "").strip()


def collect_repo_signal(repo_path: Path, commit_limit: int = 3) -> RepoSignal:
    if not repo_path.exists():
        return RepoSignal(exists=False, recent_commits=[])

    branch = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    status = _run_git(repo_path, ["status", "--porcelain"])
    log_lines = _run_git(
        repo_path,
        ["log", f"-n{max(1, commit_limit)}", "--pretty=format:%h %s"],
    ).splitlines()

    return RepoSignal(
        exists=True,
        branch=branch,
        dirty=bool(status.strip()),
        recent_commits=[line.strip() for line in log_lines if line.strip()],
    )


def _normalize_lesson(line: dict) -> str:
    text = (line.get("text") or "").strip()
    if not text:
        return "補齊可驗收步驟，避免重複失敗。"
    return text


def _make_next_steps(lessons: list[dict], repo: RepoSignal, top_k: int) -> list[str]:
    steps: list[str] = []

    if repo.exists and repo.dirty:
        steps.append("整理 AegisForge 當前未提交變更並加上驗收訊息（驗收：git status 乾淨或只剩可解釋變更）。")

    for lesson in lessons[: max(1, top_k)]:
        text = _normalize_lesson(lesson)
        steps.append(f"落地教訓：{text}（驗收：本日任務前完成一次 preflight 或 safety-check）。")

    if repo.exists and repo.recent_commits:
        steps.append("從最近 commit 挑 1 條可在 30 分鐘內完成的延伸優化（驗收：產生一筆可提交變更）。")

    # 去重 + 限制 3 條
    dedup: list[str] = []
    seen = set()
    for s in steps:
        if s in seen:
            continue
        dedup.append(s)
        seen.add(s)
        if len(dedup) >= 3:
            break
    return dedup or ["建立 1 條可驗收的最小下一步（驗收：完成後可明確標記 done）。"]


def _score(signal_count: int, next_steps: list[str], weak_lessons: int, dirty: bool) -> dict:
    signal = min(100, 65 + signal_count * 7)
    actionability = min(100, 60 + len(next_steps) * 12 - max(0, weak_lessons) * 5)
    coherence = 88 if dirty else 92
    total = round((signal + actionability + coherence) / 3)
    return {
        "signal": int(signal),
        "actionability": int(actionability),
        "coherence": int(coherence),
        "total": int(total),
    }


def generate_dream_report(
    root: Path,
    repo_path: Path,
    output_dir: Path | None = None,
    top_k: int = 3,
) -> dict:
    now = datetime.now()
    output_root = output_dir or (root / "reports" / "dreams")
    output_root.mkdir(parents=True, exist_ok=True)

    events = read_jsonl(root / "events" / "error-seeds.jsonl")
    lessons = read_jsonl(root / "lessons" / "active.jsonl")
    injected = inject_lessons(root, top_k=max(1, top_k)) if lessons else []
    health = health_report(root)
    recovery = recovery_report(root)

    repo = collect_repo_signal(repo_path)
    next_steps = _make_next_steps(injected or lessons, repo, top_k=top_k)

    signal_count = len(events[-10:]) + len(lessons) + (1 if repo.exists else 0)
    scores = _score(signal_count, next_steps, int(health.get("weak_lessons", 0)), repo.dirty)

    focus = (
        "先把 dream 下一步轉成可驗收任務，再執行 AegisForge preflight。"
        if next_steps
        else "先補齊一條可驗收的最小任務。"
    )

    commit_lines = repo.recent_commits or []
    relation_lines = [
        "夢境輸出可直接承接 lessons，避免『知道但沒做』。",
        "AegisForge 的 health/recovery 指標可當作夢境評分的客觀訊號。",
        "若倉庫有未提交變更，先收斂再擴張，能降低隔日決策噪音。",
    ]

    if repo.exists and commit_lines:
        relation_lines.append("最近 commit 主題可作為今日可推進點的候選來源。")

    report_path = output_root / f"{now:%Y-%m-%d}-dream.md"

    md: list[str] = []
    md.append(f"# Dream Log — {now:%Y-%m-%d}")
    md.append("")
    md.append("## 夢境摘要")
    md.append(f"今日共觀測到 {len(events)} 筆事件、{len(lessons)} 條教訓。")
    md.append(f"AegisForge health：weak_lessons={health.get('weak_lessons', 0)}，duplicates={health.get('duplicates_exact', 0)}。")
    if repo.exists:
        md.append(f"Repo 狀態：branch={repo.branch or 'unknown'}，dirty={'yes' if repo.dirty else 'no'}。")
    else:
        md.append("Repo 狀態：未找到指定倉庫，僅輸出夢境主流程。")
    md.append("")

    md.append("## 潛在關聯")
    for idx, line in enumerate(relation_lines[:4], start=1):
        md.append(f"{idx}. {line}")
    md.append("")

    md.append("## 可執行下一步")
    for idx, line in enumerate(next_steps, start=1):
        md.append(f"{idx}. {line}")
    md.append("")

    md.append("## 風險與阻塞")
    if repo.exists and repo.dirty:
        md.append("- 倉庫有未提交變更，若直接擴增任務容易混入噪音。建議先整理差異後再推進。")
    else:
        md.append("- 無明顯程式碼阻塞；主要風險是教訓未被實際執行。")
    if int(health.get("weak_lessons", 0)) > 0:
        md.append("- 存在弱教訓（無動詞行動），建議補成可驗收句型。")
    md.append("")

    md.append("## 今日唯一焦點")
    md.append(f"{focus}")
    md.append("")

    md.append("## 品質評分")
    md.append(f"- Signal: {scores['signal']}")
    md.append(f"- Actionability: {scores['actionability']}")
    md.append(f"- Coherence: {scores['coherence']}")
    md.append(f"- Total: {scores['total']}/100")
    md.append("")

    md.append("## AegisForge 輔助訊號")
    md.append(f"- recovery classes: {len(recovery.get('failure_classes', [])) if isinstance(recovery, dict) else 0}")
    if commit_lines:
        md.append("- recent commits:")
        for c in commit_lines[:3]:
            md.append(f"  - {c}")

    report_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    return {
        "report_path": str(report_path),
        "scores": scores,
        "focus": focus,
        "next_steps": next_steps,
        "repo_signal": {
            "exists": repo.exists,
            "branch": repo.branch,
            "dirty": repo.dirty,
            "recent_commits": commit_lines[:3],
        },
    }
