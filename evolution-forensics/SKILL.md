---
name: evolution-forensics
description: "Longitudinal codebase forensics — tracks concept lifecycles (not just commits), joins sessions to outcomes, measures rule decay and self-improvement velocity, predicts tooling from survival analysis and failure diffusion. The time-series complement to session-analyst (snapshot) and design-review (architecture)."
user-invocable: true
context: fork
argument-hint: "[--days N] [--project PROJECT] [--phase 1|2|3|4] [--quick]"
effort: high
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
  - Agent
---

# Evolution Forensics

Longitudinal analysis of how the codebase *actually evolves*. Tracks concepts through lifecycle states, joins AI sessions to their downstream outcomes, measures which rules decay and which fixes stick, and predicts what tooling to build next.

**session-analyst** sees one session. **design-review** sees workflow patterns. **This skill** sees the trajectory — which corrections stuck, which regressed, which failure classes resist mitigation across weeks.

## Current Environment
`!echo "Date: $(date +%Y-%m-%d) | CWD: $(basename $PWD) | Projects: $(ls ~/Projects/ | wc -l | tr -d ' ') | Improvement-log entries: $(grep -c '^### ' ~/Projects/meta/improvement-log.md 2>/dev/null) | Hook count: $(grep -c '"command"' ~/.claude/settings.json 2>/dev/null)"`

## Argument Parsing

Parse `$ARGUMENTS`:
- `--days N` (default: 14) — lookback window
- `--project PROJECT` — single project focus (default: all of meta, intel, selve, genomics, skills)
- `--phase N` — start from specific phase (for resuming)
- `--quick` — phases 1-2 only, skip prediction

---

## Phase 1: Evolution Index

Data collection. Three layers: commits, session→commit joins, and concept inference.

### 1a. Git History + Session Attribution

Extract commits with Session-ID trailers for session→commit joining:

```bash
DAYS=${DAYS:-14}
ARTIFACT_DIR="$HOME/Projects/meta/artifacts/evolution-forensics"
mkdir -p "$ARTIFACT_DIR"

for PROJECT in meta intel selve genomics skills; do
  PROJECT_DIR="$HOME/Projects/$PROJECT"
  [ -d "$PROJECT_DIR/.git" ] || continue

  echo "=== $PROJECT ===" >> "$ARTIFACT_DIR/git-history.md"
  git -C "$PROJECT_DIR" log \
    --since="$DAYS days ago" \
    --format="COMMIT|%H|%ai|%an|%s|%(trailers:key=Session-ID,valueonly)" \
    --numstat \
    >> "$ARTIFACT_DIR/git-history.md"
  echo "" >> "$ARTIFACT_DIR/git-history.md"
done
```

### 1b. Commit Classification

Classify each commit:

| Type | Signal | Example |
|------|--------|---------|
| **FIX** | fix, repair, correct, patch, resolve | `[hooks] Fix trap swallowing exit 2` |
| **FIX-OF-FIX** | Fixes a file touched by a FIX within 3 days | Same file, two fixes, short gap |
| **REVERT** | revert, undo, drop, remove, retire | `[infra] Drop finding-triage DB` |
| **FEATURE** | New capability, wiring, integration | `[api] Wire rate-limit refresh` |
| **RULE** | CLAUDE.md, rules/, hooks, improvement-log | `[rules] Extend probe-before-build` |
| **RESEARCH** | research/, decisions/ | `[research] Agent scaffolding landscape` |
| **CHORE** | Docs, formatting, deps | `[docs] Regenerate codebase map` |

Extract per commit: scope, type, files_changed, churn (lines +/-), Session-ID (if present).

### 1c. Session→Commit→Outcome Join

Build the causal chain. For commits with Session-ID trailers:

1. Group commits by Session-ID → "what did this session produce?"
2. For each session's commits, check: were any files subsequently touched by a FIX or FIX-OF-FIX? → "did this session's work need correction?"
3. For fix-of-fix chains, trace back: which session introduced the original code?

