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

## Pipeline overview

```
Phase 1: RECON          Read project state, identify what changed, find gaps
Phase 2: DISPATCH       Craft prompts, fire 3-5 parallel Codex audits
Phase 3: VERIFY         Check findings against actual code, correct errors
Phase 4: PLAN           Synthesize verified findings into execution plan
Phase 5: EXECUTE        Implement the plan (with user approval)
```

---

## Phase 1: Recon (~15% of effort)

Read whatever gives you the lay of the land:
- `CLAUDE.md` / `.claude/CLAUDE.md` (project instructions, index)
- `.claude/overviews/` (code inventory, if exists)
- Plans (`.claude/plans/`)
- Recent git history (`git log --oneline -30`)
- Outstanding work, TODOs, known gaps
- Any `docs/audit/` directory (skip already-completed audits)

**Output:** Mental model of project state, list of areas worth auditing.

## Phase 2: Dispatch (~25%)

### Target selection

Look for these categories of useful work:

| Category | Example | Good Codex target? |
|----------|---------|-------------------|
| **Wiring** | Does data flow correctly between components? | Yes — cross-file tracing |
| **Drift** | Do configs/docs match code? Counts match reality? | Yes — counting/comparing |
| **Completeness** | Are all expected outputs produced? | Yes — checklist verification |
| **Impact** | What downstream effects do recent changes have? | Yes — grep + trace |
| **Hygiene** | Dead code, orphan files, stale state? | Yes — existence checks |
| **Integration** | Do cross-module consumers still work? | Yes — interface matching |
| **Correctness** | Do algorithms match their cited sources? | Partial — logic only |

Don't generate prompts for things obvious from reading the code. Target things requiring **cross-referencing multiple files**, **counting/comparing**, or **tracing data flow**.

### GPT-5.4 via Codex — capabilities

**CAN do:** Read any file, run shell commands (grep/find/wc), write files, cross-reference, count/compare/compute, produce structured output (tables, matrices, categorized lists). With `--search`: web search. With configured MCPs: scite, paper-search, exa, brave, etc.

**CANNOT do:** Database queries, conversation history, `uv`/project-specific CLIs (sandbox lacks project environment — `uv` panics in system-configuration crate). **28% factual error rate on external knowledge** — never trust claims about APIs/libraries. Also hallucinates fix status — may claim "this was already fixed" when it wasn't.

**Turn limits:** `codex exec` has a built-in turn limit (~15-20 tool calls). Agents reading many files exhaust turns before synthesizing. Mitigations:
- **Max 5 files per agent.** Split larger audits into multiple agents.
- **Incremental output.** Tell the agent: "After reading each file, immediately write your findings for that file. Do not wait until the end to synthesize."
- **Use `-o FILE` flag** to capture the final message even if the agent runs out of turns mid-synthesis.
- **Prefer grep-first, read-targeted.** Tell agents to grep for specific patterns first, then read only the relevant line ranges — not entire files.

### Prompt structure

Every prompt must be self-contained and file-output-oriented:

```
Read [2-5 specific file paths]. For each [concrete thing], check:
(a) [specific verifiable property]
(b) [specific verifiable property]
Cross-reference [A] against [B]. Categorize findings as: [defined categories].
Cite file:line for every finding.
Save to [specific output path].
```

**Good patterns:**
- "Read X and Y, compare field Z" — grounded comparison
- "For each item in X, verify it exists in Y" — completeness check
- "Trace the data flow from A through B to C" — wiring audit
- "Count/rank/compute" — plays to GPT-5.4 math strength

**Bad patterns:**
- "Investigate X" — too vague, produces slop
- "Research best practices" — needs web, Codex can't
- "Fix the code" — audits should REPORT, not MODIFY
- "Check if everything works" — no specific properties

### Dispatch execution

