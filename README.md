# Agent Fusion OS

Open-source blueprint + reference implementation that combines the strongest ideas from:
- Claude Code
- GPT Codex
- OpenClaw
- Hermes Agent

Goal: build a practical agent runtime that is:
1) hard to break,
2) learns from mistakes,
3) observable in production,
4) usable across CLI + messaging channels.

## Why this project exists
Each system is strong in a different area:
- Claude Code: robust coding loop and quality of execution UX
- GPT Codex: coding task decomposition and code-generation flow
- OpenClaw: multi-channel gateway + personal assistant operations
- Hermes Agent: tool-first orchestration, skills, memory, automation

But teams still face common pain points:
- repeated failures across sessions
- no standardized learning/forgetting loop
- weak cross-channel continuity
- hard-to-verify memory quality
- limited safety guardrails for autonomous actions

Agent Fusion OS proposes one integrated architecture to solve these together.

## Core principles
- Code-enforced reliability: critical behavior in runtime hooks, not prompt wishful thinking.
- Learn + forget: capture failures, distill lessons, decay stale rules.
- Observable by default: every loop has metrics and replayable traces.
- Pluggable architecture: works with different models/providers/channels.
- Human override: approvals and policy gates for destructive actions.

## MVP scope (v0.1)
- Failure capture pipeline (tool/session/channel events)
- Lesson distillation + next-session injection
- Active forgetting (staleness + LRU + dedup)
- Policy guardrail (secrets/injection/unsafe command gates)
- Evaluation harness (before/after error recurrence metrics)

## Repository structure
- docs/problem-map.md — pain points + how each ecosystem handles them
- docs/architecture.md — unified architecture and component contracts
- docs/roadmap.md — phased implementation plan
- src/ (planned) — reference implementation

## Success criteria
- repeated error rate decreases
- first-pass task success increases
- recovery steps/time decrease
- memory hit quality improves while memory size remains bounded

## Status
Draft architecture + implementation roadmap.

## License
MIT