Output a session outcome table:

```markdown
## Session Outcomes
| Session-ID | Project | Commits | Files | Fix-of-fix within 3d? | Subsequent corrections |
|-----------|---------|---------|-------|----------------------|----------------------|
```

Sessions with high correction rates are producing fragile code. Sessions with zero corrections are producing durable code. The *difference* between them is the learning signal.

### 1d. Concept Lifecycle Inference

Concepts are tracked entities that persist across file renames, merges, and deletions. Derive them from git history — don't maintain a manual registry.

**How to identify concepts:** A concept is a cluster of related commits sharing a scope tag, touching overlapping files, or referencing the same improvement-log finding. Examples:
- `dup-read-detection` — research memo → session-analyst detection rule → hook → promoted to block
- `finding-triage-db` — script → DB → retired (full lifecycle, short-lived)
- `knowledge-substrate` — MCP server → retired, replaced by hook + propagate-correction.py

For each concept in the window, infer its current lifecycle state:

| State | Signal |
|-------|--------|
| **RESEARCH** | Exists only in research/, decisions/, or brainstorm artifacts |
| **PROTOTYPE** | Script or tool exists but isn't wired into any workflow |
| **INTEGRATED** | Wired in: called by a skill, hook, pipeline, or justfile recipe |
| **PROMOTED** | Graduated: advisory→blocking, optional→default, project→cross-project |
| **NARROWED** | Scope reduced: exceptions added, conditions tightened |
| **SUPERSEDED** | Replaced by something else (check vetoed-decisions.md, commit bodies) |
| **RETIRED** | Deleted or archived |

Track **typed relationships** between concepts using this vocabulary:
- **implements** — concept X implements idea from memo Y
- **replaces** — concept X supersedes concept Y
- **narrows** — concept X restricts scope of concept Y
- **extends** — concept X broadens concept Y
- **deprecates** — concept X makes concept Y obsolete

Write concept lifecycle to `$ARTIFACT_DIR/concept-lifecycle.md`:

```markdown
## Concept: [name]
**State:** INTEGRATED
**First seen:** 2026-03-10 (research/agent-memory-architectures.md)
**Current manifestation:** scripts/propagate-correction.py + hook
**Relationships:** replaces knowledge-substrate, implements correction-propagation
**Trajectory:** RESEARCH → PROTOTYPE → INTEGRATED (12 days)
**Evidence:** [commit hashes]
```

### 1e. Cross-Reference Sources

```bash
# Improvement log findings with status
grep -E '^### \[|^\- \*\*Status' ~/Projects/meta/improvement-log.md > "$ARTIFACT_DIR/findings-status.txt"

# Hook trigger data
uv run python3 ~/Projects/meta/scripts/hook-roi.py --days $DAYS 2>/dev/null > "$ARTIFACT_DIR/hook-triggers.txt" || echo "hook-roi unavailable"

# Agent failure modes reference
cp ~/Projects/meta/agent-failure-modes.md "$ARTIFACT_DIR/failure-modes-ref.md" 2>/dev/null || true

# Vetoed decisions
cat ~/Projects/meta/.claude/rules/vetoed-decisions.md > "$ARTIFACT_DIR/vetoed.txt" 2>/dev/null || true
```

**Phase 1 output:** `evolution-index.md` (commits + classifications), `session-outcomes.md` (session→outcome joins), `concept-lifecycle.md` (concept states + relationships).

---

## Phase 2: Pattern Extraction + Decay Metrics

Analysis. Instances become classes. Quantitative decay signals surface what's working and what isn't.

### 2a. Failure Pattern Detection

Read the evolution index and cross-reference sources. Look for:

**Fix-of-fix chains** — file/scope fixed then fixed again within days. First fix was incomplete.

**Session-correlated fragility** — sessions from 1c with high correction rates. What do fragile sessions have in common? (scope, time of day, model, project)

**Build-then-retire** — things built and removed within the window. Each is a misjudgment.