```bash
mkdir -p docs/audit  # or wherever findings should go

# Parallel dispatch (max 4 when MCPs are needed)
codex exec --model gpt-5.4 --full-auto \
  -o docs/audit/codex-{slug}.md \
  "You are auditing a codebase. Read files at their full paths. \
   Cite file:line for findings. After reading each file, immediately \
   write your findings for that file — do not wait to synthesize at the end. \
   IMPORTANT: Write your report to docs/audit/{slug}.md (NOT /tmp). \
   End with a complete markdown summary of all findings. \
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

**Key flags:**
- `exec` — non-interactive mode (not the interactive `codex` command)
- `--full-auto` — sandboxed auto-approval (replaces old `--approval-mode full-auto`)
- **Do NOT use `--ephemeral`** — sandbox cleanup deletes file writes made during execution, including `-o` output. Without `--ephemeral`, session is persisted but files survive. Cost: ~100KB per session in `~/.codex/sessions/`.
- `-o FILE` — captures last agent *text* message to file. **Caveats:**
  - If the agent spends all turns on tool calls and never produces a final text response, `-o` writes nothing. Always include in prompt: "End with a markdown summary of all findings."
  - **Files written by agents inside the sandbox may be cleaned up on agent exit.** The `-o` output file itself can also be deleted by sandbox cleanup if `--ephemeral` is used. Always `git add` or `cp` output files immediately after agents complete.
  - If `-o` files are empty or missing after agent completion, check `~/.codex/sessions/` for the session — but note that reasoning payloads are encrypted and findings are NOT recoverable from logs.
- `--search` — **only works in interactive mode, NOT in `exec`**. Use MCP tools instead.

**MCP tools:** Codex shares the global MCP config (`~/.codex/config.toml`). All configured MCPs (scite, exa, brave, paper-search, etc.) are available to `exec` agents automatically.

**MCP contention:** Max 4 parallel Codex agents when MCPs are needed. Each agent starts its own MCP server instances. 5+ concurrent agents with multiple MCPs can overwhelm the system (132+ simultaneous MCP startups observed).

**S2 API outages:** Semantic Scholar returns 403 periodically. Tell agents to fall back to `backend="openalex"` for `search_papers` if S2 fails. Or instruct agents to use `exa` web search as a paper-discovery fallback.

**Output location:** Tell agents to write to the **repo** (`docs/audit/`), NOT `/tmp`. macOS cleans up `/tmp` between sessions. After agents complete, immediately `git add` the output files before they can be cleaned up.

**Fallback:** If Codex isn't installed, write prompts to `.claude/research-dispatch.md` as numbered prompts the user can copy-paste or route to another model.

## Phase 3: Verify (~20%)

This is the critical phase. Codex findings have a ~28% error rate. Every finding must be checked.

### Verification checklist

For each audit output:
1. **Exists and has substance** — file exists, >50 lines, not truncated
2. **File paths are real** — grep/glob the cited paths, reject invented ones
3. **Line numbers are accurate** — read the cited file:line, confirm the claim
4. **Counts are correct** — re-run the counting logic yourself (e.g., `wc -l`, `jq length`, `grep -c`)
5. **Classifications are defensible** — a "bug" claim should be a real bug, not a style preference

### Common Codex hallucination patterns

| Signal | Example | Fix |
|--------|---------|-----|
| Invented file paths | `src/auth/middleware.py` when no auth/ exists | Grep for the actual location |
| Wrong counts | "17 orphan files" when actual is 10 | Re-count yourself |
| Phantom features | "missing error handling in X" when X has try/except | Read the actual code |
| Inflated severity | "critical security bug" for a missing docstring | Downgrade or drop |
| Stale references | Citing code that was refactored away | Check git log for the file |
| False fix claims | "This was already fixed" when git log shows no such commit | Verify with `git log --grep` |
| Wrong DOIs | Agent "corrects" a DOI to a different paper | Verify DOI resolves to the claimed paper |

**2026-03-18 session note:** In a 13-tool paper audit, GPT-5.4 had **zero hallucinations** in critical findings (bugs, threshold mismatches, config errors). All verified correct. The ~28% error rate is concentrated in counts, severity grading, and external knowledge claims — not in code-reading accuracy. Code-grounded findings (file:line citations) were consistently reliable.

### Verification output

Produce a verified findings summary:
- **Confirmed findings** (with corrected details where needed)
- **Rejected findings** (with reason: hallucinated path, wrong count, etc.)
- **Corrected findings** (finding was directionally right but details were wrong)

Example from this project's audit session:
```
Audit claimed: "5% test coverage, 17 orphan files, 3 missing parsers"
Verified:       14% test coverage, ~10 orphan files, 12 missing parsers
```

## Phase 4: Plan (~15%)

Synthesize verified findings into an execution plan. This is a plan-mode document, not a to-do list.

### Plan structure

```markdown
# Audit Findings — Fix & Refactor Plan

