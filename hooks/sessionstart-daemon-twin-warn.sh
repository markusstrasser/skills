#!/usr/bin/env bash
# sessionstart-daemon-twin-warn.sh — warn when a RESTART left a daemon-hosted twin of a
# prior session still executing against this checkout (double-spend + venue corruption).
#
# Exhibit 2026-07-10 (arc-agi): operator restart mid-/goal-run; the old conversation was
# adopted by the daemon as a bg job ("template":"bg") hosted in a `claude bg-spare` worker,
# which kept executing the same night queue — own monitors, resume agents in the same
# worktree, 4 commits — until manually hunted. Full detection/kill recipe:
#   arc-agi memory: harness_restart_daemon_duplicate.md
# Pre-empted past the pair-rule: a zombie main committing to the live worktree is in the
# verdict-corruption severity class (wait-for-recurrence expected cost > hook cost).
#
# Signals (both cheap, both fail-open; advisory only — never wedge SessionStart):
#   1. Another transcript for THIS project modified within the last $FRESH_S seconds
#      (a twin transcript growing beside yours).
#   2. A ~/.claude/jobs/*/state.json with "template": "bg" whose payload references this
#      project (a daemon-adopted background copy).
set -uo pipefail
FRESH_S=180

input="$(cat 2>/dev/null || true)"
cwd="$(printf '%s' "$input" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d.get("cwd","") or "")
except Exception:
    print("")' 2>/dev/null || true)"
sid="$(printf '%s' "$input" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d.get("session_id","") or "")
except Exception:
    print("")' 2>/dev/null || true)"
[ -z "$cwd" ] && cwd="$(pwd -P 2>/dev/null || true)"
[ -z "$cwd" ] && exit 0

slug="$(printf '%s' "$cwd" | tr '/.' '--')"
proj_dir="$HOME/.claude/projects/$slug"
now="$(date +%s)"
warn=""

# A fresh transcript ALONE is NOT a signal: interactive peers are covered by the
# peer-session warning, and this session's own subagents/teammates write fresh
# transcripts too (the "descendants are not peers" fiction, 2026-06-18 — confirmed
# live 2026-07-10: the naive version flagged its own teammate agents).
# The discriminating signal: a daemon bg-adopted job whose OWN transcript
# (prefix = daemonShort) is still growing — that is a live twin EXECUTING.
for st in "$HOME"/.claude/jobs/*/state.json; do
  [ -e "$st" ] || continue
  grep -q '"template"[[:space:]]*:[[:space:]]*"bg"' "$st" 2>/dev/null || continue
  short="$(basename "$(dirname "$st")")"
  [ -n "$sid" ] && case "$sid" in "$short"*) continue ;; esac
  # Job must reference this project: match slug in state, or its transcript lives in proj_dir.
  twin=""
  for f in "$proj_dir/$short"*.jsonl; do [ -e "$f" ] && twin="$f" && break; done
  if [ -z "$twin" ]; then
    grep -qF "$slug" "$st" 2>/dev/null || continue
  fi
  if [ -n "$twin" ]; then
    mtime="$(stat -f %m "$twin" 2>/dev/null || echo 0)"
    if [ $((now - mtime)) -lt "$FRESH_S" ]; then
      warn="${warn}LIVE-TWIN: bg job $short — transcript $twin modified $((now - mtime))s ago (daemon copy still EXECUTING)."$'\n'
    fi
  fi
done

[ -z "$warn" ] && exit 0

cat <<EOF
⚠ POSSIBLE DAEMON TWIN of a prior session on this checkout:
${warn}▶ Before executing any queue: run the detection recipe (arc-agi memory
  harness_restart_daemon_duplicate.md) — marker-test identity (echo WHOAMI-\$RANDOM, grep both
  jsonls), lsof-verify the bg-spare host's cwd BEFORE killing, kill -TERM the host, then sweep
  'ps aux | grep -- "--resume.*<jsonl-prefix>"' for the leftover resume child (step 5).
  A growing twin transcript = a live duplicate EXECUTING your queue. Adopt its valid detached
  work; do not re-run it.
EOF
exit 0
