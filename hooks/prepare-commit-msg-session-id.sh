#!/usr/bin/env bash
# prepare-commit-msg hook: auto-append Session-ID trailer to every commit.
# Reads from .claude/current-session-id (project-level) or ~/.claude/current-session-id (global).
# Skips if trailer already present, merge commits, or no session ID found.

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"  # message, template, merge, squash, commit (amend)

# Skip merge commits
[ "$COMMIT_SOURCE" = "merge" ] && exit 0

# Skip if Session-ID already in message
grep -q "^Session-ID:" "$COMMIT_MSG_FILE" && exit 0

# Find session ID. PREFER the per-process env var $CLAUDE_SESSION_ID: it is
# race-immune. .claude/current-session-id is a SINGLE file shared by every
# concurrent agent in the project, so a peer overwriting it between this agent's
# work and its commit would stamp the commit with the PEER's id (mis-attributed
# provenance). The env var belongs to this committing process and no peer can
# change it. Fall back to project-level then global file when the var is unset.
SID=""
if [ -n "$CLAUDE_SESSION_ID" ]; then
    SID=$(printf '%s' "$CLAUDE_SESSION_ID" | tr -d '[:space:]')
fi
if [ -z "$SID" ]; then
    for sid_path in ".claude/current-session-id" "$HOME/.claude/current-session-id"; do
        if [ -f "$sid_path" ]; then
            SID=$(cat "$sid_path" 2>/dev/null | tr -d '[:space:]')
            [ -n "$SID" ] && break
        fi
    done
fi

# No session ID found — skip silently
[ -z "$SID" ] && exit 0

# Append trailer. Git trailers need a blank line separator if body exists.
# Check if file already ends with a trailer block (key: value pattern)
if tail -1 "$COMMIT_MSG_FILE" | grep -qE '^[A-Za-z][-A-Za-z]*:'; then
    # Already in trailer block — just append
    echo "Session-ID: $SID" >> "$COMMIT_MSG_FILE"
else
    # Add blank line then trailer
    echo "" >> "$COMMIT_MSG_FILE"
    echo "Session-ID: $SID" >> "$COMMIT_MSG_FILE"
fi

exit 0
