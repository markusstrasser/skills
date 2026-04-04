---
name: dispatch-research
description: Autonomous research-to-execution pipeline. Dispatches parallel audits to Codex (GPT-5.4), verifies findings, builds execution plan, implements fixes. Triggers on "dispatch research", "codex sweep", "run audits", "audit and fix".
effort: medium
---

# Dispatch Research — Autonomous Audit-to-Execution Pipeline

Research → Dispatch → Verify → Plan → Execute. Opus orchestrates the full loop: dispatches parallel audits to GPT-5.4 via Codex CLI, verifies findings against actual code, synthesizes an execution plan, then implements it.

## When to use

"dispatch research", "run audits", "codex sweep", "audit and fix", or when the user wants autonomous project improvement — from discovery through implementation.

**Depth modes:**
- `"quick sweep"` → 3-5 lightweight audits, stop at findings (no execute)
- `"audit"` / default → full 5-phase loop
- `"deep audit"` → 15+ thorough audits, comprehensive plan

**Stop points:** "just audit" (stop after Phase 3), "plan only" (stop after Phase 4), "full auto" (all 5 phases).

## Pipeline

```
Phase 1: RECON     Read project state, identify gaps              (~15%)
Phase 2: DISPATCH  Craft prompts, fire 3-5 parallel Codex audits  (~25%)
Phase 3: VERIFY    Check findings against actual code              (~20%)
Phase 4: PLAN      Synthesize verified findings into exec plan     (~15%)
Phase 5: EXECUTE   Implement the plan (with user approval)         (~25%)
```

## GPT-5.4 via Codex — what to know

**CAN do:** Read files, shell commands, cross-reference, count/compare, structured output. Has 9 MCPs (scite, exa, brave, perplexity, research, meta-knowledge, paper-search, context7, codex_apps).

**CANNOT do:** DB queries, `uv`/project CLIs (sandbox lacks env), conversation history. **28% factual error rate on external knowledge.** Hallucinates fix status ("already fixed" when it wasn't). `--search` only works in interactive mode.

**Auth:** ChatGPT account auth. Only `gpt-5.4` (default) and `gpt-5.3-codex` work. `o3`/`gpt-4.1` rejected.

**Token overhead:** ~37K baseline per `codex exec` call (9 MCP servers, no disable flag). Cost-effective for substantial tasks only.

## Critical gotchas

**Turn limits (~15-20 tool calls):** Max 5 files per agent. Split larger audits. Include synthesis deadline in EVERY prompt: "After reading at most 5 files, STOP and synthesize. 70% reading, 30% writing. Partial report > no report." (6th+ recurrence, 2026-03-28). Codex doesn't see CLAUDE.md — the instruction must be in the prompt.

**Template-first anti-pattern:** Agents that create skeleton markdown first waste a write turn, then exhaust turns filling it in. Failed 3/4 sessions. Use `-o FILE` instead — captures final text message automatically.

**Memory pressure gate:** Before dispatching, count active processes (`pgrep -lf claude | wc -l`, NOT `pgrep -c` on macOS). If >= 4, reduce to sequential or audit directly.

**MCP contention:** Max 4 parallel Codex agents. Each starts 9 MCP servers. 5+ agents = 132+ simultaneous startups = system overwhelm.

**Output preservation:** Tell agents to write to `docs/audit/`, NOT `/tmp`. Immediately `git add` or `cp` after completion — sandbox cleanup can delete files. Do NOT use `--ephemeral` (deletes `-o` output).

**Verification is mandatory (Phase 3).** ~28% error rate concentrated in counts, severity, external knowledge. Code-grounded findings (file:line) are consistently reliable. See `references/verification-procedure.md` for checklist and hallucination patterns.

**S2 API outages:** Tell agents to fall back to `backend="openalex"` or exa if Semantic Scholar returns 403.

## Model selection

| Target | When | Tradeoff |
|--------|------|----------|
| `codex exec --model gpt-5.4` | Cross-referencing, counting, structured output | Free, parallel, output extraction fragile |
| Claude Code `Agent` subagents | Same + DuckDB/MCP access | Costs tokens, output inline (reliable) |
| `llmx chat --model gemini-3.1-pro-preview` | 1M context, huge file ingestion | Best for monolithic analysis |

**Use Codex for:** 5+ parallel audits, cross-file grep+read tracing, wiring/drift/completeness checks.
**Use Claude subagents for:** <3 file audits, tasks needing project-specific tooling (uv, DuckDB, MCP).

## Phase-by-phase execution

**Phase 1 — Recon:** Read CLAUDE.md, `.claude/overviews/`, plans, `git log --oneline -30`, `docs/audit/` (skip completed). Build mental model, identify audit targets.

**Phase 2 — Dispatch:** Craft self-contained prompts per `references/prompt-construction.md`. Execute per `references/codex-dispatch-mechanics.md`. Each prompt: "Read [files], check [properties], cross-reference [A vs B], cite file:line."

**Phase 3 — Verify:** Every finding checked against actual code. Follow `references/verification-procedure.md`. Output: confirmed / rejected (with reason) / corrected findings.

**Phase 4 — Plan:** Synthesize into phased execution plan per `references/plan-and-execute.md`. Fix ALL verified findings — don't self-select "top N." Present to user; wait for approval.

**Phase 5 — Execute:** Implement per `references/plan-and-execute.md`. Read before editing. One commit per logical change. If other agents active, commit after each fix (not batched) or use `isolation: worktree`.

## References (loaded on demand)

| File | Contents |
|------|----------|
| `references/prompt-construction.md` | Target selection categories, prompt structure, good/bad patterns |
| `references/codex-dispatch-mechanics.md` | Bash commands, flags, MCP config, `-o` caveats, fallback |
| `references/verification-procedure.md` | Verification checklist, hallucination pattern table, output format |
| `references/plan-and-execute.md` | Plan template, plan principles, execution principles, MAINTAIN.md integration |
| `references/paper-reading-dispatch.md` | DOI handling, S2 fallbacks, turn budget, GPT-5.4 strengths/weaknesses for papers |
| `references/agent-system-prompt.md` | Full system prompt for subagent dispatch |

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Commit contamination — when dispatch-research agents don't use worktree isolation, their uncommitted changes get swept into the parent session's next commit.**