**Cross-project contagion** — same failure pattern in 2+ projects. Systemic, not local.

**Concept stalls** — concepts stuck at PROTOTYPE for >7 days. Not progressing, not retired. Dead weight.

### 2b. Rule Compliance Decay

For each rule added to CLAUDE.md or rules/ within the window:

1. Identify the rule and its add-date from git log
2. Check subsequent sessions: does the agent comply?
3. Compute compliance rate at day 1, 7, 14

```markdown
## Rule Decay
| Rule | Added | Day-1 compliance | Day-7 | Day-14 | Half-life estimate | Action |
|------|-------|-----------------|-------|--------|-------------------|--------|
| probe-before-build | 03-15 | 100% | 80% | 40% | ~10d | → PROMOTE to hook |
| no-git-add-A | 03-10 | 100% | 90% | 85% | ~60d | Rule is working |
```

Rules with half-life <14 days need hook promotion. Rules with half-life >30 days are fine as instructions. This directly validates the constitution's "architecture over instructions" principle.

### 2c. Improvement-Log Cycle Time

Parse improvement-log.md to measure self-improvement pipeline velocity:

```markdown
## Self-Improvement Velocity
| Finding | Observed | Proposed | Implemented | Measured | Total cycle | Bottleneck |
|---------|----------|----------|-------------|----------|-------------|-----------|
| dup-read | 03-20 | 03-20 | 03-28 | — | 8d+ (unmeasured) | measurement |
| schema-probe | 03-15 | 03-15 | 03-26 | 03-27 | 12d | implementation |
```

Key metrics:
- **Median cycle time** (finding→implemented): the self-improvement speed
- **Measurement rate**: what % of "implemented" findings have been verified?
- **Stuck findings**: proposed but not implemented for >14 days
- **Zombie findings**: implemented but never measured — the system builds mitigations but doesn't check if they work

### 2d. Reinvention Detection

Check whether the system keeps rebuilding things that already exist:

1. From the concept lifecycle (1d), identify concepts that reached RETIRED or SUPERSEDED
2. Search recent sessions/commits for similar patterns being re-introduced
3. From session transcripts (if accessible): grep for similar function signatures or tool patterns across sessions

```markdown
## Reinvention Events
| What | Original | Reinvented in | Gap | Memory failure? |
|------|----------|--------------|-----|----------------|
| coverage-digest.sh | session X | session Y, Z | 3d | Yes — not shared |
```

High reinvention rate = retrieval/memory system is failing. The fix isn't "build more things" but "make existing things findable."

### 2e. Failure Class Taxonomy

Group patterns into classes:

```markdown
## Failure Class: [NAME]
**Definition:** What goes wrong and why
**Mechanism:** Agent behavior → bad outcome
**Instances:** [date] [project] [commit/finding ref] — [specifics]
**Frequency:** N instances / M days
**Projects:** [list]
**Related concepts:** [concept names from lifecycle, with relationship types]
**Current mitigations:** Hook/Rule/Skill — effectiveness
**Mitigation gap:** What isn't caught
**Blast radius:** low/medium/high
```

Write to `$ARTIFACT_DIR/failure-taxonomy.md`.

