# Dispatch reference history

Captured 2026-09-05 before the Astra reference corrections. These are exact prior
source bodies, retained as historical evidence rather than current instructions.
The 2026-03-18 GPT-5.4 rates and incidents are dated observations; other old
capability, quota, and output-loss claims are not current runtime guarantees.
Use the active references and current dispatch guide for operational instructions.

## Prompt construction

Source: `research/references/prompt-construction.md`. Snapshot SHA-256: `5e7987e65378dd36cd16bde5fd92ad1eda3286b8a89651b20708f313cee75919`.

`````markdown
<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Prompt Construction

## Target selection

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

## Prompt structure

Every prompt must be self-contained and file-output-oriented:

```
Read [2-5 specific file paths]. For each [concrete thing], check:
(a) [specific verifiable property]
(b) [specific verifiable property]
Cross-reference [A] against [B]. Categorize findings as: [defined categories].
Cite file:line for every finding.
Save to [specific output path].
```

## Good patterns

- "Read X and Y, compare field Z" — grounded comparison
- "For each item in X, verify it exists in Y" — completeness check
- "Trace the data flow from A through B to C" — wiring audit
- "Count/rank/compute" — plays to GPT-5.4 math strength

## Bad patterns

- "Investigate X" — too vague, produces slop
- "Research best practices" — needs web, Codex can't
- "Fix the code" — audits should REPORT, not MODIFY
- "Check if everything works" — no specific properties
`````

## Verification procedure

Source: `research/references/verification-procedure.md`. Snapshot SHA-256: `38827cdb40339249eae8a0106882fbcd6f712e96b2970af77e46dd92e1cd85a9`.

`````markdown
<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Verification Procedure

This is the critical phase. Codex findings have a ~28% error rate. Every finding must be checked.

## Verification checklist

For each audit output:
1. **Exists and has substance** — file exists, >50 lines, not truncated
2. **File paths are real** — grep/glob the cited paths, reject invented ones
3. **Line numbers are accurate** — read the cited file:line, confirm the claim
4. **Counts are correct** — re-run the counting logic yourself (e.g., `wc -l`, `jq length`, `grep -c`)
5. **Classifications are defensible** — a "bug" claim should be a real bug, not a style preference

## Common Codex hallucination patterns

| Signal | Example | Fix |
|--------|---------|-----|
| Invented file paths | `src/auth/middleware.py` when no auth/ exists | Grep for the actual location |
| Wrong counts | "17 orphan files" when actual is 10 | Re-count yourself |
| Phantom features | "missing error handling in X" when X has try/except | Read the actual code |
| Inflated severity | "critical security bug" for a missing docstring | Downgrade or drop |
| Stale references | Citing code that was refactored away | Check git log for the file |
| False fix claims | "This was already fixed" when git log shows no such commit | Verify with `git log --grep` |
| Wrong DOIs | Agent "corrects" a DOI to a different paper | Verify DOI resolves to the claimed paper |

**Mechanical citation gate (finalize):** follow [paper evidence checks](paper-evidence.md#mechanical-citation-gate-for-memo-artifacts) for the current command, blocking/advisory distinction, and parser limitations. The gate tests identifier existence and venue; source inspection still verifies that the identifier matches the claimed paper and finding.

**2026-03-18 session note:** In a 13-tool paper audit, GPT-5.4 had **zero hallucinations** in critical findings (bugs, threshold mismatches, config errors). All verified correct. The ~28% error rate is concentrated in counts, severity grading, and external knowledge claims — not in code-reading accuracy. Code-grounded findings (file:line citations) were consistently reliable.

## Verification output

Produce a verified findings summary:
- **Confirmed findings** (with corrected details where needed)
- **Rejected findings** (with reason: hallucinated path, wrong count, etc.)
- **Corrected findings** (finding was directionally right but details were wrong)

Example from this project's audit session:
```
Audit claimed: "5% test coverage, 17 orphan files, 3 missing parsers"
Verified:       14% test coverage, ~10 orphan files, 12 missing parsers
```
`````

## Plan and execute

Source: `research-ops/references/plan-and-execute.md`. Snapshot SHA-256: `4da86f75c2f338dea8d10b2ca7b4f96fd742851cd43b399850efe1c75ccdee72`.

