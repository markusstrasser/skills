---
name: debug
description: "Use when: parallel adversarial verification (code + scientific/conceptual), bug hunt fan-out, pre-commit audit. Scouts write files; frontier orchestrator model triages. NOT code-review structural scout (/code-review) or plan critique (/critique)."
user-invocable: true
argument-hint: <repo> [scope] [extra prompt]
allowed-tools: [Read, Glob, Grep, Bash, Write]
effort: medium
---

# Debug scout pipeline

Formalizes the genomics bug-hunt pattern: **scouts write, orchestrator model judges, operator steers at ship boundaries.**

## Roles

| Role | Who |
|------|-----|
| **Operator** | Human — goals, approval, irreversible apply |
| **Orchestrator** | Frontier parent model (Opus, etc.) — dispatch, triage, propose fixes |
| **Scout** | Composer ask-mode — audit files only |

## Flow

```bash
just debug ~/Projects/genomics recent --prompt "cardinal rule + RESEARCH_ONLY"
just debug-triage ~/Projects/genomics/docs/audit
# orchestrator model reads docs/audit/*-debug-handoff.md — validates SUSPECT, proposes fixes; operator approves apply:
just commit-plan --include-untracked
just commit-plan --apply 1 --dry-run
just commit-prep --repo ~/Projects/genomics
```

## Rules

1. Scouts run **cursor ask-mode only** (`scripts/debug_scout.py`) — no edits, no commit.
2. Output → `{repo}/docs/audit/YYYY-MM-DD-debug-{run}-{slug}.md`
3. Triage → `{date}-debug-handoff.md` (deduped, severity sorted)
4. **Orchestrator model** (frontier parent with context) reads handoff — scouts do not implement fixes.
5. **Operator** approves tier-1/2 apply and taste calls.
6. Check **scientific/conceptual** claims, not just code bugs (see `scripts/debug_scout_prompt.md`).
7. Scouts **verify when cheap**: git log, targeted pytest; skip costly/live/mutating → SUSPECT + hand off to orchestrator model.

## vs other skills

| Skill | Role |
|-------|------|
| `/debug` (this) | Adversarial verification → audit files → orchestrator model |
| `/code-review` | Structural line-format scout on source batches |
| `/critique` | Cross-model design/plan review (`Projects/skills/critique`) |

Critique before large changes: `/critique model` on the handoff or plan packet.

## Implementation

Scripts live in `agent-infra/scripts/` (shared infra). Vocabulary: `agent-infra/.claude/rules/orchestrator-vocabulary.md`.
