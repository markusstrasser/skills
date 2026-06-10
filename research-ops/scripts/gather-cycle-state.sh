#!/usr/bin/env bash
# Gather project state for research cycle tick. Target: <5s.
# Called via !` in SKILL.md — output replaces the placeholder before Claude sees it.
# Requires: PROJECT_ROOT env var or first argument.
set -euo pipefail
# Allow non-critical failures in data gathering
set +e

PROJECT_ROOT="${1:-${PROJECT_ROOT:-$(pwd)}}"
PROJECT_NAME=$(basename "$PROJECT_ROOT")
CYCLE_FILE="$PROJECT_ROOT/CYCLE.md"
QUEUE_DIR="$PROJECT_ROOT/queue"
DECISIONS_DIR="$PROJECT_ROOT/decisions-pending"
HASH_FILE=~/.claude/research-cycle-state-hash-${PROJECT_NAME}.txt

# --- Noop detection ---
GIT_HASH=$(cd "$PROJECT_ROOT" && git log --oneline -1 2>/dev/null || echo "na")
CYCLE_HASH=$(test -f "$CYCLE_FILE" && md5 < "$CYCLE_FILE" 2>/dev/null || echo "na")
QUEUE_HASH=$(ls "$QUEUE_DIR" "$DECISIONS_DIR" 2>/dev/null | md5 2>/dev/null || echo "na")
CURRENT_HASH="${GIT_HASH}|${CYCLE_HASH}|${QUEUE_HASH}"

PREV_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
echo "$CURRENT_HASH" > "$HASH_FILE"

if [[ "$CURRENT_HASH" = "$PREV_HASH" ]]; then
    echo "NO STATE CHANGE since last tick."
    exit 0
fi

# --- Project identity ---
echo "=== PROJECT: $PROJECT_NAME ==="
echo "Root: $PROJECT_ROOT"

# --- Bus state (queue + decisions-pending) ---
echo ""
echo "=== BUS STATE ==="
if [[ -d "$QUEUE_DIR" ]]; then
    UNUSED=$(ls "$QUEUE_DIR"/QUEUE_*.md 2>/dev/null | grep -cv '\.consumed\.' || echo "0")
    CONSUMED=$(ls "$QUEUE_DIR"/*.consumed.md 2>/dev/null | wc -l | tr -d ' ')
    echo "queue/: $UNUSED unused proposals, $CONSUMED consumed"
    ls "$QUEUE_DIR"/QUEUE_*.md 2>/dev/null | grep -v '\.consumed\.' | head -5 | while read -r f; do
        echo "  - $(basename "$f"): $(head -1 "$f" 2>/dev/null | sed 's/^#* *//' | cut -c1-60)"
    done
else
    echo "queue/: (none — Dreamer has not run, or first run)"
fi
if [[ -d "$DECISIONS_DIR" ]]; then
    DPEND=$(ls "$DECISIONS_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "decisions-pending/: $DPEND awaiting human greenlight"
else
    echo "decisions-pending/: (none)"
fi

# --- Recent git activity ---
echo ""
echo "=== GIT (last 6h) ==="
cd "$PROJECT_ROOT"
git log --oneline --since="6 hours ago" 2>/dev/null | head -10 || echo "(no recent commits)"

# --- Research docs state ---
echo ""
echo "=== RESEARCH INDEX ==="
if [[ -d "$PROJECT_ROOT/docs/research" ]]; then
    ACTIVE=$(grep -l 'ACTIVE' "$PROJECT_ROOT/docs/research/"*.md 2>/dev/null | wc -l | tr -d ' ')
    TOTAL=$(ls "$PROJECT_ROOT/docs/research/"*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "$ACTIVE active / $TOTAL total research memos"
elif [[ -d "$PROJECT_ROOT/research" ]]; then
    TOTAL=$(ls "$PROJECT_ROOT/research/"*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "$TOTAL research memos"
else
    echo "(no research directory)"
fi

# --- Steward proposals pending for this project ---
echo ""
echo "=== PENDING PROPOSALS ==="
for f in ~/.claude/steward-proposals/*.md; do
    [[ -f "$f" ]] || continue
    if grep -qi "$PROJECT_NAME" "$f" 2>/dev/null && ! grep -q "IMPLEMENTED" "$f" 2>/dev/null; then
        echo "  $(basename "$f"): $(head -1 "$f" | sed 's/^# //')"
    fi
done
[[ -z "$(ls ~/.claude/steward-proposals/*.md 2>/dev/null)" ]] && echo "(none)"

# --- Improvement signals (for signal-driven gap selection) ---
echo ""
echo "=== IMPROVEMENT SIGNALS (top 5) ==="
PROPOSE_WORK=~/Projects/agent-infra/scripts/propose-work.py
if [[ -f "$PROPOSE_WORK" ]]; then
    uv run python3 "$PROPOSE_WORK" --json --project "$PROJECT_NAME" 2>/dev/null | \
        python3 -c "
import json,sys
try:
    signals = json.load(sys.stdin)
    for s in signals[:5]:
        tag = 'STEER' if s.get('steering_impact') else s.get('category','?')[:5].upper()
        print(f\"  [{tag}] {s.get('severity','?')}: {s.get('description','?')[:80]}\")
    if len(signals) > 5:
        print(f'  ... and {len(signals)-5} more')
except: print('  (no signals)')
" 2>/dev/null || echo "  (propose-work.py unavailable)"
else
    echo "  (propose-work.py not found)"
fi

exit 0
