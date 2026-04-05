#!/bin/bash
# PostToolUse hook (Write|Edit) — advise model-review on substantial new plan files
# Advisory only (exit 0). Only fires on plans large enough to warrant cross-model review.

INPUT=$(cat)
FPATH=$(echo "$INPUT" | grep -oE '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"$//')

# Only trigger on .claude/plans/ files
echo "$FPATH" | grep -q '\.claude/plans/' || exit 0

# Must be a real file
[ -f "$FPATH" ] || exit 0

# Skip small plans (<30 lines) — not worth reviewing
LINES=$(wc -l < "$FPATH" 2>/dev/null)
[ "$LINES" -lt 30 ] && exit 0

# Skip if plan mentions "v2" or "revised" — it's an update, not new
head -5 "$FPATH" | grep -qi 'v[2-9]\|revised\|review findings' && exit 0

# Skip if already reviewed today
PLAN_SLUG=$(basename "$FPATH" .md)
TODAY=$(date +%Y-%m-%d)
if ls .model-review/${TODAY}-*${PLAN_SLUG}* 2>/dev/null | grep -q .; then
  exit 0
fi

echo "Substantial plan written (${LINES} lines). Consider /model-review before executing — then check: do the models' findings hold given your project context? Revise cosigned/deferred/rejected as needed."
