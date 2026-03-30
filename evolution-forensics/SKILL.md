---
name: evolution-forensics
description: "Longitudinal codebase forensics — scans N days of git history across projects, builds an evolution index (commit patterns, churn hotspots, fix chains), cross-references with improvement-log and hook telemetry, extracts failure classes, and predicts tooling to prevent recurrence. The time-series complement to session-analyst (snapshot) and design-review (architecture)."
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

Longitudinal analysis of how the codebase *actually evolves* — not what one session did, but what patterns emerge across days and weeks of commits, corrections, and failures.

**session-analyst** sees one session. **design-review** sees workflow patterns. **This skill** sees the *time series* — which fixes stuck, which regressed, which failure classes resist mitigation, and what tooling would bend the curve.

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

Build a structured index of what happened. This is the prep step — data collection, no analysis.

### 1a. Git History Extraction

For each project in scope, extract structured commit data:

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
    --format="COMMIT|%H|%ai|%an|%s" \
    --numstat \
    >> "$ARTIFACT_DIR/git-history.md"
  echo "" >> "$ARTIFACT_DIR/git-history.md"
done
```

### 1b. Commit Classification

Read the raw git history and classify each commit into one of:

| Type | Signal | Example |
|------|--------|---------|
| **FIX** | Subject contains: fix, repair, correct, patch, resolve, handle | `[hooks] Fix trap swallowing exit 2` |
| **FIX-OF-FIX** | Fixes something touched by a FIX commit within 3 days | Commit fixes the same file a prior fix touched |
| **REVERT** | Subject contains: revert, undo, drop, remove, retire | `[infra] Drop finding-triage DB` |
| **FEATURE** | New capability, wiring, integration | `[api] Wire rate-limit refresh` |
| **RULE** | CLAUDE.md, rules/, hooks, improvement-log changes | `[rules] Extend probe-before-build` |
| **RESEARCH** | research/, decisions/ changes | `[research] Agent scaffolding landscape` |
| **CHORE** | Docs, formatting, deps, CI | `[docs] Regenerate codebase map` |

For each commit, extract:
- **scope** (from `[scope]` prefix)
- **type** (from classification above)
- **files_changed** (from numstat)
- **churn** (lines added + deleted)
- **trailers** (Evidence:, Rejected:, Session-ID:, etc.)

Write structured output to `$ARTIFACT_DIR/evolution-index.md`:

```markdown
# Evolution Index — YYYY-MM-DD (N days)

## Summary
- Total commits: N across M projects
- Types: N fix, N fix-of-fix, N revert, N feature, N rule, N research, N chore
- Hotspot files: (top 10 by commit count)
- Fix-of-fix chains: N (list)

## Per-Project

### [project]
| Date | Scope | Type | Subject | Files | Churn |
|------|-------|------|---------|-------|-------|
| ... | ... | ... | ... | ... | ... |

## Churn Hotspots
Files touched by 5+ commits in the window, ranked by churn:
| File | Commits | Lines changed | Types |
|------|---------|--------------|-------|

## Fix Chains
Sequences where a file was fixed, then fixed again within 3 days:
| File | Fix 1 | Fix 2 | Gap (days) | Same scope? |
|------|-------|-------|-----------|-------------|

## Revert/Retire Log
Things that were built then removed:
| What | Built | Removed | Lifespan | Why removed (from commit body) |
|------|-------|---------|----------|-------------------------------|
```

### 1c. Cross-Reference Sources

Enrich the index with data from other systems:

```bash
# Improvement log — extract findings with status
grep -E '^### \[|^\- \*\*Status' ~/Projects/meta/improvement-log.md > "$ARTIFACT_DIR/findings-status.txt"

# Hook trigger data (if available)
uv run python3 ~/Projects/meta/scripts/hook-roi.py --days $DAYS 2>/dev/null > "$ARTIFACT_DIR/hook-triggers.txt" || echo "hook-roi unavailable"

# Agent failure modes reference
cp ~/Projects/meta/agent-failure-modes.md "$ARTIFACT_DIR/failure-modes-ref.md" 2>/dev/null || true

