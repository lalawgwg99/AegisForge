# AegisForge

**Agent Reliability OS** — 讓你的 AI Agent 少重複犯錯、出事更快恢復、危險操作有證據可追。

提供 **Python SDK**、**MCP Tool Server**、**CLI** 三種接入方式，支援 LLM 智慧教訓萃取與外部日誌匯入。

---

## 安裝

```bash
pip install -e .            # 基本安裝
pip install -e '.[mcp]'     # 含 MCP server 支援
pip install -e '.[all]'     # 全部
```

需求：Python 3.10+

---

## 快速開始

### Python SDK（推薦）

```python
from aegisforge import AegisForge

af = AegisForge(".aegisforge")

# 1. 安全閘門 — 執行前檢查
result = af.safety_check("delete production table", "DROP TABLE users", profile="strict")
if result.blocked:
    raise RuntimeError(f"Blocked: {result.reason}")
if result.needs_approval:
    print(f"需要人工確認: {result.reason}")

# 2. Preflight 防呆 — 注入歷史教訓
guard = af.preflight("run sync job", "api token timeout config")
if guard.has_guardrails:
    print(guard.brief)  # 給 agent 的前置提示

# 3. 捕捉錯誤、學習教訓
af.capture("tool", "timeout", "request timeout after 30s")
af.distill()                    # 提煉教訓
lessons = af.inject(top_k=3)   # 取出最相關的教訓

# 4. 恢復策略學習
plan = af.recover("timeout", ["retry_backoff", "restart_worker", "escalate"])
print(f"建議策略: {plan.chosen_strategy} (mode: {plan.mode})")
af.record_outcome("timeout", plan.chosen_strategy, success=True)

# 5. 匯入外部日誌
af.import_log("agent-run.jsonl", field_map={"message": "msg", "source": "component"})
```

### Agent 整合範例

```python
from aegisforge import AegisForge

af = AegisForge(".aegisforge")

def agent_execute(action: str, content: str):
    # Step 1: Safety gate
    safety = af.safety_check(action, content)
    if safety.blocked:
        return {"error": f"blocked: {safety.reason}", "evidence": safety.evidence}
    
    # Step 2: Preflight guardrails
    guard = af.preflight(action, content)
    context = f"Guardrails:\n{guard.brief}" if guard.has_guardrails else ""
    
    # Step 3: Execute with guardrails in context
    try:
        result = do_action(action, content, extra_context=context)
        return result
    except Exception as e:
        # Step 4: Capture failure and learn
        af.capture("agent", classify_error(e), str(e))
        
        # Step 5: Get recovery strategy
        plan = af.recover(classify_error(e), ["retry", "fallback", "escalate"])
        return execute_recovery(plan.chosen_strategy, action, content)
```

---

## MCP Server（Claude Code / AI IDE 整合）

AegisForge 提供 MCP Tool Server，讓 Claude Code 等 AI 工具直接呼叫安全閘門和記憶功能。

### 設定

在 `~/.claude/settings.json` 加入：

```json
{
  "mcpServers": {
    "aegisforge": {
      "command": "python",
      "args": ["-m", "aegisforge.mcp_server"],
      "env": {
        "AEGISFORGE_ROOT": ".aegisforge"
      }
    }
  }
}
```

或直接在專案的 `.mcp.json`：

```json
{
  "mcpServers": {
    "aegisforge": {
      "command": "python",
      "args": ["-m", "aegisforge.mcp_server"],
      "env": {
        "AEGISFORGE_ROOT": ".aegisforge"
      }
    }
  }
}
```

### 可用 MCP Tools

| Tool | 說明 |
|------|------|
| `aegis_safety_check` | 安全閘門 — 判斷 allow/ask/block |
| `aegis_safety_replay` | 重播驗證歷史安全決策 |
| `aegis_preflight` | 前置防呆 — 注入相關 guardrails |
| `aegis_capture` | 捕捉失敗事件 |
| `aegis_distill` | 提煉教訓 |
| `aegis_inject` | 取出 top-k 教訓 |
| `aegis_recover` | 推薦恢復策略（Thompson Sampling） |
| `aegis_record_outcome` | 回報恢復結果 |
| `aegis_recovery_stats` | 恢復統計 |
| `aegis_causal_distill` | 建立因果 lane |
| `aegis_health` | 記憶品質報告 |
| `aegis_forget` | 遺忘曲線清理 |
| `aegis_import_log` | 匯入外部日誌 |

