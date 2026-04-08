# AegisForge（白話版）

一句話：
AegisForge 幫你的 Agent「少重複犯錯、出事更快恢復、危險操作可追證據」，而且能用 benchmark 證明有沒有進步。

-----------------------------------

## 3 分鐘上手（照抄可跑）

需求：Python 3.9+

```bash
cd AegisForge
PYTHONPATH=src python3 -m aegisforge.cli --help
```

先建立幾筆錯誤事件：

```bash
PYTHONPATH=src python3 -m aegisforge.cli capture --source tool --type timeout --message "request timeout after 30s"
PYTHONPATH=src python3 -m aegisforge.cli capture --source tool --type unauthorized --message "401 unauthorized from api"
```

提煉教訓：

```bash
PYTHONPATH=src python3 -m aegisforge.cli distill --max 3
PYTHONPATH=src python3 -m aegisforge.cli inject --top-k 3
```

-----------------------------------

## p2：Causal Lane Memory + preflight guardrail

1) 從歷史錯誤產生因果 lane：

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge causal-distill --max-lanes 8 --min-support 2
```

2) 任務前注入 guardrail：

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge preflight \
  --action "run sync job" \
  --content "api token timeout settings" \
  --top-k 4
```

你會拿到 `injected_guardrails` 和 `preflight_brief`，可直接放進 agent 任務前置提示。

-----------------------------------

## p3：Verifiable Safety Gate（有證據、可 replay）

1) 執行安全判斷：

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge safety-check \
  --action "delete production table" \
  --content "DROP TABLE users; rm -rf /tmp/old" \
  --profile balanced
```

回傳會包含：
- decision（allow / ask / block）
- reason
- evidence（命中規則）
- decision_id（可回放）

2) 用 decision_id replay 驗證：

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge safety-replay --decision-id <decision_id>
```

`verified: true` 代表可重算且一致。

-----------------------------------

## p4：Benchmark Pack（Before/After 報告）

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge benchmark-pack --rounds 300
```

會產出：
1) Recovery before/after（baseline vs adaptive）
2) Safety scenario 指標（accuracy / unsafe_allow_rate / overblock_rate）
3) Causal preflight before/after
4) 報告檔：`.aegisforge/reports/benchmark-report.md`

-----------------------------------

## 9.0 驗收（預設門檻）

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root /tmp/aegisforge-qc quality-check --rounds 300
```

預設門檻：
- adaptive_success_rate >= 0.75
- relative_lift_pct >= 20%
- weak_lessons == 0

-----------------------------------

## 命令總覽

### 事件 / 教訓
- capture
- distill
- inject
- forget
- health

### 風險策略（舊版）
- policy

### 恢復學習
- recover-plan
- recover-feedback
- recover-report
- benchmark-recovery

### 因果記憶與前置防呆
- causal-distill
- preflight

### 可驗證安全閘門
- safety-check
- safety-replay

### 一鍵驗收與報告
- quality-check
- benchmark-pack

-----------------------------------

## 資料位置（預設 --root=.aegisforge）

- events/error-seeds.jsonl
- lessons/active.jsonl
- lessons/snapshot.json
- recovery/graph.json
- causal/lanes.json
- policy/decisions.jsonl
- benchmarks/...
- reports/benchmark-report.md

-----------------------------------

## 版本

目前：v0.3.0

-----------------------------------

## License

MIT
