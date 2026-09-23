#!/usr/bin/env bash
# prepare-commit-msg hook: auto-append Session-ID trailer to every commit.
# Prefers the committing process's own session id; the shared .claude/current-session-id
# (project, then global) is the last resort.
# Skips if trailer already present, merge commits, or no session ID found.

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"  # message, template, merge, squash, commit (amend)

# Skip merge commits
[ "$COMMIT_SOURCE" = "merge" ] && exit 0

# Skip if Session-ID already in message
grep -q "^Session-ID:" "$COMMIT_MSG_FILE" && exit 0

# Find session ID. PREFER a per-process agent identity, in this order:
#   $CLAUDE_SESSION_ID       Claude's Bash tool shell (it also has the next one, same value)
#   $CLAUDE_CODE_SESSION_ID  Claude hook processes, which lack the first (probed 2026-09-21),
#                            e.g. a Stop-hook auto-checkpoint commit
#   $CODEX_THREAD_ID         Codex
# All are race-immune. .claude/current-session-id is a SINGLE file shared by every
# concurrent agent in the project, so a peer overwriting it between this agent's
# work and its commit would stamp the commit with the PEER's id (mis-attributed
# provenance), and git-history-guard would then treat the commit as foreign. The env
# vars belong to this committing process and no peer can change them. Fall back to
# the project-level then global file only when all three are unset.
SID=""
PROCESS_SID="${CLAUDE_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-${CODEX_THREAD_ID:-}}}"
if [ -n "$PROCESS_SID" ]; then
    SID=$(printf '%s' "$PROCESS_SID" | tr -d '[:space:]')
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
