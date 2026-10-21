#!/usr/bin/env bash
# userprompt-context-warn.sh — Detect continuation boilerplate pastes.
# UserPromptSubmit hook. Non-blocking (exit 0). Warns user that this session's
# resume checkpoint exists and manual context pasting is unnecessary.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract user message and cwd. CC 2.1.x renamed the field `.user_message` ->
# `.prompt` (~2026-06-16); read the new field, fall back to the old, flag missing-both.
USER_MSG=$(printf '%s' "$INPUT" | jq -r '.prompt // .user_message // ""' 2>/dev/null || true)
if [ -n "$INPUT" ] && [ "$(printf '%s' "$INPUT" | jq -r 'has("prompt") or has("user_message")' 2>/dev/null)" = "false" ]; then
    echo "[DEGRADED] userprompt-context-warn: envelope has neither .prompt nor .user_message — CC UserPromptSubmit contract drifted" >&2
fi

CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || true)
SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null || true)

# Check for continuation boilerplate patterns
if echo "$USER_MSG" | grep -qi "continued from a previous conversation\|session is being continued\|context ran out\|ran out of context\|previous conversation that ran out"; then
    # Is there a checkpoint stamped with THIS session at the project root the PreCompact
    # writer uses (git toplevel of the drifting hook cwd)? A peer's file does not count.
    HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
    ROOT="$CWD"
    if [ -n "$CWD" ]; then
        ROOT=$(python3 "$HOOK_DIR/checkpoint_resume.py" project-root "$CWD" 2>/dev/null || echo "$CWD")
    fi
    if [ -n "$ROOT" ] && [ -n "$SID" ]; then
        OWN=$(python3 "$HOOK_DIR/checkpoint_resume.py" select-read "$ROOT/.claude" "$SID" 2>/dev/null \
            | jq -r 'select(.is_current) | .path' 2>/dev/null || true)
        if [ -n "$OWN" ]; then
            echo "This session's checkpoint exists ($OWN) — the agent will auto-read it. No need to paste continuation context." >&2
        fi
    fi
fi

exit 0