---

## CLI

```bash
# 設定 PYTHONPATH（未 pip install 時）
export PYTHONPATH=src

# 基本流程
aegisforge capture --source tool --type timeout --message "request timeout after 30s"
aegisforge distill --max 3
aegisforge inject --top-k 3

# 安全閘門
aegisforge safety-check --action "delete table" --content "DROP TABLE users" --profile balanced
aegisforge safety-replay --decision-id <id>

# Preflight 防呆
aegisforge causal-distill --max-lanes 8 --min-support 2
aegisforge preflight --action "run sync" --content "api token timeout" --top-k 4

# 恢復策略
aegisforge recover-plan --failure-class timeout --strategies retry_backoff restart_worker escalate
aegisforge recover-feedback --failure-class timeout --strategy retry_backoff --success true
aegisforge recover-report --failure-class timeout

# LLM 教訓萃取
aegisforge distill-llm --max 3 --api-url http://localhost:11434/v1 --model gemma4:e4b

# 匯入外部日誌
aegisforge import-log --path agent-run.jsonl
aegisforge import-log --path agent.log --format text
aegisforge import-log --path custom.jsonl --field-map '{"message":"msg","error_type":"level"}'

# 驗收與報告
aegisforge quality-check --rounds 300
aegisforge benchmark-pack --rounds 300
aegisforge benchmark-recovery --rounds 200

# Dream Mode
aegisforge dream-report --repo-path .
aegisforge dream-actions --status pending
aegisforge dream-complete --id <action_id>

# 維護
aegisforge health
aegisforge forget --max-lessons 50 --stale-days 30
```

---

## LLM 教訓萃取

預設使用模板萃取教訓（5 種固定句型）。啟用 LLM 萃取可從錯誤訊息中提煉更精確、更有上下文的教訓。

### SDK

```python
from aegisforge import AegisForge, LLMConfig

af = AegisForge(".aegisforge", llm=LLMConfig(
    api_url="http://localhost:11434/v1",  # Ollama
    model="gemma4:e4b",
    enabled=True,
))

# distill 會自動使用 LLM，失敗時 fallback 到模板
af.capture("api", "timeout", "upstream gateway timeout after 45s on /api/v2/sync")
lessons = af.distill()
```

### 環境變數

```bash
export AEGISFORGE_LLM_URL=http://localhost:11434/v1
export AEGISFORGE_LLM_MODEL=gemma4:e4b
export AEGISFORGE_LLM_KEY=sk-xxx  # 可選，Ollama 不需要
```

支援所有 OpenAI-compatible API：OpenAI、Ollama、vLLM、LiteLLM、Groq 等。

---

## Agent 日誌匯入

將真實 agent 執行日誌匯入 AegisForge，用歷史錯誤訓練防呆與恢復策略。

### 支援格式

**JSONL**（自動偵測 error 行）：
```jsonl
{"level":"error","message":"request timeout after 30s","source":"api","timestamp":"2024-01-01T00:00:00Z"}
{"level":"info","message":"all good","source":"api"}
{"level":"error","message":"401 unauthorized","source":"auth"}
```

**純文字**（自動提取含錯誤關鍵字的行）：
```
2024-01-01 INFO: starting sync
2024-01-01 ERROR: connection timeout to database
2024-01-01 INFO: retry succeeded
```

### 欄位映射

如果你的日誌欄位名稱不同，可以自訂映射：

```python
af.import_log("custom.jsonl", field_map={
    "message": "msg",           # 你的日誌用 "msg" 而非 "message"
    "error_type": "severity",   # 用 "severity" 而非 "error_type"
    "source": "component",      # 用 "component" 而非 "source"
})
```

自動偵測的 error 關鍵字：`error`, `fail`, `exception`, `timeout`, `unauthorized`, `denied`, `crash`, `panic`, `fatal`, `rate limit`, `not found` 等。

自動分類的 error_type：`timeout`, `unauthorized`, `rate_limit`, `not_found`, `connection_error`, `validation_error`。

---

## SDK API 參考

### `AegisForge(root, llm=None)`

