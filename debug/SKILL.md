---
name: debug
description: "Use when: parallel adversarial bug-hunt fan-out or pre-commit audit; scouts write files, orchestrator model triages. NOT a code-review scout (/code-review) or plan critique (/critique)."
user-invocable: true
argument-hint: <repo> [scope] [extra prompt]
allowed-tools: [Read, Glob, Grep, Bash, Write]
effort: medium
---

# Debug scout pipeline

Formalizes the genomics bug-hunt pattern: **scouts write, orchestrator model judges, operator steers at ship boundaries.** (The file-bus pipeline that once wrapped this — `/orchestrate`, consolidation, commit-slice — was retired 2026-09-02; the parent session triages `docs/audit/` inline.)

## Roles

| Role | Who |
|------|-----|
| **Operator** | Human — goals, approval, irreversible apply |
| **Orchestrator model** | Frontier parent (Opus, etc.) — dispatch, triage, propose fixes |
| **Scout** | Composer ask-mode — audit files only |

## Flow

```bash
J="just -f ~/Projects/agent-infra/justfile"
$J adversarial-debug-scout ~/Projects/genomics recent --prompt "cardinal rule + RESEARCH_ONLY"
$J debug-until-dry ~/Projects/genomics &     # or: wave loop until no new confirmed bugs
# orchestrator model reads docs/audit/*-debug-handoff.md — validates SUSPECT, fixes confirmed
# findings inline, notes rejections in the memo; operator approves tier-1/2 apply.
```

**arc-agi multi-round audits:** before round 2+ scouts, run `just -C ~/Projects/arc-agi audit-ledger skip-fixed-md` and prepend the markdown block to each scout prompt. Ledger: `loop/audit/ledger.jsonl`. After fixes: `just -C ~/Projects/arc-agi audit-ledger seed-from-git`.

## Rules

1. Scouts run **cursor ask-mode only** (`agent-infra/scripts/debug_scout.py`) — no edits, no commit.
2. Output → `{repo}/docs/audit/YYYY-MM-DD-debug-{run}-{slug}.md`
3. **Orchestrator model** reads the handoffs and triages inline — scouts do not implement fixes.
5. **Operator** approves tier-1/2 apply and taste calls.
6. Check **scientific/conceptual** claims, not just code bugs (see `agent-infra/scripts/debug_scout_prompt.md`).
7. Scouts **verify when cheap**: git log, targeted pytest; skip costly/live/mutating → SUSPECT + hand off.

## vs other skills

| Skill | Role |
|-------|------|
| `/debug` (this) | Adversarial scout fan-out only |
| `/code-review` | Structural line-format scout on source batches |
| `/critique` | Cross-model design/plan review |

Critique before large changes: `/critique model` on the handoff or plan packet.
