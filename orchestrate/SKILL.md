---
name: orchestrate
description: "Use when: /orchestrate, file-bus multi-agent pipeline, baseline-since-last-green → audit → verify → commit-slice, operator briefing. Orchestrator model dispatches scouts; operator approves apply. NOT single-skill /debug (scout-only) or /observe (session retro)."
user-invocable: true
argument-hint: <repo> [mode: audit|fix|ship|status]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: medium
---

# Orchestrate (file-bus pipeline)

**Operator** = human. **Orchestrator model** = you (frontier parent). **Scout** = ask-mode subagent; audit files only.

Full recipe + flag registry: `~/Projects/agent-infra/.claude/rules/orchestrator-tool-names.md`.  
Invoke from any repo:

```bash
J="just -f ~/Projects/agent-infra/justfile"
```

## Modes (parse `$ARGUMENTS`)

| Mode | Do |
|------|-----|
| `status` (default) | `$J operator-status-briefing <repo>` |
| `audit` | baseline → optional `/debug` → consolidation |
| `fix` | read handoffs + `fix-backlog.md`; implement; `$J verification-gate-runner <repo>` |
| `ship` | `$J commit-slice-planning <repo> --status-only` → operator approves → `--apply N` |

## Audit pipeline

```bash
$J baseline-since-last-green <repo>
# if RED or operator asked: /debug <repo> …  (adversarial-debug-scout)
$J audit-findings-consolidation <repo>/docs/audit --repo <repo>
```

**arc-agi:** before dispatching round 2+ scouts, run `just -C ~/Projects/arc-agi audit-ledger skip-fixed-md` and inject into scout prompts. Triage open rows only: `just -C ~/Projects/arc-agi audit-ledger list --open`. Seed after fix wave: `audit-ledger seed-from-git`.

Read `docs/audit/*-findings-consolidation-handoff.md` and human `fix-backlog.md` before triaging — parser beats empty scout output.

## Rules

1. Check stderr `llm:` on every tool — deterministic tools never call models.
2. Hybrids: step flags only (`--draft-messages-with-agent`, `--synthesis`); honor `ORCHESTRATOR_TOOLS_NO_LLM=1`.
3. Gate `UNKNOWN`/`SKIPPED` = no autonomous apply (same as `RED`).
4. Tier-1/2 apply and taste → **operator** sign-off.
5. Sub-skills: `/debug` (adversarial scout), `/code-review` (structural diff scout), `/critique` (plan packet).
