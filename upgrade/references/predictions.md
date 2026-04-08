<!-- Reference file for evolution-forensics skill. Loaded on demand. -->

# Predictions & Proposals (Phase 4)

## 4a. Generate Proposals

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

## 4b. Vetoed + Native Feature Checks

Before finalizing:
1. Re-read `vetoed-decisions.md` — drop any matching proposal
2. Check Claude Code changelog and deferred-features for native coverage:

```bash
grep -i "KEYWORD" ~/Projects/meta/research/claude-code-native-features-deferred.md 2>/dev/null | head -5
```

## 4c. Final Output Format

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

## Output Files

| File | Phase | Contains |
|------|-------|----------|
| `evolution-index.md` | 1b | Classified commits |
| `session-outcomes.md` | 1c | Session→commit→correction chains |
| `concept-lifecycle.md` | 1d | Concept states + typed relationships |
| `failure-taxonomy.md` | 2e | Failure classes with evidence |
| `causal-analysis.md` | 3c | Root causes + survival stats |
| `predictions.md` | 4c | Ranked proposals + system health metrics |
