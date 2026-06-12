#!/usr/bin/env bash
# userprompt-context-warn.sh — Detect continuation boilerplate pastes.
# UserPromptSubmit hook. Non-blocking (exit 0). Warns user that checkpoint.md
# exists and manual context pasting is unnecessary.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract user message and cwd
USER_MSG=$(printf '%s' "$INPUT" | jq -r '.user_message // ""' 2>/dev/null || true)

CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || true)

# Check for continuation boilerplate patterns
if echo "$USER_MSG" | grep -qi "continued from a previous conversation\|session is being continued\|context ran out\|ran out of context\|previous conversation that ran out"; then
    # Check if checkpoint.md exists
    if [ -n "$CWD" ] && [ -f "$CWD/.claude/checkpoint.md" ]; then
        echo "checkpoint.md exists in .claude/ — the agent will auto-read it. No need to paste continuation context." >&2
    fi
fi

exit 0
