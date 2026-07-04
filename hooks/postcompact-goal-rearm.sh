#!/usr/bin/env bash
# PostCompact: re-arm the goal-run wrap-up ritual for the next fill cycle.
# Companion to stop-goal-wrapup.py / precompact-goal-guard.py (opt-in via .claude/goal-run).
set -uo pipefail
cwd=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null) || exit 0
[ -n "$cwd" ] && rm -f "$cwd/.claude/goal-wrapup-fired" "$cwd/.claude/goal-compact-blocks"
exit 0
