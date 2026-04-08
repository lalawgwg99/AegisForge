# Roadmap

## Phase 0 (Week 1): Foundation
- define event schema
- implement local JSONL event writer
- create baseline metrics script

Exit criteria:
- reproducible event logs
- baseline report generated from sample runs

## Phase 1 (Week 2-3): Learning loop MVP
- failure capture from tool/session events
- distill 1-3 lessons per session
- inject top-K lessons at next start

Exit criteria:
- recurrence-rate drops on controlled task set

## Phase 2 (Week 4): Forgetting + quality
- dedup logic
- stale decay
- lesson lint checks

Exit criteria:
- memory stays bounded without quality collapse

## Phase 3 (Week 5): Safety gates
- secret/injection scanner
- risky action approval workflow

Exit criteria:
- policy decisions logged and auditable

## Phase 4 (Week 6): OSS release kit
- example configs
- benchmark task pack
- docs + contribution guide
- first public GitHub release

## Phase 5 (Week 7-8): Breakthrough track
- self-evolving recovery graph（策略會依歷史成功率動態調整）
- causal lane memory（把事件收斂為因果摘要，任務前可檢索注入 guardrail）
- verifiable safety gate（策略決策附 evidence，可審計可回放）

Exit criteria:
- recovery success rate 可量測且優於 v0.2 baseline
- repeated failure rate 明顯下降
- 高風險誤放行率下降，且 decision 可解釋

## Backlog
- vector retrieval for lesson routing
- reliability credit score（策略/工具/流程信用分，驅動 merge 與 escalation）
- adversarial verification lane（合併前自動生成反例與破壞測試）
- multi-agent arbitration layer
- long-horizon objective planning
