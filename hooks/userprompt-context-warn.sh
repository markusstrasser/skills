#!/usr/bin/env bash
# userprompt-context-warn.sh — Detect continuation boilerplate pastes.
# UserPromptSubmit hook. Non-blocking (exit 0). Warns user that checkpoint.md
# exists and manual context pasting is unnecessary.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract user message and cwd. CC 2.1.x renamed the field `.user_message` ->
# `.prompt` (~2026-06-16); read the new field, fall back to the old, flag missing-both.
USER_MSG=$(printf '%s' "$INPUT" | jq -r '.prompt // .user_message // ""' 2>/dev/null || true)
if [ -n "$INPUT" ] && [ "$(printf '%s' "$INPUT" | jq -r 'has("prompt") or has("user_message")' 2>/dev/null)" = "false" ]; then
    echo "[DEGRADED] userprompt-context-warn: envelope has neither .prompt nor .user_message — CC UserPromptSubmit contract drifted" >&2
fi

CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || true)

# Check for continuation boilerplate patterns
if echo "$USER_MSG" | grep -qi "continued from a previous conversation\|session is being continued\|context ran out\|ran out of context\|previous conversation that ran out"; then
    # Check if checkpoint.md exists
    if [ -n "$CWD" ] && [ -f "$CWD/.claude/checkpoint.md" ]; then
        echo "checkpoint.md exists in .claude/ — the agent will auto-read it. No need to paste continuation context." >&2
    fi
fi

exit 0