# Session shape anomalies (zero-cost structural flags)
uv run python3 ~/Projects/meta/scripts/session-shape.py --days $DAYS 2>/dev/null > "$ARTIFACT_DIR/session-shapes.txt" || echo "session-shape unavailable"

# Vetoed decisions (things NOT to re-propose)
cat ~/Projects/meta/.claude/rules/vetoed-decisions.md > "$ARTIFACT_DIR/vetoed.txt" 2>/dev/null || true
```

**Output:** `$ARTIFACT_DIR/evolution-index.md` — the full structured index. Verify it exists and is >1KB before proceeding.

---

## Phase 2: Failure Pattern Extraction

Now analyze the index for recurring failure patterns. This is where instances become classes.

### 2a. Pattern Detection

Read the evolution index and cross-reference sources. Look for these specific pattern types:

**Fix-of-fix chains** — A file or scope that gets fixed, then fixed again within days. This means the first fix was incomplete or introduced a new bug. Each chain is a potential failure class.

**Churn-without-convergence** — Files with high churn (many commits) but no net improvement (same issues reappear). The system is thrashing, not learning.

**Rule-then-violation** — A rule was added (CLAUDE.md, rules/, hook) but subsequent sessions still violate it. The rule isn't working. Cross-reference: improvement-log entries marked "implemented" but with later recurrence entries.

**Build-then-retire** — Features or infrastructure built and then removed within the window. The revert/retire log from Phase 1 feeds this. Each instance is a misjudgment — either premature building or bad requirements.

**Hook blindspot** — Failure modes documented in `agent-failure-modes.md` that have NO corresponding hook, rule, or skill. The gap between what's known and what's enforced.

**Cross-project contagion** — Same failure pattern appearing in 2+ projects. Indicates a systemic issue, not a project-specific one.

### 2b. Class Taxonomy

Group individual patterns into failure *classes*. A class is defined by:

```markdown
## Failure Class: [NAME]

**Definition:** One sentence — what goes wrong and why
**Mechanism:** How the failure propagates (agent behavior → bad outcome)
**Instances in window:**
- [date] [project] [commit/finding ref] — [specific instance]
- ...
**Frequency:** N instances / M days = rate
**Projects affected:** [list]
**Current mitigations:**
- Hook: [name] — [effectiveness: blocks N%, misses N%]
- Rule: [CLAUDE.md section] — [compliance: observed in N/M sessions]
- Skill: [name] — [coverage: addresses N% of instances]
**Mitigation gap:** What the current mitigations DON'T catch
**Blast radius:** [low/medium/high] — what happens when this failure occurs unmitigated
```

Write taxonomy to `$ARTIFACT_DIR/failure-taxonomy.md`.

### 2c. Verify Against Known Patterns

Cross-check your taxonomy against `agent-failure-modes.md`:
- Are any of your classes already documented there? → Note as "KNOWN, mitigation status: X"
- Are any documented modes NOT appearing in recent history? → Note as "DORMANT or MITIGATED"
- Are any of your classes genuinely NEW? → Flag for Phase 4

Cross-check against vetoed decisions:
- Would any recommendation you're forming re-propose a vetoed approach? → Drop it now.

---

## Phase 3: Causal Analysis

For each failure class, determine *why* existing mitigations aren't sufficient.

### 3a. Mitigation Failure Modes

For each class with mitigation gap > 0:

| Class | Mitigation exists? | Why it fails | Category |
|-------|-------------------|-------------|----------|
| ... | Hook X | Too narrow — catches pattern A but not variant B | COVERAGE_GAP |
| ... | Rule Y | Instruction-only, no enforcement — compliance ~60% | UNHOOKABLE |
| ... | None | Not recognized as a pattern until now | NOVEL |
| ... | Skill Z | Skill exists but isn't invoked when needed | ROUTING_GAP |

Categories:
- **COVERAGE_GAP** — Mitigation exists but doesn't cover all variants
- **UNHOOKABLE** — Rule exists but can't be enforced deterministically
- **NOVEL** — Pattern wasn't recognized before this analysis
- **ROUTING_GAP** — Tool exists but isn't reached (wrong trigger, not in workflow)
- **SEMANTIC** — Failure requires judgment to detect, not pattern matching

### 3b. Root Cause Clustering

Cluster failure classes by root cause:

| Root Cause | Classes | Addressable by |
|-----------|---------|---------------|
| Agent doesn't read available docs before probing | schema-probe-loop, CLI-flag-guessing | Hook (detect repeated failures before doc reads) |
| Same-model review is a martingale | missed-bugs-in-review, sycophantic-compliance | Cross-model (architectural) |
| Async coordination is manual | file-poll-loops, background-task-waste | Better async primitives |
| ... | ... | ... |

Write to `$ARTIFACT_DIR/causal-analysis.md`.

---

## Phase 4: Tooling Predictions

The payoff. For each unmitigated or under-mitigated failure class, propose concrete tooling.

### 4a. Generate Proposals

For each failure class ranked by `frequency x blast_radius x (1 - mitigation_coverage)`:

```markdown
## Proposal: [NAME]

