<!-- Reference file for evolution-forensics skill. Loaded on demand. -->

# Causal Analysis & Survival (Phase 3)

## 3a. Mitigation Failure Modes

For each class with mitigation gap > 0:

| Category | Meaning | Example |
|----------|---------|---------|
| **COVERAGE_GAP** | Mitigation exists but misses variants | Hook catches pattern A, not variant B |
| **DECAY** | Rule existed, compliance dropped below threshold | Rule half-life <14d from 2b |
| **NOVEL** | Not recognized as a pattern until now | New failure class |
| **ROUTING_GAP** | Tool exists but isn't reached | Skill not invoked when needed |
| **SEMANTIC** | Requires judgment, not pattern matching | Unhookable |

## 3b. Artifact Survival Analysis

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

## 3c. Root Cause Clustering

Cluster failure classes by root cause:

| Root Cause | Classes | Addressable by |
|-----------|---------|---------------|
| Doesn't read docs before probing | schema-probe, CLI-flag-guess | Hook (detect failures before doc reads) |
| Rule decay without hook promotion | repeated-read, polling-loops | Decay curve → auto-promote |
| Memory/retrieval failure | reinvention events | Better concept surfacing |

Write to `$ARTIFACT_DIR/causal-analysis.md`.
