<!-- Reference file for brainstorm skill. Loaded on demand. -->
# Synthesis & Extraction Templates

## Disposition Table (Step 4)

After extracting all ideas, build this table. Every extracted item must have a disposition.

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

For EXPLORE items, note which technique generated it (initial/denial/domain/constraint/knowledge-injection) to track which methods produce the most useful ideas across sessions.

## Synthesis Output (Step 5)

Save to `$BRAINSTORM_DIR/synthesis.md`:

```markdown
## Brainstorm: [topic]
**Date:** YYYY-MM-DD
**Perturbation:** Denial xN, Domain forcing xN, Constraint inversion xN
**Human seeds:** [yes/no]
**Extraction:** N items total → E explore, P parked, R rejected

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
LLMX_AVAILABLE=$(which llmx 2>/dev/null && echo "yes" || echo "no")
TOPIC_SLUG=$(echo "$TOPIC" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//;s/-$//' | cut -c1-40)
BRAINSTORM_ID=$(openssl rand -hex 3)
BRAINSTORM_DIR=".brainstorm/$(date +%Y-%m-%d)-${TOPIC_SLUG}-${BRAINSTORM_ID}"
mkdir -p "$BRAINSTORM_DIR"
```
