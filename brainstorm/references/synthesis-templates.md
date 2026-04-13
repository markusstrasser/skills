<!-- Reference file for brainstorm skill. Loaded on demand. -->
# Synthesis & Extraction Templates

## Coverage Matrix (Step 3.5)

Use this after perturbation and before extraction/synthesis. `matrix.json` is the coverage
contract. `matrix.md` is a rendered operator view over the same rows.

### `matrix.json` row example

```json
[
  {
    "idea_id": "D1",
    "short_name": "event-sourced memory",
    "source_artifact": "denial-r1.md",
    "axis": "denial",
    "domain_row": null,
    "domain": null,
    "dominant_paradigm_escaped": "append-only log",
    "transfer_mechanism": "replace ad hoc writes with replayable state deltas",
    "cell_status": "covered",
    "disposition": "EXPLORE",
    "merged_into": null,
    "caller_evidence": null,
    "speculative": false,
    "notes": "Strong denial survivor"
  }
]
```

### `matrix.md` rendered view

```markdown
## Coverage Matrix
| Idea | Source / Round | Dominant Paradigm Escaped | Axis | Domain Row | Cell Status | Disposition | Notes |
|------|----------------|---------------------------|------|------------|-------------|-------------|-------|
| I1   | Initial        | append-only log           | initial | -        | Covered     | PARK        | Baseline basin |
| D1   | Denial R1      | append-only log           | denial  | -        | Covered     | EXPLORE     | Explicitly banned |
| F3   | Domain         | queue semantics           | domain  | Natural systems | Partial | PARK | Analogy only |
| C2   | Constraint     | offline-first             | constraint | -     | Missed      | REJECT      | No useful transfer |
```

Cell statuses: `Covered`, `Partial`, `Missed`, `Duplicate`, `Questionable`.

## Coverage Summary (`coverage.json`)

Record the matrix summary structurally before prose:

```json
{
  "requested_axes": ["denial", "domain", "constraint"],
  "executed_axes": ["denial", "domain"],
  "idea_count_by_axis": {"initial": 12, "denial": 8, "domain": 6},
  "distinct_paradigms_escaped": 5,
  "domain_row_coverage": {
    "Natural systems": 1,
    "Human institutions": 1,
    "Engineering": 0
  },
  "duplicate_count": 3,
  "merge_count": 2,
  "uncovered_cells": ["constraint:offline-first", "engineering:domain"],
  "mature_frontier_stop_reason": "forced-domain rounds collapsed into reframings"
}
```

If the summary cannot explain why synthesis is safe, run another perturbation pass or stop.

## Disposition Table (Step 4)

After extracting all ideas, build this table. Every extracted item must have a disposition.
The table should render from `matrix.json`, not diverge from it.

```markdown
## Disposition Table
| ID  | Idea (short) | Source | Disposition | Reason |
|-----|-------------|--------|-------------|--------|
| I3  | Event-sourced memory | Initial | EXPLORE | Novel, low maintenance |
| D1  | Append-only log | Denial R1 | MERGE w/ I3 | Same paradigm |
| D5  | No memory at all | Denial R2 | EXPLORE | Radical simplification |
| F2  | Immune system model | Domain | PARK | Interesting, no path yet |
| C1  | Offline-first design | Constraint | EXPLORE | Transfers well |
```

Dispositions: `EXPLORE` (pursue), `PARK` (not now), `REJECT` (bad fit), `MERGE WITH [ID]` (dedup).
After pain-point gating, add `caller_evidence` and `speculative` to the underlying row.

For EXPLORE items, note which technique generated it (initial/denial/domain/constraint/knowledge-injection) to track which methods produce the most useful ideas across sessions.

## Synthesis Output (Step 5)

Save to `$BRAINSTORM_DIR/synthesis.md`:

```markdown
## Brainstorm: [topic]
**Date:** YYYY-MM-DD
**Perturbation:** Denial xN, Domain forcing xN, Constraint inversion xN
**Human seeds:** [yes/no]
**Extraction:** N items total → E explore, P parked, R rejected, M merged
**Coverage:** axes [list], paradigms escaped N, uncovered cells [count]

### Ideas to Explore (ranked by novelty x feasibility)
| Rank | ID(s) | Idea | Why Non-Obvious | Maintenance | Composability |
|------|-------|------|----------------|--------|------|

### Parked
| ID | Idea | Why Parked |

### Rejected
| ID | Idea | Why Rejected |

### Paradigm Gaps
What design space was NOT covered? What domains or constraints went unexplored?

### Suggested Next Step
Which 1-2 ideas to prototype first? Cheapest validation?
```

## Pre-Flight Scripts

### Dedup Check

```bash
RECENT=$(find .brainstorm/ -name "synthesis.md" -mtime -1 2>/dev/null)
if [ -n "$RECENT" ]; then
  echo "Recent brainstorm(s) found:"
  for f in $RECENT; do echo "  $f"; head -5 "$f"; echo "---"; done
fi
```

Also check git for cross-session brainstorms:

```bash
git log --oneline -10 --all | grep -i "brainstorm"
```

### Constitutional Check

```bash
CONSTITUTION=$(find . -maxdepth 3 -name "CONSTITUTION.md" 2>/dev/null | head -1)
if [ -z "$CONSTITUTION" ]; then
  CLAUDE_MD=$(find . -maxdepth 1 -name "CLAUDE.md" | head -1)
  if [ -n "$CLAUDE_MD" ] && grep -q "^## Constitution" "$CLAUDE_MD"; then
    CONSTITUTION="$CLAUDE_MD"
  fi
fi
GOALS=$(find . -maxdepth 3 -name "GOALS.md" 2>/dev/null | head -1)
```

### Output Setup

```bash
EXTERNAL_DISPATCH_AVAILABLE=$(test -f ~/Projects/skills/scripts/llm-dispatch.py && echo "yes" || echo "no")
TOPIC_SLUG=$(echo "$TOPIC" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//;s/-$//' | cut -c1-40)
BRAINSTORM_ID=$(openssl rand -hex 3)
BRAINSTORM_DIR=".brainstorm/$(date +%Y-%m-%d)-${TOPIC_SLUG}-${BRAINSTORM_ID}"
mkdir -p "$BRAINSTORM_DIR"
```
