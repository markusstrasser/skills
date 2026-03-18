#!/usr/bin/env bash
# postmerge-overview.sh — Regenerate overviews after pull/merge.
# Install as .git/hooks/post-merge in opted-in projects.
#
# Runs generation in background so it doesn't block the terminal.

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
CONF="$PROJECT_ROOT/.claude/overview.conf"
GENERATE="$HOME/Projects/skills/hooks/generate-overview.sh"

[[ -f "$CONF" ]] || exit 0
[[ -x "$GENERATE" ]] || exit 0

export OVERVIEW_MODEL="gemini-3-flash-preview"

echo "Regenerating overviews after pull (background)..."
nohup "$GENERATE" --auto --project-root "$PROJECT_ROOT" > /tmp/overview-pull-$(basename "$PROJECT_ROOT").log 2>&1 &

# Update marker
MARKER="$PROJECT_ROOT/.claude/overview-marker"
mkdir -p "$(dirname "$MARKER")"
git rev-parse HEAD > "$MARKER"

exit 0
