#!/usr/bin/env bash
# postpush-overview.sh — Generate overviews after git push using the strongest model.
# Install as .git/hooks/post-push in opted-in projects, OR call from a git push wrapper.
#
# Git doesn't have a native post-push hook, so this is triggered by:
#   1. A pre-push hook that schedules it: nohup postpush-overview.sh &
#   2. Or a shell alias: git push && postpush-overview.sh
#
# Runs generation in the background so it never blocks anything.

set -euo pipefail

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
CONF="$PROJECT_ROOT/.claude/overview.conf"
GENERATE="$HOME/Projects/skills/hooks/generate-overview.sh"

# Only run if project is opted in
[[ -f "$CONF" ]] || exit 0
[[ -x "$GENERATE" ]] || { echo "generate-overview.sh not found" >&2; exit 0; }

# Override model to strongest long-context model
export OVERVIEW_MODEL="gemini-3.1-pro-preview"

echo "Generating overviews in background (model: $OVERVIEW_MODEL)..."
nohup "$GENERATE" --auto --project-root "$PROJECT_ROOT" > /tmp/overview-push-$(basename "$PROJECT_ROOT").log 2>&1 &

# Update marker so SessionEnd doesn't re-trigger for the same commits
MARKER="$PROJECT_ROOT/.claude/overview-marker"
mkdir -p "$(dirname "$MARKER")"
git rev-parse HEAD > "$MARKER"

exit 0
