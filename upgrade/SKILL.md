---
name: upgrade
description: "Use when: 'audit the codebase', 'find bugs', 'what can be improved across the project'. Full codebase review via Gemini+GPT parallel analysis. Phased: inventory → brainstorm → research → plan → review → implement. NOT for single-change review (use /review) or session quality (use /observe)."
user-invocable: true
argument-hint: <mode> [project or target]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: high
---

# Upgrade — Consolidated Codebase Improvement

Five modes covering the full improvement lifecycle: find bugs, strengthen enforcement, discover novel analyses, optimize agent discoverability, and forensic concept tracking.

## Modes

| Mode | Trigger | What it does | Source skill |
|------|---------|-------------|--------------|
| `audit` | `audit [path]` | Gemini+GPT parallel bug-finding, triage table, per-finding verify+rollback | project-upgrade |
| `harness` | `harness [path]` | Architecture-focused: typed guarantees, enforcement gaps, duplicate definitions | project-upgrade --harness |
| `discover` | `discover [path]` | Novel analysis discovery: inventory, brainstorm, research, plan, review, implement | novel-expansion |
| `pliability` | `pliability [path]` | Make files agent-discoverable: split monoliths, rename for self-description, build indexes | agent-pliability |
| `forensics` | `forensics [--days N] [--project P]` | Longitudinal concept lifecycle analysis, rule decay, survival metrics, predictions | evolution-forensics |

Parse mode from the first word of `$ARGUMENTS`. Default to `audit` if no mode given.

---

## Mode: audit

Feed entire codebase to Gemini 3.1 Pro (1M context) + GPT-5.4 in parallel, get structured findings, triage with disposition table, execute fixes with verification and rollback. Each verified change gets its own git commit.

### Pipeline

| Phase | What | Reference |
|-------|------|-----------|
| 0 | Pre-flight: env, backlog gate, language detect, baseline | `references/preflight-scripts.md` |
| 1 | Dump codebase (diff-aware or full) | `references/codebase-dump.md` |
| 2 | Parallel Gemini + GPT analysis | `references/model-prompts-standard.md` |
| 3 | Cross-validation (if `--thorough`) | `references/cross-validation.md` |
| 4 | Extract, auto-validate, triage | `references/triage-procedures.md` |
| 5 | Execute with per-finding verify+rollback | `references/execution-loop.md` |
| 6 | Report, MAINTAIN.md integration, baseline SHA | `references/report-template.md` |

### Effort tiers

- **Quick** (`audit --quick`): Phase 0-2 only. Findings list, no execution. ~2 minutes.
- **Standard** (`audit`): Full pipeline. ~15-30 minutes.
- **Thorough** (`audit --thorough`): Adds GPT cross-validation. ~30-60 minutes.
- **Deferred** (`audit --deferred`): Re-triage prior deferrals. Skips Phases 1-3. See `references/deferred-retriage.md`.

### Cross-model dispatch

Uses `~/Projects/skills/review/scripts/model-review.py` for Gemini+GPT parallel dispatch. Provider names: Google is `-p google` (not `-p gemini`). Always pass `--max-tokens 65536` on Gemini dispatches.

### Why dual-model?

Cross-family review catches 31pp more errors than single-model (FINCH-ZK). Same-model review is a martingale. Gemini gets pattern detection + 1M context; GPT gets formal reasoning + type system depth.

### Triage rules

**Disposition evidence requirements:**
- **DEFER with "no incidents"**: Must `grep -i KEYWORD CLAUDE.md` and show zero matches. Unverified "no incidents" claims miss documented pitfalls.
- **REJECT with "already exists"**: Must cite the specific file:line or test name.
- **DEFER without grepping**: Before deferring, grep for callers/usage. "Needs canary validation" for dead code (zero callers) is overcautious.

**Finding categories (priority order):**
BROKEN_REFERENCE > ERROR_SWALLOWED > IMPORT_ISSUE > DUPLICATION > PATTERN_INCONSISTENCY > MISSING_SHARED_UTIL > DEAD_CODE > NAMING_INCONSISTENCY > HARDCODED > COUPLING

### Anti-patterns

- **"Top N" triage.** All APPLY findings get implemented. Don't self-select a subset.
- **Batch apply without verification.** Each change MUST be verified independently.
- **Trusting model file paths.** Verify every path before editing. Gemini hallucinates paths ~15%.
- **Trusting "this function is never called."** Grep the codebase. Dynamic dispatch is invisible to static analysis.
- **Rubber-stamping model findings as triage.** You have project context the models don't: vetoed decisions, deliberate exclusions, runtime environment, dead code status. Cross-check EVERY finding before presenting the disposition table.

### Evaluation scorecard

