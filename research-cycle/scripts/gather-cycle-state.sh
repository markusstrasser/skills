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
HASH_FILE=~/.claude/research-cycle-state-hash-${PROJECT_NAME}.txt
ORCH_DB=~/.claude/orchestrator.db

# --- Noop detection ---
GIT_HASH=$(cd "$PROJECT_ROOT" && git log --oneline -1 2>/dev/null || echo "na")
CYCLE_HASH=$(test -f "$CYCLE_FILE" && md5 < "$CYCLE_FILE" 2>/dev/null || echo "na")
ORCH_HASH=$(sqlite3 "$ORCH_DB" "SELECT count(*),group_concat(status) FROM tasks WHERE project='$PROJECT_NAME' AND status IN ('pending','running','failed','blocked') ORDER BY id" 2>/dev/null || echo "na")
CURRENT_HASH="${GIT_HASH}|${CYCLE_HASH}|${ORCH_HASH}"

PREV_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
echo "$CURRENT_HASH" > "$HASH_FILE"

if [[ "$CURRENT_HASH" = "$PREV_HASH" ]]; then
    echo "NO STATE CHANGE since last tick."
    exit 0
fi

# --- Project identity ---
echo "=== PROJECT: $PROJECT_NAME ==="
echo "Root: $PROJECT_ROOT"

# --- Cycle file state ---
echo ""
echo "=== CYCLE STATE ==="
if [[ -f "$CYCLE_FILE" ]]; then
    # Extract current phase and queue counts
    PHASE=$(grep -m1 '^## Phase:' "$CYCLE_FILE" 2>/dev/null | sed 's/## Phase: //' || echo "unknown")
    QUEUE_PENDING=$(grep -c '^\- \[ \]' "$CYCLE_FILE" 2>/dev/null || echo "0")
    QUEUE_DONE=$(grep -c '^\- \[x\]' "$CYCLE_FILE" 2>/dev/null || echo "0")
    DISCOVERIES=$(grep -c '^\- \[NEW\]' "$CYCLE_FILE" 2>/dev/null || echo "0")
    echo "Phase: $PHASE"
    echo "Queue: $QUEUE_PENDING pending, $QUEUE_DONE done"
    echo "New discoveries: $DISCOVERIES"
    # Show queue items awaiting human
    echo "--- Awaiting approval ---"
    grep '^\- \[ \] APPROVE' "$CYCLE_FILE" 2>/dev/null | head -5 || echo "(none)"
else
    echo "(no CYCLE.md — first run)"
fi

# --- Orchestrator tasks for this project ---
echo ""
echo "=== ORCHESTRATOR (${PROJECT_NAME}) ==="
if [[ -f "$ORCH_DB" ]]; then
    sqlite3 "$ORCH_DB" "SELECT id, pipeline, status, substr(prompt,1,60) FROM tasks WHERE project='$PROJECT_NAME' AND status NOT IN ('done','done_with_denials') ORDER BY id DESC LIMIT 5" 2>/dev/null || echo "(no tasks)"
else
    echo "(orchestrator DB not found)"
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

exit 0
