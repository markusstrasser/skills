#!/usr/bin/env bash
# Rate-limit-aware research cycle runner.
# If Claude is rate-limited (>=6 processes), runs through the shared Python
# dispatch helper instead of raw llmx CLI subprocess dispatch.
#
# Usage: run-cycle.sh [project_dir]
#   Or from Claude Code: ! ~/Projects/skills/research-cycle/scripts/run-cycle.sh

set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
CYCLE_FILE="$PROJECT_DIR/CYCLE.md"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_ROOT="$(cd "$SKILL_DIR/.." && pwd)"

MAX_PROCS="${RATE_LIMIT_THRESHOLD:-6}"
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
echo "Claude processes: $CLAUDE_PROCS (threshold: $MAX_PROCS)"

if [ "$CLAUDE_PROCS" -ge "$MAX_PROCS" ]; then
    echo "Rate-limited mode: routing through shared LLM dispatch"

    # Gather state (same script the skill uses)
    STATE=$("$SKILL_DIR/scripts/gather-cycle-state.sh" "$PROJECT_DIR" 2>&1 | head -80)

    if echo "$STATE" | grep -q "NO STATE CHANGE"; then
        echo "No state change — noop."
        exit 0
    fi

    # Build prompt from CYCLE.md + state
    CYCLE_CONTENT=""
    if [ -f "$CYCLE_FILE" ]; then
        CYCLE_CONTENT=$(head -200 "$CYCLE_FILE")
    fi

    cycle_context=$(mktemp /tmp/cycle-dispatch-context-XXXXXX)
    cycle_output=$(mktemp /tmp/cycle-dispatch-output-XXXXXX)
    cycle_meta=$(mktemp /tmp/cycle-dispatch-meta-XXXXXX)
    cycle_error=$(mktemp /tmp/cycle-dispatch-error-XXXXXX)

    cat > "$cycle_context" << PROMPT_EOF
# Research Cycle Tick (rate-limited mode)

Project: $PROJECT_DIR
Project name: $(basename "$PROJECT_DIR")

## Current State
$STATE

## CYCLE.md (current)
$CYCLE_CONTENT

## Instructions
You are running one tick of the research cycle. Pick the highest-priority phase:
1. Recent execution without verification → verify
2. Approved items in queue → execute (skip — can't execute code via llmx)
3. Active plan not yet reviewed → review
4. Gaps without plan → plan
5. Discoveries without gap analysis → gap-analyze
6. Verification done without improve → improve
7. Nothing pending → discover

For discover: search for new developments relevant to this project.
For gap-analyze: analyze discoveries and write gaps.
For plan/review: analyze and write recommendations.

Output your findings as markdown that should be appended to CYCLE.md.
Start with "## [Phase]: [description]" and include a date.
Be concise — this will be appended to a file.
PROMPT_EOF

    set +e
    uv run --project "$SKILLS_ROOT" python3 "$SKILLS_ROOT/scripts/llm-dispatch.py" \
        --profile cheap_tick \
        --context "$cycle_context" \
        --prompt "Run one research cycle tick. Output markdown for CYCLE.md." \
        --output "$cycle_output" \
        --meta "$cycle_meta" \
        --error-output "$cycle_error" \
        >/dev/null
    dispatch_exit=$?
    set -e

    if [ "$dispatch_exit" -eq 0 ] && [ -s "$cycle_output" ]; then
        echo "" >> "$CYCLE_FILE"
        cat "$cycle_output" >> "$CYCLE_FILE"
        echo "---"
        echo "Appended to CYCLE.md via shared dispatch (rate-limited mode)"
        head -5 "$cycle_output"
    else
        echo "Dispatch failed — skipping this tick" >&2
        if [ -s "$cycle_error" ]; then
            cat "$cycle_error" >&2
        elif [ -s "$cycle_meta" ]; then
            cat "$cycle_meta" >&2
        fi
        rm -f "$cycle_context" "$cycle_output" "$cycle_meta" "$cycle_error"
        exit 1
    fi

    rm -f "$cycle_context" "$cycle_output" "$cycle_meta" "$cycle_error"
else
    echo "Normal mode: running via Claude skill"
    echo "Use /research cycle in your Claude session instead."
    echo "(This script is for rate-limited fallback only)"
fi
