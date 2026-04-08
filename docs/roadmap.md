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

## Backlog
- vector retrieval for lesson routing
- multi-agent arbitration layer
- long-horizon objective planning