| Metric | Target | Failure Threshold |
|--------|--------|-------------------|
| Finding correctness | >=60% verified | <40% |
| Apply success rate | >=80% retained | <60% |
| Zero unreviewed changes | 100% | Any violation |
| No test regression | Baseline pass -> post-run pass | Any regression |
| Static error reduction | Errors_after <= Errors_before | Errors increase |

---

## Mode: harness

Architecture-focused deep analysis for agent-developed codebases. Finds enforcement gaps, not current bugs. Prevents future bug categories.

### When to use

- Codebase is primarily agent-developed (enforcement > convention)
- After a standard audit has already cleaned obvious bugs
- When the goal is "fewer categories of future bugs" not "fewer current bugs"
- When the codebase has grown to 50+ files with shared modules

### What it finds that audit misses

- Pydantic roundtrips (models immediately `.model_dump()`'d back to dicts)
- Open vocabularies (string fields that should be StrEnum)
- Missing Protocols (duck-typed interfaces with no structural contract)
- Duplicate definitions (constants/sets defined in N files instead of imported from one)
- `dict[str, Any]` returns from high-traffic functions
- Missing import-time checks and runtime invariants

### Pipeline

Same as audit but uses Phase 2H prompts: `references/model-prompts-harness.md`

### Triage differences

Standard triage asks "is this a real bug?" Harness triage asks:
1. Does the enforcement already exist? (Models hallucinate missing features at ~40% rate)
2. How many callers does this affect? (Grep the function/type, count importers)
3. Is the "duplicate" actually intentional variation?
4. What's the injection point? (Can we change one function, or do we need N file edits?)

Apply threshold: items that affect <3 files or prevent <1 known bug class -> DEFER.

---

## Mode: discover

Systematically discover what's missing from a codebase, validate feasibility, and implement. Six phases, each with explicit gates to prevent known failure modes.

### Failure mode gates (mandatory)

| # | Failure | Prevention Gate |
|---|---------|-----------------|
| F1 | Researching already-built features | **Inventory gate**: grep `scripts/*.py` for concept keywords before ANY research |
| F2 | Codex CLI as file-output tool | **Tool gate**: use `llmx -o file.md`, never `codex -q "write to X"` |
| F3 | Gemini Pro timeout on large context | **Context gate**: summarize to <15KB for Gemini Pro; <50KB for GPT-5.4 |
| F4 | Duplicate frontier candidates re-entering | **Idempotency gate**: maintain existing-ID ban list |
| F5 | MCP tool-call schema mismatch | **Schema gate**: validate payload shape before dispatch |
| F6 | Fixed survivor quota padding weak ideas | **Calibration gate**: default 0-2 survivors; 0 is healthy |
| F7 | Concept duplicates under new phrasing | **Semantic dedup gate**: check concept overlap, not just IDs |
| F8 | Long memo append corruption | **Append-at-tail gate**: inspect file tail before every append |

### Pipeline

| Phase | Budget | Gates | Reference |
|-------|--------|-------|-----------|
| 1. Inventory | ~10% | F1, F7 | `references/phase-1-inventory.md` |
| 2. Brainstorm | ~15% | F1, F4 | `references/phase-2-brainstorm.md` |
| 3. Research | ~25% | F1-F6 | `references/phase-3-research.md` |
| 4. Plan | ~15% | -- | `references/phase-4-plan.md` |
| 5. Model Review | ~15% | F3 | `references/phase-5-review.md` |
| 6. Implement | ~20% | -- | `references/phase-6-implement.md` |

### Key judgments

- Up to 3 Claude agents + 2 llmx GPT-5.4 in parallel. One idea per agent.
- Survivor calibration: default 0-2. A 0-survivor pass is healthy.
- Every object must have a caller -- dead code with a plan does not pass.
- Can stop after Phase 4 if user wants to implement later.

---

## Mode: pliability

Make a project's files more discoverable for agents. File names alone should tell an agent what to read before acting on any given task.

### Core insight

A file name is the cheapest index entry. If the name is good enough, the agent knows to read it without needing a rule. A file called `context-rot-mitigation-strategies.md` self-triggers when the task involves context. A file called `notes.md` triggers nothing.

### Pipeline

**Phase 1: Scan** -- inventory knowledge files (docs, research, CLAUDE.md, skills, scripts). For each file note line count, name descriptiveness, section count.

**Phase 2: Identify problems:**
- **Monoliths**: >150 lines with 3+ `##` sections covering different topics. Split candidates.
- **Cryptic names**: names that don't tell you what's inside or when to read it. Rename candidates.
- **Missing index**: CLAUDE.md has no section mapping docs/research to "when to consult."
- **Iterative content**: dated iterations of the same analysis are NEVER candidates for archival or deletion. They are candidates for indexing.

**Phase 3: Propose changes** -- output a table (monoliths to split, files to rename, index to add/update). Ask the user before proceeding.

**Phase 4: Execute** -- for approved changes only:
- Splitting: extract sections, preserve front matter, add provenance note, cross-reference siblings. Commit: `[pliability] Split {original} into {n} topic files`
- Renaming: check references first (`grep -r`), `git mv`, update references. Commit: `[pliability] Rename {old} -> {new} for discoverability`
- Indexing: add/update Research & Docs Index section in CLAUDE.md with "Consult before" triggers. Commit: `[pliability] Add research index to CLAUDE.md`

**Phase 5: Verify** -- `ls` affected directories, read CLAUDE.md index, check for broken references.

### What this mode does NOT do

- Rewrite file contents (only splits and moves)
- Change code logic or tests
- Modify CLAUDE.md beyond the index section
- Touch files outside the project root
- Rename conventionally-named files (README, CLAUDE.md, pyproject.toml)

---

## Mode: forensics

Longitudinal analysis of how the codebase actually evolves. Tracks concepts through lifecycle states, joins AI sessions to downstream outcomes, measures which rules decay and which fixes stick.

**session-analyst** sees one session. **design-review** sees workflow patterns. **forensics** sees the trajectory.

### Argument parsing

- `--days N` (default: 14) -- lookback window
- `--project PROJECT` -- single project focus (default: all)
- `--phase N` -- start from specific phase (for resuming)
- `--quick` -- phases 1-2 only, skip prediction

### Pipeline

**Phase 1: Evolution Index** -- data collection. The index IS the skill; analysis without evidence is speculation.
1. Git history + session attribution across projects. See `references/git-extraction.md`.
2. Commit classification (FIX / FIX-OF-FIX / REVERT / FEATURE / RULE / RESEARCH / CHORE). See `references/commit-classification.md`.
3. Session->commit->outcome join. See `references/session-outcome-joins.md`.
4. Concept lifecycle inference (RESEARCH -> PROTOTYPE -> INTEGRATED -> PROMOTED / NARROWED / SUPERSEDED / RETIRED). See `references/concept-lifecycle.md`.
5. Cross-reference improvement-log, hook triggers, failure modes, vetoed decisions. See `references/git-extraction.md` (Phase 1e).

**Phase 2: Pattern Extraction + Decay Metrics** -- instances become classes.
1. Failure patterns: fix-of-fix chains, session-correlated fragility, build-then-retire, concept stalls (PROTOTYPE >7 days).
2. Rule compliance decay: compliance at day 1/7/14. Half-life <14d = promote to hook. Half-life >30d = instruction is working.
3. Improvement-log cycle time: median finding->implemented, stuck findings (>14d), zombie findings.
4. Reinvention detection: retired/superseded concepts being rebuilt = retrieval failure, not building failure.
5. Failure class taxonomy. See `references/pattern-extraction.md`, `references/failure-taxonomy.md`.

**Phase 3: Causal Analysis + Survival** -- why mitigations fail, artifact survival stats.
1. Mitigation failure modes: COVERAGE_GAP / DECAY / NOVEL / ROUTING_GAP / SEMANTIC. See `references/causal-analysis.md`.
2. Artifact survival analysis by type (hook, script, rule, research memo).
3. Root cause clustering.

**Phase 4: Predictions** -- ranked proposals for what to build next.
1. Rank by `frequency x blast_radius x (1 - mitigation_coverage)`.
2. Veto check against `vetoed-decisions.md` and Claude Code native features.
3. Final output: system health metrics, priority actions, deferred proposals, concept lifecycle summary. See `references/predictions.md`.

### Key judgment calls

- **<10 commits in window**: data is too thin. Report "insufficient data", suggest extending `--days`.
- **Rule decay -> hook promotion**: half-life <14 days is the trigger.
- **Reinvention vs. retrieval**: fix is surfacing existing things, not building more.
- **Concept stalls**: PROTOTYPE >7 days with no commits = recommend retire or integrate.
- **Don't conflate frequency with severity.** Rare catastrophic > frequent trivial.

---

## Shared Anti-Patterns

- **Over-scaffolding.** Don't add monitoring, CI/CD, auth, or enterprise patterns to personal projects.
- **Omitting project context from model prompts.** Without CLAUDE.md purpose + recent git history, models flag theoretical bugs that can't happen.
- **Don't maintain a manual concept registry.** Infer from git history and improvement-log. Manual upkeep rots.
- **Don't re-propose vetoed decisions.** Check `vetoed-decisions.md` before proposing.
- **Don't count dev effort as cost.** Filter by maintenance burden.
- **Don't fabricate instances.** Every failure class cites a commit hash or improvement-log entry.

## Known Limitations

- **Dynamic dispatch**: `getattr()`, `importlib.import_module()`, CLI `entry_points` invisible to static analysis.
- **Test coverage**: No tests = verification degrades to syntax/import checks only.
- **Monorepos**: >500K tokens need splitting. Run per-package.

$ARGUMENTS
