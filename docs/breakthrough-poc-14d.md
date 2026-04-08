# Breakthrough PoC (14 days)

## Goal
把 AegisForge 從「可運作的 reliability layer」升級到「可學習、可預測、可證明」的 reliability OS。

## Track A — Self-Evolving Recovery Graph
### Day 1-3
- 定義資料結構：`failure_class -> candidate_strategies[] -> success_rate`
- 實作最小 learner store（JSONL/SQLite 皆可）
- 接入目前 `policy` / `forget` 流程的輸出

### Day 4-5
- 加入策略排序（先以 Thompson Sampling 或 UCB 簡化版）
- 支援三類失敗：`trust_gate`, `prompt_delivery`, `stale_branch`

Acceptance:
- 自動恢復成功率可量測
- 相同 failure class 在第 N 次後能收斂到較優策略

## Track B — Causal Lane Memory
### Day 6-8
- 定義 `causal_summary` schema：
  - trigger
  - intermediate_states
  - blocker
  - applied_fix
  - outcome
- 任務結束時落地 summary

### Day 9-10
- 啟動任務前做相似因果案例檢索
- 將 top-1 guardrail 注入執行前檢查

Acceptance:
- 重複故障率下降
- false regression 判斷下降

## Track C — Verifiable Safety Gate
### Day 11-12
- 將高風險命令判斷從 keyword 改為語義風險分級
- 決策輸出包含 evidence（命中規則、風險分數、要求權限）

### Day 13-14
- 導入回放測試集（dangerous / benign 命令對照）
- 產生 before/after 指標報告

Acceptance:
- 高風險誤放行率下降
- 誤攔截率可接受且可調

## KPIs
- recovery_success_rate
- repeated_failure_rate
- false_regression_rate
- unsafe_allow_rate
- overblock_rate
- mean_time_to_recover

## Deliverables
- `src/aegisforge/recovery_graph.py`（或對應模組）
- `src/aegisforge/causal_memory.py`
- `src/aegisforge/policy_explain.py`
- `scripts/benchmark_breakthrough.py`
- `reports/breakthrough-before-after.json`
