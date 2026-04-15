# AegisForge

![CI](https://github.com/lalawgwg99/AegisForge/actions/workflows/ci.yml/badge.svg)

**Agent Reliability OS**
讓 AI Agent 少重複犯錯、出事更快恢復、危險操作有證據可追。

AegisForge 提供三種接入方式：
- Python SDK（最推薦，整合成本最低）
- MCP Tool Server（給 Claude Code / AI IDE 直接呼叫）
- CLI（腳本化與驗收流程）

---

## 你會得到什麼

AegisForge 主要解決 4 件事：
1. **Safety Gate**：先判斷高風險操作（allow / ask / block）。
2. **Learning Loop**：從失敗事件提煉教訓，避免重犯。
3. **Recovery Graph**：根據歷史成功率推薦恢復策略。
4. **Causal Preflight**：任務前注入 guardrails，降低同型故障。

---

## 3 分鐘快速開始（SDK）

### 1) 安裝

```bash
pip install -e .
# 或：pip install -e '.[mcp]'   # 需要 MCP server
# 或：pip install -e '.[all]'   # 全部功能
```

需求：Python 3.10+

### 2) 最小可跑範例

```python
from aegisforge import AegisForge

af = AegisForge(".aegisforge")

# 1. 安全檢查
safety = af.safety_check("delete production table", "DROP TABLE users", profile="balanced")
if safety.blocked:
    raise RuntimeError(f"Blocked: {safety.reason}")
if safety.needs_approval:
    print(f"需要人工確認: {safety.reason}")

# 2. 捕捉失敗 -> 提煉教訓 -> 注入
af.capture("tool", "timeout", "request timeout after 30s")
af.distill(max_lessons=3)
print(af.inject(top_k=3))

# 3. 恢復策略學習
plan = af.recover("timeout", ["retry_backoff", "restart_worker", "escalate_human"])
print(plan.chosen_strategy, plan.mode)
af.record_outcome("timeout", plan.chosen_strategy, success=True)

# 4. 建立因果 lane + 任務前防呆
af.causal_distill(max_lanes=8, min_support=2)
preflight = af.preflight("run sync job", "api token timeout config", top_k=4)
print(preflight.brief)
```

---

## 接入方式選擇

| 場景 | 建議 |
|---|---|
| 你在寫 Python Agent / 後端服務 | SDK |
| 你要讓 Claude Code / IDE 直接呼叫功能 | MCP Server |
| 你要做 shell 腳本、CI 驗收、批次流程 | CLI |

---

## CLI 常用流程

```bash
# 若尚未 pip install -e .，先設定：
export PYTHONPATH=src

# 失敗學習循環
aegisforge capture --source tool --type timeout --message "request timeout after 30s"
aegisforge distill --max 3
aegisforge inject --top-k 3

# 安全閘門
aegisforge safety-check --action "delete table" --content "DROP TABLE users" --profile balanced
aegisforge safety-replay --decision-id <id>

# 恢復策略
aegisforge recover-plan --failure-class timeout --strategies retry_backoff restart_worker escalate_human
aegisforge recover-feedback --failure-class timeout --strategy retry_backoff --success true
aegisforge recover-report --failure-class timeout

# 因果記憶 + preflight
aegisforge causal-distill --max-lanes 8 --min-support 2
aegisforge preflight --action "run sync" --content "api token timeout" --top-k 4

# 外部日誌匯入
aegisforge import-log --path agent-run.jsonl
aegisforge import-log --path agent.log --format text
aegisforge import-log --path custom.jsonl --field-map '{"message":"msg","error_type":"level"}'

# 驗收
aegisforge quality-check --rounds 300
aegisforge benchmark-pack --rounds 300
```

---

## MCP Server（Claude Code / AI IDE）

在 `~/.claude/settings.json` 或專案 `.mcp.json` 加入：

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

可用工具：
- `aegis_safety_check`
- `aegis_safety_replay`
- `aegis_preflight`
- `aegis_capture`
- `aegis_distill`
- `aegis_inject`
- `aegis_recover`
- `aegis_record_outcome`
- `aegis_recovery_stats`
- `aegis_causal_distill`
- `aegis_health`
- `aegis_forget`
- `aegis_import_log`

---

## Hermes / OpenClaw 接入檢查清單

上線前請逐項確認：

1. 使用獨立資料根目錄（不要共用同一個 `.aegisforge`）。
2. 預設 profile 用 `balanced`（不要一開始就 `dev`）。
3. 先完成一輪 smoke test：`safety-check`、`capture -> distill -> inject`、`recover + record_outcome`。
4. 外部日誌匯入前先對齊欄位映射（`message` / `error_type` / `source`）。
5. 在執行層保留權限邊界（容器或最小系統權限），不要只依賴安全閘門。
6. Dev / Staging / Prod 分離 root 路徑，避免訓練資料互相污染。

### 最小設定範本：Hermes

```json
{
  "mcpServers": {
    "aegisforge": {
      "command": "python",
      "args": ["-m", "aegisforge.mcp_server"],
      "env": {
        "AEGISFORGE_ROOT": ".aegisforge-hermes",
        "AEGISFORGE_PROFILE": "balanced"
      }
    }
  }
}
```

### 最小設定範本：OpenClaw

```json
{
  "mcpServers": {
    "aegisforge": {
      "command": "python",
      "args": ["-m", "aegisforge.mcp_server"],
      "env": {
        "AEGISFORGE_ROOT": ".aegisforge-openclaw",
        "AEGISFORGE_PROFILE": "balanced"
      }
    }
  }
}
```

備註：`AEGISFORGE_PROFILE` 主要是接入層統一管理參數用；實際決策仍以呼叫 `safety_check(..., profile=...)` 的參數為準。

---

## LLM 教訓萃取（可選）

預設用模板萃取；啟用後可用 LLM 抽出更精準教訓，失敗會自動 fallback 模板。

```python
from aegisforge import AegisForge, LLMConfig

af = AegisForge(
    ".aegisforge",
    llm=LLMConfig(
        api_url="http://localhost:11434/v1",  # OpenAI-compatible endpoint
        model="gemma4:e4b",
        enabled=True,
    ),
)
```

環境變數：

```bash
export AEGISFORGE_LLM_URL=http://localhost:11434/v1
export AEGISFORGE_LLM_MODEL=gemma4:e4b
export AEGISFORGE_LLM_KEY=sk-xxx  # Ollama 可省略
```

---

## 外部日誌匯入

支援 JSONL 與純文字；會自動偵測錯誤行並分類常見錯誤類型。

```python
af.import_log("custom.jsonl", field_map={
    "message": "msg",
    "error_type": "severity",
    "source": "component",
})
```

---

## 安全閘門規則摘要

- Secret（`sk-*`, `password=`, `token=`） -> `block`
- Prompt injection（`ignore previous`, `system:`, `you are now`） -> `block`
- 危險指令（`rm -rf`, `curl | bash`, `mkfs`, `dd if=`）
  - `strict`: `block`
  - `balanced`: `ask`
  - `dev`: `allow`（但 secret/injection 仍 block）

---

## 驗收與測試

### 本地測試

```bash
# 方式一（推薦）
pip install -e .
pytest -q

# 方式二（不安裝套件）
PYTHONPATH=src pytest -q
```

### 品質檢查

```bash
PYTHONPATH=src python -m aegisforge.cli quality-check --rounds 300
```

---

## 常見問題（Troubleshooting）

### `ModuleNotFoundError: No module named 'aegisforge'`

你在 repo 根目錄直接跑測試時，通常要二選一：
1. `pip install -e .`
2. `PYTHONPATH=src pytest -q`

### MCP 啟動失敗：`No module named mcp`

請安裝：

```bash
pip install -e '.[mcp]'
```

---

## 專案結構

```text
src/aegisforge/
├── sdk.py
├── cli.py
├── mcp_server.py
├── core.py
├── safety_gate.py
├── recovery_graph.py
├── causal_lane.py
├── llm_extract.py
├── log_import.py
├── quality.py
├── benchmark_pack.py
├── dream_mode.py
└── storage.py
```

資料預設落在 `.aegisforge/`：
- `events/error-seeds.jsonl`
- `lessons/active.jsonl`
- `recovery/graph.json`
- `causal/lanes.json`
- `policy/decisions.jsonl`
- `reports/benchmark-report.md`

---

## 文件與路線圖

- Architecture: `docs/architecture.md`
- Roadmap: `docs/roadmap.md`
- Breakthrough PoC: `docs/breakthrough-poc-14d.md`
- Problem map: `docs/problem-map.md`

## 範例

- SDK loop: `examples/sdk_agent_loop.py`
- Import + distill: `examples/import_then_distill.py`
- MCP config: `examples/mcp_setup_example.json`
- Hermes MCP config: `examples/hermes_mcp_config.json`
- OpenClaw MCP config: `examples/openclaw_mcp_config.json`

## Changelog

- `CHANGELOG.md`

---

## 版本與授權

- Version: `v0.4.0`
- License: MIT
