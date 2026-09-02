<!-- Reference file for evolution-forensics skill. Loaded on demand. -->

# Failure Class Taxonomy (Phase 2e)

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
