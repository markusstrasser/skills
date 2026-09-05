# Research dispatch history

Snapshot preserved on 2026-09-05. Use `codex-dispatch-mechanics.md` for the current dispatch contract; the removed flags and old output/overhead assumptions below are historical.

<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Codex Dispatch Mechanics

## Dispatch execution

```bash
mkdir -p docs/audit  # or wherever findings should go

# Parallel dispatch (max 4 when MCPs are needed)
codex exec --model gpt-5.4 --full-auto \
  -o docs/audit/codex-{slug}.md \
  "You are auditing a codebase. Read files at their full paths. \
   Cite file:line for findings. \
   Do NOT create any files or write any templates. Just read code and analyze. \
   BUDGET: Read at most 5 files. After that, STOP and synthesize. \
   Spend 70% of effort reading, 30% writing your report. \
   A partial report is infinitely better than no report. \
   Your final text message will be captured automatically. \
   End with a COMPLETE markdown report of all findings. \
   TASK: [prompt]" &

codex exec --model gpt-5.4 --full-auto \
  -o docs/audit/codex-{slug}.md \
  "..." &

wait

# IMMEDIATELY copy -o output after agents finish (sandbox cleanup can delete them)
for f in docs/audit/codex-*.md; do
  [ -f "$f" ] && cp "$f" "$f.bak"
done
```

## Key flags

- `exec` — non-interactive mode (not the interactive `codex` command)
- `--full-auto` — sandboxed auto-approval (replaces old `--approval-mode full-auto`)
- **Do NOT use `--ephemeral`** — sandbox cleanup deletes file writes made during execution, including `-o` output. Without `--ephemeral`, session is persisted but files survive. Cost: ~100KB per session in `~/.codex/sessions/`.
- `-o FILE` — captures last agent *text* message to file. **Caveats:**
  - If the agent spends all turns on tool calls and never produces a final text response, `-o` writes nothing. Always include in prompt: "End with a markdown summary of all findings."
  - **Files written by agents inside the sandbox may be cleaned up on agent exit.** The `-o` output file itself can also be deleted by sandbox cleanup if `--ephemeral` is used. Always `git add` or `cp` output files immediately after agents complete.
  - If `-o` files are empty or missing after agent completion, check `~/.codex/sessions/` for the session — but note that reasoning payloads are encrypted and findings are NOT recoverable from logs.
- `--search` — **only works in interactive mode, NOT in `exec`**. Use MCP tools instead.

## MCP tools

Codex shares the global MCP config (`~/.codex/config.toml`). 9 configured MCPs (context7, exa, research, meta-knowledge, brave-search, paper-search, perplexity, scite, codex_apps) are available to `exec` agents automatically. Each contributes to the ~37K token overhead.

## MCP contention

Max 4 parallel Codex agents when MCPs are needed. Each agent starts its own MCP server instances (9 servers x N agents). 5+ concurrent agents can overwhelm the system (132+ simultaneous MCP startups observed).

## S2 API outages

Semantic Scholar returns 403 periodically. Tell agents to fall back to `backend="openalex"` for `search_papers` if S2 fails. Or instruct agents to use `exa` web search as a paper-discovery fallback.

## Output location

Tell agents to write markdown findings to the **repo** (`docs/audit/`), NOT `/tmp`. macOS cleans up `/tmp` between sessions. If you dispatch through `meta/scripts/codex_dispatch.py`, raw stdout/stderr now default to `docs/archive/audit-logs/<run>/` whenever `--output-dir` is under `docs/audit/`. If you keep extra sweep logs yourself, put them there too, not active `docs/audit/`. After agents complete, immediately `git add` the markdown outputs before they can be cleaned up.

## Fallback

If Codex isn't installed, write prompts to `.claude/research-dispatch.md` as numbered prompts the user can copy-paste or route to another model.

## Superseded skill-root dispatch instructions — 2026-09-05

Preserved verbatim below; the current root and canonical dispatch reference supersede the fixed quotas, model limits, flags, and automatic approval pauses.

> **Cheap parallel lanes via codex subprocesses ($0).** A fleet of research lanes can run as
> background `codex exec --full-auto` workers that invoke `$research` and each write their own memo
> — same skills + MCP stack as Claude, network-backed, subscription-billed. Canary first, then fan
> out. Full mechanics + gotchas: `model-guide/references/codex-subprocess-dispatch.md`.


# Mode: dispatch

Research -> Dispatch -> Verify -> Plan -> Execute. Opus orchestrates the full loop: dispatches parallel audits to GPT-5.4 via Codex CLI, verifies findings against actual code, synthesizes an execution plan, then implements it.

## When to use

"dispatch research", "run audits", "codex sweep", "audit and fix", or when the user wants autonomous project improvement — from discovery through implementation.

**Depth modes:**
- `"quick sweep"` -> 3-5 lightweight audits, stop at findings (no execute)
- `"audit"` / default -> full 5-phase loop
- `"deep audit"` -> 15+ thorough audits, comprehensive plan

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
| `uv run python3 ~/Projects/skills/scripts/llm-dispatch.py --profile deep_review ...` | 1M context, huge file ingestion | Best for monolithic analysis |

**Use Codex for:** 5+ parallel audits, cross-file grep+read tracing, wiring/drift/completeness checks.
**Use Claude subagents for:** <3 file audits, tasks needing project-specific tooling (uv, DuckDB, MCP).

## Phase-by-phase execution

**Phase 1 -- Recon:** Read CLAUDE.md, `.claude/overviews/`, plans, `git log --oneline -30`, `docs/audit/` (skip completed). Build mental model, identify audit targets.

**Phase 2 -- Dispatch:** Craft self-contained prompts per `references/prompt-construction.md`. Execute per `references/codex-dispatch-mechanics.md`. Each prompt: "Read [files], check [properties], cross-reference [A vs B], cite file:line."

**Phase 3 -- Verify:** Every finding checked against actual code. Follow `references/verification-procedure.md`. Output: confirmed / rejected (with reason) / corrected findings.

**Phase 4 -- Plan:** Synthesize into phased execution plan per `references/plan-and-execute.md`. Fix ALL verified findings -- don't self-select "top N." Present to user; wait for approval.

**Phase 5 -- Execute:** Implement per `references/plan-and-execute.md`. Read before editing. One commit per logical change. If other agents active, commit after each fix (not batched) or use `isolation: worktree`.

## References (loaded on demand)

| File | Contents |
|------|----------|
| `references/prompt-construction.md` | Target selection categories, prompt structure, good/bad patterns |
| `references/codex-dispatch-mechanics.md` | Bash commands, flags, MCP config, `-o` caveats, fallback |
| `references/verification-procedure.md` | Verification checklist, hallucination pattern table, output format |
| `references/plan-and-execute.md` | Plan template, plan principles, execution principles, MAINTAIN.md integration |
| `references/paper-reading-dispatch.md` | DOI handling, S2 fallbacks, turn budget, GPT-5.4 strengths/weaknesses for papers |
| `references/agent-system-prompt.md` | Full system prompt for subagent dispatch |


## Retired compile search path — 2026-09-05

Native validation found that `~/Projects/personal/apps/phenome/docs` no longer exists. Removed that path from the compile search command; the live personal health, life and synthoria corpora remain in scope. Earlier command preserved:

```bash
rg -l "^#.*{concept}" ~/Projects/personal/health ~/Projects/personal/life ~/Projects/personal/synthoria ~/Projects/personal/apps/phenome/docs ~/Projects/genomics/docs ~/Projects/agent-infra/research -g '*.md'
```
