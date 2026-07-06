#!/usr/bin/env bash
# PostCompact: re-arm the goal-run wrap-up ritual for the next fill cycle.
# Companion to stop-goal-wrapup.py / precompact-goal-guard.py (opt-in via .claude/goal-run).
# Owner-gated like its companions: a PEER session compacting in an armed repo must not
# erase the owner's ritual/block state (would re-prompt the ritual and reset the
# blocked-compact cap mid-cycle).
set -uo pipefail
out=$(python3 -c "
import sys, json
p = json.load(sys.stdin)
print(p.get('cwd', ''))
print(p.get('session_id', ''))
" 2>/dev/null) || exit 0
cwd=$(printf '%s\n' "$out" | sed -n 1p)
sid=$(printf '%s\n' "$out" | sed -n 2p)
[ -n "$cwd" ] || exit 0
marker="$cwd/.claude/goal-run"
[ -f "$marker" ] || exit 0
owner=$(awk 'NR==1 {print $2}' "$marker" 2>/dev/null || true)
if [ -n "${owner:-}" ] && [ "$sid" != "$owner" ]; then exit 0; fi
rm -f "$cwd/.claude/goal-wrapup-fired" "$cwd/.claude/goal-compact-blocks"
exit 0
