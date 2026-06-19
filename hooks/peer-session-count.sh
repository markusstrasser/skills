#!/usr/bin/env bash
# peer-session-count.sh — print the number of INDEPENDENT `claude` sessions whose
# cwd is the given checkout, EXCLUDING this session's own claude tree (subagents,
# `claude -p`, hung children are DESCENDANTS — never peers; counting them drove a
# multi-hour multi-agent-collision fiction, 2026-06-18).
#
# THE single source for "do peers share this checkout?" (epistemic-principle #9 —
# one definition, consumers LOAD it). Consumers:
#   - sessionstart-peer-session-warn.sh  → the loud isolate-to-a-worktree nudge.
#   - stop-uncommitted-warn.sh           → do NOT claim a subprocess-written file
#     is "most likely YOURS" when a peer sharing the checkout could have written it
#     (the recurring mis-attribution that nudged 4 peer files toward commit, 2026-06-19).
#
# Usage:  peer-session-count.sh [<cwd>]   (cwd arg; else reads {"cwd":...} on stdin; else $PWD)
# Output: a single integer on stdout. Fail-open → 0 on any error (advisory; never wedge).
set -uo pipefail

cwd="${1:-}"
if [ -z "$cwd" ]; then
  cwd="$(python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("cwd","") or "")
except Exception: print("")' 2>/dev/null || true)"
fi
[ -z "$cwd" ] && cwd="$(pwd -P 2>/dev/null || true)"
[ -z "$cwd" ] && { echo 0; exit 0; }
cwd="$(cd "$cwd" 2>/dev/null && pwd -P || printf '%s' "$cwd")"  # canonicalize (/tmp vs /private/tmp)

pids="$(pgrep -x claude 2>/dev/null | paste -sd, - || true)"
[ -z "$pids" ] && { echo 0; exit 0; }

# my session's claude (walk up from THIS helper's PID — the helper is a descendant
# of the calling hook, which is a descendant of my session's claude). Descendants
# of my_claude are mine, never peers.
my_claude=""; p=$$
while [ "${p:-0}" -gt 1 ]; do
  case "$(ps -o comm= -p "$p" 2>/dev/null | tr -d ' ')" in *claude*) my_claude="$p"; break;; esac
  p="$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')"
done

# claude PIDs whose cwd == this checkout.
cand="$(lsof -a -d cwd -Fpn -p "$pids" 2>/dev/null \
        | awk -v c="$cwd" '/^p/{pid=substr($0,2)} /^n/{if(substr($0,2)==c)print pid}')"

_is_mine() {  # true if $1 is my session's claude or a descendant of it
  [ -z "$my_claude" ] && return 1
  local q="$1"
  while [ "${q:-0}" -gt 1 ]; do
    [ "$q" = "$my_claude" ] && return 0
    q="$(ps -o ppid= -p "$q" 2>/dev/null | tr -d ' ')"
  done
  return 1
}
peers=0
for pid in $cand; do _is_mine "$pid" || peers=$((peers + 1)); done
# Fallback: if our own claude PID couldn't be identified, degrade to self-minus-one
# rather than over-counting.
if [ -z "$my_claude" ]; then
  cnt="$(printf '%s\n' "$cand" | grep -c . 2>/dev/null || echo 0)"
  [ "$cnt" -gt 0 ] && peers=$((cnt - 1)) || peers=0
fi
echo "$peers"
exit 0
