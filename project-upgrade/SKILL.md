---
name: project-upgrade
description: Autonomous codebase improvement. Standard mode finds bugs via Gemini+GPT. --harness finds architectural leverage (typed guarantees, enforcement, unification for agent-developed codebases). --deferred re-triages prior deferrals.
argument-hint: [path or --harness or --deferred or --quick or --thorough]
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Agent
  - Task
effort: medium
---

# Project Upgrade -- Autonomous Codebase Improvement

Feed entire codebase to Gemini 3.1 Pro (1M context) + GPT-5.4 in parallel, get structured findings, triage with disposition table, execute fixes with verification and rollback. Each verified change gets its own git commit.

## Prerequisites

- `llmx` CLI installed (`which llmx`)
- Gemini API key configured (for 1M context analysis)
- Clean git working tree (will error if dirty)
- Project must fit in ~500K tokens (most projects under 50K LOC do)

## Pipeline Overview

| Phase | What | Reference |
|-------|------|-----------|
| 0 | Pre-flight: env, backlog gate, language detect, baseline | `references/preflight-scripts.md` |
| 1 | Dump codebase (diff-aware or full) | `references/codebase-dump.md` |
| 2 | Parallel Gemini + GPT analysis | `references/model-prompts-standard.md` |
| 2H | Harness mode prompts (if `--harness`) | `references/model-prompts-harness.md` |
| 3 | Cross-validation (if `--thorough`) | `references/cross-validation.md` |
| 4 | Extract, auto-validate, triage | `references/triage-procedures.md` |
| 5 | Execute with per-finding verify+rollback | `references/execution-loop.md` |
| 6 | Report, MAINTAIN.md integration, baseline SHA | `references/report-template.md` |
| 6D | Deferred re-triage (if `--deferred`) | `references/deferred-retriage.md` |

## Effort Tiers

- **Quick** (`--quick`): Phase 0-2 only. Produces findings list, no execution. ~2 minutes.
- **Standard** (default): Full pipeline. Triage + execute + report. ~15-30 minutes.
- **Thorough** (`--thorough`): Adds GPT cross-validation (Phase 3). ~30-60 minutes.
- **Harness** (`--harness`): Architecture-focused deep queries. See "Harness Mode" below.
- **Deferred** (`--deferred`): Re-triage prior deferrals. Skips Phases 1-3. See `references/deferred-retriage.md`.

## Critical Decisions (WHY)

### Why dual-model?

Cross-family review catches 31pp more errors than single-model (FINCH-ZK). Same-model review is a martingale. Gemini gets pattern detection + 1M context; GPT gets formal reasoning + type system depth.

### Why user approval gate?

The disposition table (Phase 4) is the kill switch. The user MUST see and approve before execution. Zero unreviewed changes is a constitutional requirement.

### Why per-finding commits?

Batch apply with no rollback granularity is the #1 failure mode. Each APPLY finding gets: snapshot -> fix -> verify -> commit (or revert). `git status --porcelain` must be empty after each finding.

### Why backlog gate?