Cross-check against `agent-failure-modes.md` (known vs novel) and `vetoed-decisions.md` (don't re-propose).

---

## Phase 3: Causal Analysis + Survival

Why do mitigations fail? How long do artifacts survive? What predicts durability?

### 3a. Mitigation Failure Modes

For each class with mitigation gap > 0:

| Category | Meaning | Example |
|----------|---------|---------|
| **COVERAGE_GAP** | Mitigation exists but misses variants | Hook catches pattern A, not variant B |
| **DECAY** | Rule existed, compliance dropped below threshold | Rule half-life <14d from 2b |
| **NOVEL** | Not recognized as a pattern until now | New failure class |
| **ROUTING_GAP** | Tool exists but isn't reached | Skill not invoked when needed |
| **SEMANTIC** | Requires judgment, not pattern matching | Unhookable |

### 3b. Artifact Survival Analysis

From the revert/retire log and concept lifecycle, compute survival statistics:

```markdown
## Survival by Artifact Type
| Type | N created | N surviving | Median survival (days) | Shortest | Longest |
|------|-----------|-------------|----------------------|----------|---------|
| Hook | 8 | 7 | 30+ | 14 | 30+ |
| Script | 12 | 8 | 18 | 3 | 30+ |
| Rule | 15 | 13 | 25+ | 7 | 30+ |
| Research memo | 20 | 20 | — | — | — |
```

Predictive signal: artifacts created without prior research (no RESEARCH-state concept) should have shorter survival. Artifacts created after /brainstorm or /model-review should survive longer. Verify this.

### 3c. Root Cause Clustering

Cluster failure classes by root cause:

| Root Cause | Classes | Addressable by |
|-----------|---------|---------------|
| Doesn't read docs before probing | schema-probe, CLI-flag-guess | Hook (detect failures before doc reads) |
| Rule decay without hook promotion | repeated-read, polling-loops | Decay curve → auto-promote |
| Memory/retrieval failure | reinvention events | Better concept surfacing |

Write to `$ARTIFACT_DIR/causal-analysis.md`.

---

## Phase 4: Predictions

Ranked proposals for what to build next.

### 4a. Generate Proposals

Rank failure classes by `frequency × blast_radius × (1 - mitigation_coverage)`. For each:

```markdown
## Proposal: [NAME]
**Addresses:** [failure class]
**Type:** hook | skill | rule | architecture | native-feature-adoption
**Mechanism:** How it prevents the failure
**Maintenance:** low/medium/high
**False positive risk:** low/medium/high
**Validation:** How to verify it works
**Rejected alternatives:** What else was considered and why not
```

### 4b. Vetoed + Native Feature Checks

Before finalizing:
1. Re-read `vetoed-decisions.md` — drop any matching proposal
2. Check Claude Code changelog and deferred-features for native coverage:

```bash
grep -i "KEYWORD" ~/Projects/meta/research/claude-code-native-features-deferred.md 2>/dev/null | head -5
```

### 4c. Final Output

Write to `$ARTIFACT_DIR/predictions.md`:

```markdown
# Evolution Forensics — YYYY-MM-DD (N days, M projects)

## System Health
- Self-improvement cycle time: Nd median
- Measurement rate: N% of implemented findings verified
- Rule decay: N rules below half-life threshold
- Reinvention rate: N events (memory failure indicator)
- Artifact survival: scripts Nd median, hooks Nd median

## Priority Actions
1. [Proposal] — [rationale]

## Deferred
- [Proposal] — [why]

## Already Mitigated
- [Class] — [by what]

## Concept Lifecycle Summary
| Concept | State | Trajectory | Days in state |
```

---

## Output Files

| File | Phase | Contains |
|------|-------|----------|
| `evolution-index.md` | 1b | Classified commits |
| `session-outcomes.md` | 1c | Session→commit→correction chains |
| `concept-lifecycle.md` | 1d | Concept states + typed relationships |
| `failure-taxonomy.md` | 2e | Failure classes with evidence |
| `causal-analysis.md` | 3c | Root causes + survival stats |
| `predictions.md` | 4c | Ranked proposals + system health metrics |

## Anti-Patterns

- **Don't maintain a manual concept registry.** Infer concepts from git history and improvement-log. If it needs manual upkeep, it'll rot.
- **Don't re-propose vetoed decisions.**
- **Don't count dev effort as cost.** Filter by maintenance burden.
- **Don't fabricate instances.** Every failure class cites a commit hash or improvement-log entry.
- **Don't conflate frequency with severity.** Rare catastrophic > frequent trivial.
- **Don't skip Phase 1.** The index IS the skill. Analysis without evidence is speculation.
- **Don't treat reinvention as failure to build.** It's failure to retrieve. The fix is surfacing, not building more.
