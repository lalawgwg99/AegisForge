# AegisForge

AegisForge 是一個開源的 Agent Reliability OS（代理人可靠性作業層）。

它整合 Claude Code、GPT Codex、OpenClaw、Hermes Agent 各自強項，解決 AI 代理人在實務落地最常見的 5 個痛點：
- 重複犯錯
- 記憶膨脹且品質下降
- 高風險操作缺乏硬性閘門
- 多通道行為不一致
- 改進無法量化

重點：
AegisForge 不是只做文件，現在已包含可跑的 MVP CLI 代碼（capture/distill/inject/health）。

## 3 分鐘快速開始

需求：Python 3.9+

1) 進入專案
```bash
cd AegisForge
```

2) 直接執行（免安裝，最穩）
```bash
PYTHONPATH=src python3 -m aegisforge.cli capture --source tool --type timeout --message "request timeout after 30s"
PYTHONPATH=src python3 -m aegisforge.cli capture --source tool --type unauthorized --message "401 unauthorized from api"
```

3) 萃取 lesson
```bash
PYTHONPATH=src python3 -m aegisforge.cli distill --max 3
```

4) 下一輪注入 lesson
```bash
PYTHONPATH=src python3 -m aegisforge.cli inject --top-k 3
```

5) 執行遺忘策略（stale + LRU）
```bash
PYTHONPATH=src python3 -m aegisforge.cli forget --max-lessons 50 --stale-days 30
```

6) 風險動作 policy 判斷
```bash
PYTHONPATH=src python3 -m aegisforge.cli policy --action exec --content "rm -rf /tmp/demo" --profile balanced
```

7) 健康檢查
```bash
PYTHONPATH=src python3 -m aegisforge.cli health
```

可選安裝（新版 pip 可用）：
```bash
python3 -m pip install .
# 之後可直接用 aegisforge ...
```

資料會寫在：
- `.aegisforge/events/error-seeds.jsonl`
- `.aegisforge/lessons/active.jsonl`

## 目前已實作（MVP）

- failure capture：把錯誤事件寫入 JSONL
- lesson distillation：依錯誤類型萃取可執行教訓
- lesson injection：選 top-k lessons 注入下一輪（會回寫 hits/last_used）
- active forgetting：stale decay + LRU eviction
- policy gate：針對高風險動作輸出 allow/block/ask
- health report：檢查 lessons 數量、精確重複、語義重複、弱規則

## 為什麼這個方向比單一產品更有價值

- 吸收 Claude Code / Codex 的工程迭代速度
- 吸收 OpenClaw 的多通道運營能力
- 吸收 Hermes 的 tool/skill/memory 可組合性
- 再加上一層 code-enforced reliability（可驗證、可指標化）

## 架構文件

- `docs/problem-map.md`：四大生態痛點與融合策略
- `docs/architecture.md`：統一架構與資料契約
- `docs/roadmap.md`：分階段路線與驗收標準

## 接下來要做（v0.2）

- semantic dedup（語義去重）
- stale decay + LRU eviction
- policy gate（allow/block/ask）
- benchmark 任務集與 before/after 報告
- OpenClaw/Hermes adapter

## 貢獻

請看 `CONTRIBUTING.md`。

## License

MIT