| 方法 | 回傳 | 說明 |
|------|------|------|
| `safety_check(action, content, profile)` | `SafetyResult` | 安全閘門評估 |
| `preflight(action, content, top_k)` | `PreflightResult` | 前置防呆 |
| `capture(source, error_type, message)` | `dict` | 捕捉失敗事件 |
| `distill(max_lessons)` | `list[dict]` | 提煉教訓（LLM 或模板） |
| `inject(top_k)` | `list[dict]` | 取出教訓 |
| `recover(failure_class, strategies, explore_rate)` | `RecoveryPlan` | 推薦恢復策略 |
| `record_outcome(failure_class, strategy, success)` | `dict` | 回報結果 |
| `recovery_stats(failure_class)` | `dict` | 恢復統計 |
| `causal_distill(max_lanes, min_support)` | `dict` | 建立因果 lane |
| `health()` | `dict` | 記憶品質報告 |
| `forget(max_lessons, stale_days)` | `dict` | 遺忘曲線 |
| `benchmark(rounds, seed)` | `dict` | 恢復學習基準測試 |
| `import_log(path, format, field_map)` | `dict` | 匯入外部日誌 |

### `SafetyResult`

| 屬性 | 說明 |
|------|------|
| `decision` | `"allow"` / `"ask"` / `"block"` |
| `reason` | 判定原因 |
| `risk_score` | 風險分數 |
| `evidence` | 命中規則列表 |
| `decision_id` | 可用於 replay 的 ID |
| `blocked` | `bool` — 是否被阻擋 |
| `needs_approval` | `bool` — 是否需要人工確認 |
| `allowed` | `bool` — 是否允許 |
| `to_dict()` | 轉為 dict |

### `PreflightResult`

| 屬性 | 說明 |
|------|------|
| `guardrails` | guardrail 列表 |
| `brief` | 可直接注入 prompt 的文字 |
| `has_guardrails` | `bool` — 是否有 guardrails |
| `count` | guardrail 數量 |

### `RecoveryPlan`

| 屬性 | 說明 |
|------|------|
| `chosen_strategy` | 推薦策略 |
| `mode` | `"exploit"` / `"explore"` |
| `ranked` | 按分數排序的策略列表 |

---

## 安全閘門偵測項目

| 類型 | 偵測內容 | 決策 |
|------|---------|------|
| Secret | `sk-*`, `password=`, `api_key=`, `token=` | block |
| Prompt Injection | `ignore previous`, `system:`, `you are now`（含 Unicode 全形繞過） | block |
| 危險指令 | `rm -rf`, `curl \| bash`, `mkfs`, `dd if=` | strict:block / balanced:ask |
| 破壞操作 | delete, remove, drop, truncate, format, exec | strict:block / balanced:ask |

Profile 行為：
- **strict**：危險操作直接 block
- **balanced**（預設）：危險操作需人工確認（ask）
- **dev**：危險操作放行，但 secret/injection 仍 block

---

## 資料位置

預設 `--root=.aegisforge`：

```
.aegisforge/
├── events/error-seeds.jsonl      # 錯誤事件
├── lessons/active.jsonl          # 教訓
├── lessons/snapshot.json         # 教訓快照
├── recovery/graph.json           # 恢復策略圖
├── causal/lanes.json             # 因果 lane
├── policy/decisions.jsonl        # 安全決策日誌
├── benchmarks/                   # 基準測試資料
└── reports/
    ├── benchmark-report.md       # 基準報告
    └── dreams/                   # Dream mode 報告
        ├── YYYY-MM-DD-dream.md
        └── action-ledger.jsonl
```

---

## 架構

```
aegisforge/
├── sdk.py             # Python SDK（主要進入點）
├── mcp_server.py      # MCP Tool Server
├── cli.py             # CLI
├── core.py            # 核心：capture, distill, inject, forget, health
├── safety_gate.py     # 安全閘門：evaluate, check, replay
├── causal_lane.py     # 因果記憶與 preflight
├── recovery_graph.py  # Thompson Sampling 恢復策略
├── llm_extract.py     # LLM 教訓萃取
├── log_import.py      # 外部日誌匯入
├── dream_mode.py      # Dream mode 報告
├── quality.py         # 驗收與品質檢查
├── benchmark_pack.py  # 綜合基準測試
└── storage.py         # JSONL 讀寫（含 file lock）
```

---

## 測試

```bash
pip install pytest
PYTHONPATH=src python3 -m pytest tests/ -v
```

---

## 版本

v0.4.0

## License

MIT
