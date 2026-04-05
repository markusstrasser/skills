#!/bin/bash
# PostToolUse hook (Write|Edit) — advise model-review after new plan files
# Advisory only (exit 0). Fires when a plan file is created or substantially edited.

INPUT=$(cat)
FPATH=$(echo "$INPUT" | grep -oE '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"$//')

# Only trigger on .claude/plans/ files
echo "$FPATH" | grep -q '\.claude/plans/' || exit 0

# Skip if this is a minor edit (model-review applying its own fixes)
# Heuristic: if the commit message mentions "model-review" or "review findings", skip
RECENT_MSG=$(git log --oneline -1 -- "$FPATH" 2>/dev/null)
echo "$RECENT_MSG" | grep -qi 'review\|model-review\|revision\|v[0-9]' && exit 0

# Check if a model-review already exists for this plan (same day)
PLAN_SLUG=$(basename "$FPATH" .md)
TODAY=$(date +%Y-%m-%d)
if ls .model-review/${TODAY}-*${PLAN_SLUG}* 2>/dev/null | grep -q .; then
  exit 0  # already reviewed today
fi

echo "Plan file written: $(basename "$FPATH"). Run /model-review before executing — cross-model review is required for non-trivial plans (Constitution §12)."