**Addresses class:** [failure class name]
**Type:** hook | skill | rule | architecture | native-feature-adoption
**Mechanism:** [How it prevents the failure — be specific]
**Implementation sketch:** [10-20 lines of what the hook/skill/rule would look like]
**Maintenance burden:** [low/medium/high] — what breaks when the codebase evolves?
**False positive risk:** [low/medium/high] — how often would this fire incorrectly?
**Validation:** [How to verify it works — specific test or metric]
**Rejected alternatives:**
- [Alternative 1] — why not: [reason]
- [Alternative 2] — why not: [reason]
```

### 4b. Priority Matrix

Rank proposals by actionability:

| Proposal | Frequency | Blast radius | Maintenance | False positives | Score |
|----------|-----------|-------------|-------------|----------------|-------|
| ... | ... | ... | ... | ... | ... |

Score = `frequency * blast_radius_weight / (maintenance + false_positive_risk)` where blast_radius_weight is 1/2/3 for low/medium/high.

### 4c. Vetoed Check

Before finalizing: re-read `vetoed-decisions.md`. Drop any proposal that matches a vetoed approach. Note: "Dropped proposal X — matches veto: [entry]".

### 4d. Native Feature Check

For each proposal of type "hook" or "skill": check if Claude Code, the SDK, or a vendor tool already provides this natively. Run:

```bash
# Check Claude Code changelog for relevant features
grep -i "KEYWORD" ~/Projects/meta/research/anthropic-claude-weekly-*.md 2>/dev/null | head -5
grep -i "KEYWORD" ~/Projects/meta/research/claude-code-native-features-deferred.md 2>/dev/null | head -5
```

If a native feature covers 80%+ of the proposal, recommend adoption over building.

### 4e. Final Output

Write to `$ARTIFACT_DIR/predictions.md`:

```markdown
# Evolution Forensics — Tooling Predictions
**Date:** YYYY-MM-DD
**Window:** N days across M projects
**Commits analyzed:** N
**Failure classes found:** N (M novel, K known, J dormant)

## Priority Actions
1. [Proposal] — [one-line rationale]
2. ...

## Deferred (low priority or blocked)
- [Proposal] — deferred because: [reason]

## Already Mitigated (no action)
- [Class] — covered by: [mitigation]
```

---

## Output Convention

All artifacts go to `~/Projects/meta/artifacts/evolution-forensics/`. The key outputs:

| File | Phase | Contains |
|------|-------|----------|
| `git-history.md` | 1a | Raw git log data |
| `evolution-index.md` | 1b | Structured commit index with classifications |
| `failure-taxonomy.md` | 2b | Failure classes with instances and mitigations |
| `causal-analysis.md` | 3b | Root cause clusters and mitigation failure modes |
| `predictions.md` | 4e | Ranked tooling proposals |

The evolution-index is the prep artifact. The predictions file is the actionable output.

## Anti-Patterns

- **Don't re-propose vetoed decisions.** Check `vetoed-decisions.md` before every recommendation.
- **Don't count dev effort as cost.** Filter by maintenance burden, not implementation effort.
- **Don't fabricate instances.** Every failure class entry must cite a specific commit hash or improvement-log entry.
- **Don't propose without checking native features.** Step 4d exists for a reason.
- **Don't conflate frequency with severity.** A rare catastrophic failure outranks a frequent trivial one.
- **Don't skip Phase 1.** The index IS the skill. Analysis without evidence is speculation.
