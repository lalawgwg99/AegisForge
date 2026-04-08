# AegisForge

AegisForge 是一個開源的 Agent Reliability OS（代理人可靠性作業層）。

它的目標不是「讓 Agent 看起來更聰明」，而是讓 Agent 在真實工作流中：
- 少重複犯錯
- 少做高風險誤動作
- 在故障時更快恢復
- 並且把改善量化成指標

---

## 為什麼你會有感

AegisForge v0.2 已經加入「自適應恢復圖（Adaptive Recovery Graph）」：
- 系統不再固定用同一招恢復
- 會根據歷史成功率，自動提高高成功策略排序
- 每次恢復結果都會回寫，下一次會更準

簡單說：用得越久，恢復策略越貼近你實際環境。

---

## 目前功能（v0.2）

1) Failure capture
- 把失敗事件寫入 `events/error-seeds.jsonl`

2) Lesson distillation + injection
- 從錯誤萃取可執行 lesson
- 下輪注入 top-k lesson（並回寫 `hits`、`last_used`）

3) 語義去重 + 遺忘
- 語義相似 lesson 不重複新增
- stale decay + LRU eviction，避免記憶膨脹

4) Policy gate
- 對高風險操作輸出 `allow / ask / block`

5) Adaptive Recovery Graph（新）
- `recover-plan`: 針對 failure class 排序候選恢復策略
- `recover-feedback`: 回寫恢復成功/失敗
- `recover-report`: 查看策略成功率與 posterior score
- `benchmark-recovery`: 模擬 adaptive vs baseline 成效

---

## 安裝與啟動

需求：Python 3.9+

```bash
cd AegisForge
python3 -m pip install .
# 或免安裝：直接使用 PYTHONPATH=src
```

CLI 入口：
```bash
aegisforge --help
# 或
PYTHONPATH=src python3 -m aegisforge.cli --help
```

---

## 5 分鐘快速體驗（先跑這段）

```bash
cd AegisForge

# 1) 建立幾筆失敗事件
PYTHONPATH=src python3 -m aegisforge.cli capture --source tool --type timeout --message "request timeout after 30s"
PYTHONPATH=src python3 -m aegisforge.cli capture --source tool --type unauthorized --message "401 unauthorized from api"

# 2) 萃取 lesson
PYTHONPATH=src python3 -m aegisforge.cli distill --max 3

# 3) 注入 lesson（模擬下一輪）
PYTHONPATH=src python3 -m aegisforge.cli inject --top-k 3

# 4) 看健康度
PYTHONPATH=src python3 -m aegisforge.cli health
```

---

## 重點：如何驗證「真的有感提升」

### 方法 A：直接跑內建 benchmark（建議）

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root /tmp/aegisforge-bench benchmark-recovery --rounds 300 --seed 42
```

輸出會包含：
- `baseline_success_rate`
- `adaptive_success_rate`
- `absolute_lift`
- `relative_lift_pct`

結果判讀建議：
- `absolute_lift > 0.08`：可視為有感提升（實務通常已明顯）
- `relative_lift_pct > 15%`：代表 adaptive 已有實用價值
- 若低於上述門檻，先檢查策略候選是否過少或 feedback 品質不足

你要看的不是單次結果，而是：
- adaptive 是否穩定高於 baseline
- 在不同 seed 下是否仍有正提升

建議多跑幾次：
```bash
PYTHONPATH=src python3 -m aegisforge.cli --root /tmp/aegisforge-bench benchmark-recovery --rounds 300 --seed 1
PYTHONPATH=src python3 -m aegisforge.cli --root /tmp/aegisforge-bench benchmark-recovery --rounds 300 --seed 7
PYTHONPATH=src python3 -m aegisforge.cli --root /tmp/aegisforge-bench benchmark-recovery --rounds 300 --seed 99
```

### 方法 B：接真實流程（建議團隊使用）

1. 每次故障前先 `recover-plan`
2. 實際執行後回報 `recover-feedback`
3. 每日看一次 `recover-report`

範例：
```bash
# 先拿策略排序
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge recover-plan \
  --failure-class timeout \
  --strategies retry_backoff restart_worker escalate_human

# 假設你採用 retry_backoff 並成功
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge recover-feedback \
  --failure-class timeout \
  --strategy retry_backoff \
  --success true

# 看學習後報表
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge recover-report
```

---

## 所有 CLI 命令

### 事件與記憶
- `capture --source --type --message`
- `distill --max`
- `inject --top-k`
- `forget --max-lessons --stale-days`
- `health`

### 風險策略
- `policy --action --content --profile(strict|balanced|dev)`

### 恢復學習（v0.2）
- `recover-plan --failure-class --strategies ... [--explore-rate 0.15]`
- `recover-feedback --failure-class --strategy --success true|false`
- `recover-report [--failure-class xxx]`
- `benchmark-recovery --rounds --seed`

---

## 資料目錄

預設寫到 `--root`（預設 `.aegisforge`）：

- `events/error-seeds.jsonl`
- `lessons/active.jsonl`
- `lessons/snapshot.json`
- `recovery/graph.json`  ← 自適應恢復圖核心資料

---

## KPI 建議（團隊導入）

最少追 6 個：
1. recovery_success_rate
2. repeated_failure_rate
3. mean_time_to_recover
4. unsafe_allow_rate
5. overblock_rate
6. lesson_duplication_rate

建議週節奏：
- 每日：recover-report + health
- 每週：benchmark-recovery（固定 rounds/seed 集）
- 每雙週：調整 policy 與候選策略集

---

## 設計原則

- 可執行：不是概念文件，所有核心流程可用 CLI 跑
- 可驗證：每個改善都要能用指標驗證
- 可維護：資料結構簡單、透明、可追溯

---

## 文件

- `docs/problem-map.md`：痛點與策略地圖
- `docs/architecture.md`：架構與資料契約
- `docs/roadmap.md`：分階段 roadmap
- `docs/breakthrough-poc-14d.md`：突破方案 14 天 PoC

---

## 開發與貢獻

```bash
cd AegisForge
python3 -m pip install -e .
```

建議提 PR 前至少跑：
```bash
PYTHONPATH=src python3 -m aegisforge.cli --root /tmp/aegisforge-check benchmark-recovery --rounds 200 --seed 42
PYTHONPATH=src python3 -m aegisforge.cli --root /tmp/aegisforge-check health
```

更多規範請看 `CONTRIBUTING.md`。

---

## License

MIT
