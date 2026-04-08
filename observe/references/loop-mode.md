<!-- Reference file for observe skill (architecture mode). Loaded on demand. -->

# Loop Mode & Accrual-Synthesis Pipeline

## Loop Mode Output

When invoked via `/loop`, use quick mode. Output patterns as JSONL (one per line) to the rolling patterns file:

```bash
PATTERNS_FILE="$HOME/Projects/meta/artifacts/observe/patterns.jsonl"
mkdir -p "$(dirname "$PATTERNS_FILE")"
```

For each pattern found, append one JSON line:
```json
{"ts": "2026-03-17T14:00:00Z", "type": "WORKFLOW_REPEAT", "name": "research-verify-commit", "frequency": 4, "sessions": ["abc123", "def456"], "projects": ["intel", "meta"], "evidence": "user typed 'now verify those claims'...", "verified": true}
```

After writing patterns, check timestamp of last synthesis:
```bash
SYNTH_FILE="$HOME/Projects/meta/artifacts/observe/last-synthesis.md"
```
If `last-synthesis.md` is >24h old or doesn't exist, AND there are 5+ new patterns since last synthesis, trigger a full synthesis (Phases 3-5) and write to `artifacts/observe/YYYY-MM-DD-synthesis.md`. The synthesis reads ALL patterns from the last 7 days, deduplicates by name, counts recurrences, and produces ranked proposals.

The synthesis file is picked up by `propose-work.py` in the morning brief -- proposals with 3+ recurrences surface as work items.

**Delta detection:** Check `artifacts/observe/last-synthesis.md` mtime for timestamp of last run. Only analyze sessions modified after that timestamp.

## Accrual -> Synthesis -> Execute Loop

```
Quick runs (every 4h)
  -> patterns.jsonl (append-only, rolling)
     -> Daily synthesis (auto-triggered when 5+ new patterns + >24h since last)
        -> YYYY-MM-DD-synthesis.md (ranked proposals)
           -> propose-work.py morning brief (surfaces top proposals)
              -> Human approves -> orchestrator task or interactive session
```

**Recurrence is the quality signal.** A pattern seen once is noise. Seen 3 times across 2 projects = proposal. Seen 5+ times = urgent. The patterns.jsonl file is the institutional memory of what the system wants to become.

## Pruning

Patterns older than 30 days are archived to `patterns-archive.jsonl`. Implemented proposals are marked `"status": "implemented"`.

## Implementation Tracking

After writing patterns, check implementation status:
```bash
for pattern in $(cat artifacts/observe/patterns.jsonl | python3 -c "import sys,json; [print(json.loads(l).get('name','')) for l in sys.stdin]"); do
  if git log --oneline --since="30 days ago" --grep="$pattern" | head -1 | grep -q .; then
    echo "IMPLEMENTED: $pattern"
  fi
done
```
Mark implemented patterns in patterns.jsonl with `"status": "implemented"`.