`````markdown
<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Plan and Execute

## Phase 4: Plan structure

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

## Plan principles

1. **Group by impact** — bugs before drift before hygiene
2. **Cite the verified finding** for each fix — traceability from audit -> plan -> commit
3. **Include verification commands** — how to confirm each fix worked
4. **Estimate scope honestly** — "~10 min" not "trivial"
5. **Flag deferred items** — things found but not worth fixing now (with reason per item, not a batch cutoff)
6. **Phase boundaries** — commit after each phase, not one giant commit
7. **Fix ALL verified findings** — don't self-select "top N" and implicitly drop the rest. Every confirmed finding gets a plan entry. If something must be deferred, give it an explicit disposition with a reason.

## Plan approval

Present the plan to the user. Wait for approval before executing. If the plan has 3+ phases, offer to execute phase-by-phase with checkpoints.

## Phase 5: Execution principles

1. **Read before editing** — always read the target file before modifying
2. **One logical change per commit** — granular semantic commits
3. **Commit after each phase** — not one big commit at the end
4. **Run tests after code changes** — `uv run pytest tests/` or equivalent
5. **Verify each fix** against the plan's verification commands
6. **Fix the neighborhood when it unblocks progress** — incidental cleanup (lint markers, related bugs, broken adjacent code) is part of the work. The only thresholds: split when >100 lines or when the cleanup touches a public API/contract.
7. **Parallel where possible** — use Agent tool for independent file edits
8. **Verify paths before fixing paths** — when fixing a wrong file path, run `find` for actual location + `head -5` to check structure before editing. Don't guess from directory names (3-iteration failure observed)
9. **Run the script after each fix** — don't batch all fixes then test. Optional fields with explicit `None` values, wrong JSON structures, etc. only surface at runtime

## Multi-agent commit safety

If SessionStart reported `PEER SESSION` (same checkout), other agents may `git add` your uncommitted edits under wrong commit messages. Mitigations:
- **Commit after each fix**, not batched at the end of a phase
- Or use `isolation: worktree` for the entire dispatch-research session
- Never leave edited files uncommitted while background agents are running

## Commit message format

Reference the audit finding:
```
[scope] Verb thing — why (from audit)
```

## Post-execution

- Verify no uncommitted changes remain
- Run full test suite
- Summarize: N findings addressed, M commits, any deferred items

## MAINTAIN.md Integration

If `MAINTAIN.md` exists in the project root (project uses `/maintain`), **you must** also:
- Append to `## Log`: `YYYY-MM-DD | dispatch-research | N findings, M applied, D deferred | [commit range]`
- Append deferred findings to `## Queue` with IDs continuing the M00N sequence
- Append applied fixes to `## Fixed`
- Never write placeholder commit refs such as `uncommitted`. If code commits are likely in the same session, defer the `MAINTAIN.md` update until the real commit hash or range exists, then write the final entries in one pass.

This feeds results into the SWE quality lane so `/maintain` can track them.
`````

## Paper reading dispatch

Source: `research/references/paper-reading-dispatch.md`. Snapshot SHA-256: `ebe67b27f15587c747938b0e74b05857a7320dae04e91e5b3d09eef2b04ae16a`.

`````markdown
<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Paper-Reading Dispatch (Research Audits)

When auditing tool implementations against source papers:

## DOI handling

- Never hardcode DOIs in prompts — they're often wrong (3/4 were wrong in the 2026-03-18 genomics audit). Tell agents to SEARCH for the paper by title/author, then verify the DOI matches.
- Tell agents: "Search for the paper first. Do not trust the DOI I provide — verify it resolves to the correct paper."

## S2 fallbacks

- Semantic Scholar (S2) API goes down periodically (403 errors). Tell agents: "If search_papers with S2 fails, retry with `backend='openalex'`. If fetch_paper fails, use exa to find the paper on PMC or the publisher site."
- All 4 agents in the 2026-03-18 session hit S2 403s but recovered via OpenAlex + PMC full text.

## Paper-reading turn budget

- Fetching a paper + reading a script + comparing + writing a report = ~6-8 tool calls minimum per tool.
- With Codex's ~15-20 turn limit, each agent can cover 2-3 tools (not 4+).
- Have agents write findings incrementally after each tool, not in one synthesis at the end.

## Output preservation

- Codex sandbox file writes can be cleaned up on agent exit. The `-o` flag output can also disappear.
- **Read output files while agents are still running** (poll with `while` loop checking file existence).
- Immediately `git add` or copy files once found. Don't wait for all agents to complete.
- If files vanish after agent completion: the content is lost. Recreate from conversation context if you read it during execution.

## What GPT-5.4 does well for paper audits

- Code-grounded comparison (reading scripts, citing file:line) — consistently accurate
- Identifying threshold mismatches between configs and paper recommendations
- Finding real bugs (missing imports, config path errors, mode drift)
- Correcting wrong DOIs and finding the right papers

## What GPT-5.4 does poorly

- Severity grading (tends to inflate)
- Claiming things are "missing" when they exist in different files
- External knowledge claims about API behavior, library features (verify these)

Codex CLI only supports OpenAI models. For Claude/Gemini dispatch, use `llmx` or Claude Code subagents. Consult `/model-guide` for task-specific routing if uncertain.
`````

## Agent system prompt

Source: `research/references/agent-system-prompt.md`. Snapshot SHA-256: `e783c9b1d97abbeb7758d03a449992b51416065704e46f80354e844fd7ef487b`.

`````markdown
<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Agent System Prompt

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
what and why, verification commands. Write plan to a file (.claude/plans/ or docs/audit/)
— in-context update_plan() is lost on compaction. Present to user for approval.

PHASE 5 — EXECUTE (~25%): After approval, implement. Read before editing. One
commit per logical change. Run tests after code changes. Verify each fix. Don't
over-engineer — fix what was found, nothing more.

Stop points: User may say "just audit" (→ stop after Phase 3), "plan only"
(→ stop after Phase 4), or "full auto" (→ all 5 phases without pause).
Default: pause for approval between Phase 4 and Phase 5.
```
`````