If >50 unfixed findings exist, do not generate more. Audit-accumulation (findings pile up faster than they're fixed) is a documented anti-pattern. Fix before auditing.

## llmx Gotchas

- **Provider names:** Google is `-p google` (NOT `-p gemini`). OpenAI is `-p openai`.
- **Temperature:** Gemini 3.1 Pro locks to 1.0 server-side (thinking model) -- do NOT pass `-t`.
- **Max tokens:** Always pass `--max-tokens 65536` on Gemini dispatches -- server default is 8K, silently truncates large JSON output.
- **File input:** Use `-f` for context file, NOT `cat | pipe` (stdin dropped when prompt arg provided).
- **Multi-agent coordination:** If `pgrep -lf claude | wc -l` >= 2, check `git log --oneline -10` and plan only your delta.

## Triage Rules

### Disposition evidence requirements

- **DEFER with "no incidents"**: Must `grep -i KEYWORD CLAUDE.md` and show zero matches. Unverified "no incidents" claims miss documented pitfalls. (Evidence: 2026-03-27 retro -- G008 deferred citing "no incidents" when CLAUDE.md pitfall #18 was the exact incident.)
- **REJECT with "already exists"**: Must cite the specific file:line or test name. "Already enforced by X" without a citation is an unverified factual claim.
- **DEFER without grepping**: Before deferring, grep for callers/usage. "Needs canary validation" for dead code (zero callers) is overcautious. A 5-second grep prevents findings from rotting in the deferred queue. (Evidence: 2026-04-03 -- F004 deferred as "needs canary" was pure dead code.)

### Finding categories (priority order)

BROKEN_REFERENCE > ERROR_SWALLOWED > IMPORT_ISSUE > DUPLICATION > PATTERN_INCONSISTENCY > MISSING_SHARED_UTIL > DEAD_CODE > NAMING_INCONSISTENCY > HARDCODED > COUPLING

## Anti-Patterns

- **"Top N" triage.** If a finding is dispositioned APPLY, it gets implemented -- all of them. Don't self-select "the top 5" and silently drop the rest. If deferring, change disposition to DEFER with a per-item reason.
- **Batch apply without verification.** Each change MUST be verified independently. No rollback granularity = no safety net.
- **Trusting model file paths.** Verify every path before editing. Gemini hallucinates paths ~15% of the time.
- **Trusting "this function is never called."** Grep the codebase. Dynamic dispatch (`getattr`, CLI entry_points) is invisible to static analysis.
- **Low-severity, high-blast-radius.** NAMING_INCONSISTENCY affecting 20 files is high risk for low reward. Defer unless automated.
- **Over-scaffolding.** Don't add monitoring, CI/CD, auth, or enterprise patterns to personal projects.
- **Omitting project context from model prompts.** Without CLAUDE.md purpose + recent git history, models flag theoretical bugs that can't happen in practice.

## Harness Mode (`--harness`)

### When to use

- Codebase is primarily agent-developed (enforcement > convention)
- After a standard run has already cleaned obvious bugs
- When the goal is "fewer categories of future bugs" not "fewer current bugs"
- When the codebase has grown to 50+ files with shared modules

### The agent-vs-human tradeoff

| Dimension | Human-developed | Agent-developed |
|-----------|----------------|-----------------|
| Why bugs happen | Logic errors, edge cases | Hallucinated field names, copy-pasted definitions, wrong dict keys |
| What prevents bugs | Code review, conventions | Types, import-time checks, StrEnums -- things that produce errors |
| Cost of large refactors | High (human hours) | Near-zero (agent tokens). Scope is never a valid deferral reason. |
| What to optimize for | Fewer current bugs | Fewer categories of future bugs |

### What it finds that standard mode misses

- Pydantic roundtrips (models immediately `.model_dump()`'d back to dicts)
- Open vocabularies (string fields that should be StrEnum)
- Missing Protocols (duck-typed interfaces with no structural contract)
- Duplicate definitions (constants/sets defined in N files instead of imported from one)
- `dict[str, Any]` returns from high-traffic functions
- Missing import-time checks and runtime invariants

### Triage differences

Standard triage asks "is this a real bug?" Harness triage asks:
1. Does the enforcement already exist? (Models hallucinate missing features at ~40% rate)
2. How many callers does this affect? (Grep the function/type, count importers)
3. Is the "duplicate" actually intentional variation?
4. What's the injection point? (Can we change one function, or do we need N file edits?)

Apply threshold: items that affect <3 files or prevent <1 known bug class -> DEFER.

### Expected yield vs standard

| Metric | Standard | Harness |
|--------|----------|---------|
| Findings per model | 10-30 | 5-15 (fewer, higher leverage) |
| Hallucination rate | 40-55% | 40-55% (same) |
| Lines changed per finding | 5-20 | 20-200 (structural) |
| Bug classes prevented | 0 (fixes existing) | 1-3 per finding (prevents future) |

Full prompts and context preparation: `references/model-prompts-harness.md`

## Known Limitations

- **Dynamic dispatch**: `getattr()`, `importlib.import_module()`, CLI `entry_points` invisible to static analysis. Dead code findings for these need manual verification.
- **Test coverage**: No tests = verification degrades to syntax/import checks only.
- **Monorepos**: >500K tokens need splitting. Run per-package.
- **Non-Python**: JS and Rust support functional but less tested.

## Evaluation Scorecard

| Metric | Target | Failure Threshold |
|--------|--------|-------------------|
| Finding correctness | >=60% verified | <40% |
| Apply success rate | >=80% retained | <60% |
| Zero unreviewed changes | 100% | Any violation |
| No test regression | Baseline pass -> post-run pass | Any regression |
| Static error reduction | Errors_after <= Errors_before | Errors increase |
| Time-to-value | <=45 min (<150K LOC) | >2 hours |
