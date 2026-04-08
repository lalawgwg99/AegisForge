# Unified Architecture (draft)

## Layer 1: Event Fabric
Inputs from:
- tool calls
- command runs
- channel messages
- session lifecycle events
- failure/retry outcomes

Output:
- normalized event stream (JSONL)

## Layer 2: Reliability Harness
Modules:
1) failure-capture
2) lesson-distill
3) lesson-router
4) forgetting-engine
5) integrity-check

Responsibilities:
- convert failures into actionable lessons
- inject relevant lessons at session start
- remove stale/duplicate/low-utility lessons

## Layer 3: Safety & Policy
- secret leakage scanner
- prompt injection detector
- destructive-action approval gate
- policy profiles (strict / balanced / dev)

## Layer 4: Runtime Adapters
- CLI adapter
- messaging adapters (Telegram/WhatsApp/Slack/Discord/...)
- model provider adapters

## Layer 5: Dream Orchestrator（new）
- dream-primary synthesis（摘要、關聯、下一步、焦點）
- aegisforge-secondary signal（health/recovery/repo 狀態）
- actionable scoring（Signal / Actionability / Coherence）
- markdown artifact writer（daily dream log）

## Layer 6: Evaluation & Ops
- recurrence-rate dashboard
- success-rate and recovery-step metrics
- lesson quality lint report
- replay/debug toolkit

## Core data contracts

### error-seed
- id
- timestamp
- context (tool/channel/session)
- error_type
- raw_excerpt

### lesson
- id
- text
- tags
- source_errors
- confidence
- hits
- last_used
- created_at

### policy-decision
- action
- decision (allow/block/ask)
- reason
- rule_id