**Session:** YYYY-MM-DD | **Project:** <name>

## Context
<1-2 sentences on what audits found, what was verified>

## Phase N: <Category> (<impact level>, <scope estimate>)

### NA. <Specific fix>
**Files:** `path/to/file.py:lines`
- What to change
- Why (cite the verified finding)
- How (brief implementation note if non-obvious)

## Execution Order
<Phases ordered by: bugs first, then drift, then structural, then cleanup>

## Verification
<How to confirm fixes worked — specific commands>
```

### Plan principles

1. **Group by impact** — bugs before drift before hygiene
2. **Cite the verified finding** for each fix — traceability from audit → plan → commit
3. **Include verification commands** — how to confirm each fix worked
4. **Estimate scope honestly** — "~10 min" not "trivial"
5. **Flag deferred items** — things found but not worth fixing now (with reason)
6. **Phase boundaries** — commit after each phase, not one giant commit

### Plan approval

Present the plan to the user. Wait for approval before executing. If the plan has 3+ phases, offer to execute phase-by-phase with checkpoints.

## Phase 5: Execute (~25%)

After user approves the plan, implement it.

### Execution principles

1. **Read before editing** — always read the target file before modifying
2. **One logical change per commit** — granular semantic commits
3. **Commit after each phase** — not one big commit at the end
4. **Run tests after code changes** — `uv run pytest tests/` or equivalent
5. **Verify each fix** against the plan's verification commands
6. **Don't over-engineer** — fix what was found, don't refactor the neighborhood
7. **Parallel where possible** — use Agent tool for independent file edits

### Commit message format

Reference the audit finding:
```
[scope] Verb thing — why (from audit)
```

### Post-execution

- Verify no uncommitted changes remain
- Run full test suite
- Summarize: N findings addressed, M commits, any deferred items

---

## Tuning knobs

**Depth:** "quick sweep" (3-5 audits, stop at findings) → default (full loop) → "deep audit" (15+ audits)

**Scope:** Target a specific area ("audit the search module") or sweep the whole project.

**Stop point:** User can say "just audit" (stop after Phase 3), "plan only" (stop after Phase 4), or "full auto" (all 5 phases).

**Output location:** Default `docs/audit/`. User can override.

## Model selection

| Target | When | Tradeoff |
|--------|------|----------|
| `codex exec --model gpt-5.4` | Cross-referencing, counting, structured output | Free, parallel, but output extraction fragile |
| Claude Code `Agent` subagents | Same tasks + DuckDB/MCP access | Costs tokens, but output is inline — no extraction issues |
| `llmx chat --model gemini-3.1-pro-preview` | 1M context (huge file ingestion) | Best for monolithic file analysis |

**Codex vs Claude subagents (learned 2026-03-18):** For codebase audits, Claude `Agent` subagents with `subagent_type=Explore` are more reliable than Codex `exec` because: (1) output is returned directly to parent context — no `-o` extraction failures, (2) full MCP/DuckDB access, (3) no sandbox environment mismatch. Use Codex when you need 10+ parallel audits (Claude subagents are limited by parent context cost) or when the task is purely file-grep (no project tooling needed).

## Paper-reading dispatch (research audits)

When auditing tool implementations against source papers:

**DOI handling:**
- Never hardcode DOIs in prompts — they're often wrong (3/4 were wrong in the 2026-03-18 genomics audit). Tell agents to SEARCH for the paper by title/author, then verify the DOI matches.
- Tell agents: "Search for the paper first. Do not trust the DOI I provide — verify it resolves to the correct paper."

**S2 fallbacks:**
- Semantic Scholar (S2) API goes down periodically (403 errors). Tell agents: "If search_papers with S2 fails, retry with `backend='openalex'`. If fetch_paper fails, use exa to find the paper on PMC or the publisher site."
- All 4 agents in the 2026-03-18 session hit S2 403s but recovered via OpenAlex + PMC full text.

**Paper-reading turn budget:**
- Fetching a paper + reading a script + comparing + writing a report = ~6-8 tool calls minimum per tool.
- With Codex's ~15-20 turn limit, each agent can cover 2-3 tools (not 4+).
- Have agents write findings incrementally after each tool, not in one synthesis at the end.

**Output preservation:**
- Codex sandbox file writes can be cleaned up on agent exit. The `-o` flag output can also disappear.
- **Read output files while agents are still running** (poll with `while` loop checking file existence).
- Immediately `git add` or copy files once found. Don't wait for all agents to complete.
- If files vanish after agent completion: the content is lost. Recreate from conversation context if you read it during execution.

**What GPT-5.4 does well for paper audits:**
- Code-grounded comparison (reading scripts, citing file:line) — consistently accurate
- Identifying threshold mismatches between configs and paper recommendations
- Finding real bugs (missing imports, config path errors, mode drift)
- Correcting wrong DOIs and finding the right papers

**What GPT-5.4 does poorly:**
- Severity grading (tends to inflate)
- Claiming things are "missing" when they exist in different files
- External knowledge claims about API behavior, library features (verify these)

Codex CLI only supports OpenAI models. For Claude/Gemini dispatch, use `llmx` or Claude Code subagents. Consult `/model-guide` for task-specific routing if uncertain.

---

## Agent system prompt

When dispatching this as a subagent (via Agent tool or `claude --print`), use this as the prompt:

```
You are an autonomous audit-to-execution agent. You will:

