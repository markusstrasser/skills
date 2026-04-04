<!-- Reference file for design-review skill. Loaded on demand. -->

# Output Templates

## Proposal Template (Phase 4)

For each surviving proposal:

```markdown
### [TYPE] Proposal Name

**Pattern:** What was observed [sessions: list]
**Frequency:** N occurrences across M sessions, K projects
**Current cost:** Estimated minutes/week of human or agent time
**Approach considered:**
1. [Selected approach] — why selected
2. [Alternative A] — why not (preserve for reference)
3. [Alternative B] — why not
**Proposal:** What to build (hook? skill? pipeline? MCP tool? script? justfile command?)
**Implementation sketch:**
```pseudocode
# 5-15 lines showing the core mechanism
```
**Blast radius:** Which projects/workflows affected
**Reversibility:** easy (hook/script) | medium (skill/pipeline) | hard (architectural)
**Status:** NEW | KNOWN:location
**Priority:** (weekly_minutes_saved × project_count) / implementation_hours
**Wild card?:** [yes/no — at least one proposal must challenge a current assumption]
```

Sort by priority descending.

## Report Header (Phase 5)

Write to `YYYY-MM-DD.md` in `$ARTIFACT_DIR`.

```bash
ARTIFACT_DIR="$HOME/Projects/meta/artifacts/design-review"
mkdir -p "$ARTIFACT_DIR"
```

Include this header:

```markdown
# Design Review — YYYY-MM-DD
**Sessions analyzed:** N across K projects (DAYS days)
**Patterns extracted:** N (Gemini), M verified
**Proposals:** N (P new, Q known)
**Top proposal:** [name] — estimated [X] min/week saved
**Wild card:** [name]
```
