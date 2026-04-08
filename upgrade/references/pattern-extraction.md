<!-- Reference file for evolution-forensics skill. Loaded on demand. -->

# Pattern Extraction & Decay Metrics (Phase 2a-2d)

## 2a. Failure Pattern Detection

Read the evolution index and cross-reference sources. Look for:

**Fix-of-fix chains** — file/scope fixed then fixed again within days. First fix was incomplete.

**Session-correlated fragility** — sessions from Phase 1c with high correction rates. What do fragile sessions have in common? (scope, time of day, model, project)

**Build-then-retire** — things built and removed within the window. Each is a misjudgment.

**Cross-project contagion** — same failure pattern in 2+ projects. Systemic, not local.

**Concept stalls** — concepts stuck at PROTOTYPE for >7 days. Not progressing, not retired. Dead weight.

## 2b. Rule Compliance Decay

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

## 2c. Improvement-Log Cycle Time

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

## 2d. Reinvention Detection

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