PHASE 1 — RECON (~15%): Read CLAUDE.md, git log --oneline -30, .claude/plans/,
.claude/overviews/, docs/audit/ (skip completed). Build a model of what changed,
what's outstanding, where risks are.

PHASE 2 — DISPATCH (~25%): Craft 3-5 self-contained audit prompts for GPT-5.4
via Codex CLI. Each prompt: "Read [files], check [properties], cross-reference
[A vs B], cite file:line, save to docs/audit/<slug>.md". Dispatch in parallel.

PHASE 3 — VERIFY (~20%): For EVERY finding, verify against actual code. Check
file paths exist, line numbers match, counts are correct. Codex has ~28% error
rate. Produce: confirmed findings, rejected findings (with reason), corrected
findings. This phase is mandatory — never skip verification.

PHASE 4 — PLAN (~15%): Synthesize verified findings into phased execution plan.
Group by impact (bugs → drift → structural → cleanup). Include: files to change,
what and why, verification commands. Present to user for approval.

PHASE 5 — EXECUTE (~25%): After approval, implement. Read before editing. One
commit per logical change. Run tests after code changes. Verify each fix. Don't
over-engineer — fix what was found, nothing more.

Stop points: User may say "just audit" (→ stop after Phase 3), "plan only"
(→ stop after Phase 4), or "full auto" (→ all 5 phases without pause).
Default: pause for approval between Phase 4 and Phase 5.
```
