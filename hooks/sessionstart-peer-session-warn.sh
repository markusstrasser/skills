#!/usr/bin/env bash
# SessionStart (global): warn when a peer `claude` session shares this checkout.
#
# Concurrent interactive sessions on ONE working copy clobber shared .claude/
# state (checkpoint.md, current-session-id, trackers) — the #1 cross-session
# failure found by the 2026-06-13 drift pass. The field-standard fix is
# isolate-per-agent + merge via git (CAID arXiv:2603.21489; worktree>soft 7.8pp).
# This hook nudges toward `claude --worktree` when it detects the risk.
#
# Advisory only, ALWAYS exit 0 (constitution principle 10: fail open).
# Disable with PEER_SESSION_WARN_OFF=1. Detection is claude-vs-claude (the clean,
# reliable signal — `claude` is the literal process name); codex peers are
# mentioned in the text but not enumerated (its process model is murkier).
#
# Decision: agent-infra decisions/2026-06-13-multiagent-shared-state-event-sourcing.md
set -uo pipefail

[ "${PEER_SESSION_WARN_OFF:-0}" = "1" ] && exit 0

input="$(cat 2>/dev/null || true)"
cwd="$(printf '%s' "$input" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("cwd","") or "")
except Exception: print("")' 2>/dev/null)"
[ -z "$cwd" ] && cwd="$(pwd -P 2>/dev/null || true)"
[ -z "$cwd" ] && exit 0
# canonicalize so /tmp vs /private/tmp etc. compare equal
cwd="$(cd "$cwd" 2>/dev/null && pwd -P || printf '%s' "$cwd")"

# Peer detection is SINGLE-SOURCED in peer-session-count.sh (epistemic-#9) — the
# exact same detector the Stop hook (stop-uncommitted-warn.sh) uses, so both hooks
# agree on "does a peer share this checkout". It counts INDEPENDENT claude trees
# whose cwd is here, excluding my own subagents/children. Fail-open → 0.
peers="$(~/Projects/skills/hooks/peer-session-count.sh "$cwd" 2>/dev/null || echo 0)"

if [ "$peers" -ge 1 ]; then
  base="$(basename "$cwd")"
  sfx="$(date +%H%M 2>/dev/null || echo 2)"
  # LOUD + one-paste-actionable (operator's 2026-06-14 ask): re-fires every session
  # a peer is present, so it can't be forgotten; carries the exact isolate command
  # so acting is a single paste, not a recall-from-memory task. No silent magic.
  echo "⚠  PEER SESSION — ${peers} other claude session(s) share this checkout:"
  echo "       ${cwd}"
  echo "   Shared .claude/ state (current-session-id, trackers, checkpoint) WILL clobber across them"
  echo "   → mis-stamped commits + cross-session confusion (auto-checkpoint now fails closed, but state still thrashes)."
  echo "   ▶ Isolate THIS session — exit, then relaunch in its own worktree (one paste):"
  echo "         claude --worktree ${base}-wt${sfx}"
  echo "   (branches local HEAD; merge back via git. Parallel codex = same risk. Silence: PEER_SESSION_WARN_OFF=1)"
  # Log the fire so the 2026-06-28-peer-warn prediction (does the loud form reduce
  # concurrent-session sharing?) is measurable, not vibes.
  ~/Projects/skills/hooks/hook-trigger-log.sh "peer-session-warn" "warn" "peers=${peers}" 2>/dev/null || true
fi
exit 0
