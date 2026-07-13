#!/bin/bash
# PostToolUse:Bash — detect repeated file-stat commands on the same path
# Catches: wc, ls, head, tail, stat, cat, du targeting the same file 3+ times
# Complements posttool-dup-read.sh which only catches Read tool calls.
# Evidence: 4 recurrences of poll-loop pattern (2026-03-06 → 2026-03-29)

INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Extract file path from stat-like commands
# Matches: wc [-flags] /path, ls [-flags] /path, head/tail [-n N] /path, stat /path, cat /path, du /path
# Also: sleep N && wc /path (strip sleep prefix)
CMD_CLEAN=$(echo "$CMD" | sed 's/^sleep [0-9]*[smh]* *&&//' | sed 's/^ *//')
# Segment-scoped extraction: a stat verb only counts with a path from its OWN pipeline/command
# segment. Pipeline `| tail -N` / `| head -N` are output-shaping (no file arg) — the old
# whole-line grep matched them and then grabbed a path from a LATER `&&` segment, so N distinct
# write-CLI invocations (`... | tail -1 && git add /x`) collided into one "polled" token.
# Evidence: 2026-07-13 arc-agi — 15 distinct idea_backlog add/edit/done calls blocked as
# "Polled /idea_backlog.py 15x". Same extractor-degradation class as F2/binary/directory above.
PATH_TARGET=""
while IFS= read -r _seg; do
  _seg=$(echo "$_seg" | sed 's/^ *//')
  echo "$_seg" | grep -qE '^(command +)?(wc|ls|head|tail|stat|cat|du)\b' || continue
  _p=$(echo "$_seg" | grep -oE '(/[^ |;>&]+)' | head -1)
  [ -n "$_p" ] && { PATH_TARGET="$_p"; break; }
done <<EOF_SEGS
$(echo "$CMD_CLEAN" | sed 's/&&/\n/g; s/||/\n/g' | tr '|;' '\n')
EOF_SEGS
[ -z "$PATH_TARGET" ] && exit 0

# Shared read-only batch artifacts — parallel refute/extract fan-out reads these
# once per worker; not output-file poll loops (observe v2 poll-hook collision).
case "$PATH_TARGET" in
  */primer.md|*/_status.tsv) exit 0 ;;
esac

# Reject extraction artifacts that collide across DISTINCT file accesses:
#   - shell-quoted slashes (/" or /$VAR" patterns)
#   - paths ending in / (directory prefix with no leaf)
#   - paths shorter than 12 chars (likely /tmp/x, /dev/null, fragments)
#   - paths containing unexpanded $VAR
# Without this, `cat "$MEM/$f"` for distinct $f values all collide on /$f"
# and `ls ~/.claude/projects/` collides with all sub-path reads on /.claude/projects/.
# Evidence: docs/audit/observe-gaps-2026-05-11/findings.md F2 — false-fire at 17x.
case "$PATH_TARGET" in
  *'"'|*'$'*|*/) exit 0 ;;
esac
[ "${#PATH_TARGET}" -lt 12 ] && exit 0

# Reject BINARY paths — `ls dir | /usr/bin/grep x` extracts /usr/bin/grep as
# the "polled file" (the binary is the first absolute path after the verb).
# Fired 21-33x as a false positive across main + arm sessions on 2026-06-13;
# nobody polls a binary. Same artifact class as F2 above.
case "$PATH_TARGET" in
  /usr/bin/*|/bin/*|/sbin/*|/usr/local/bin/*|/opt/homebrew/bin/*|*/.bun/bin/*|*/node_modules/.bin/*) exit 0 ;;
esac

# Reject DIRECTORY targets — `ls DIR` / `du -sh DIR` extract a bare directory
# (no trailing slash, so the `*/` guard above misses it). A background task's
# output is always a FILE, never a directory, so re-running `ls`/`du` on the
# active project dir is normal work, not poll-loop. Without this, N distinct
# `ls`/`du` on one dir collapse to a single token and trip the counter.
# Same artifact class as F2 (17x) and the binary case (21-33x): the first-path
# extractor degrading to a coarser token than the polled leaf.
[ -d "$PATH_TARGET" ] && exit 0

# Scope tracker per session + fork context to avoid cross-subagent false positives
# CLAUDE_AGENT_ID is set for subagents; fall back to PPID for main session
_SCOPE="${CLAUDE_AGENT_ID:-${CLAUDE_SESSION_ID:-$PPID}}"
TRACKER="/tmp/claude-bash-poll-tracker-${_SCOPE}"
echo "$PATH_TARGET" >> "$TRACKER"

COUNT=$(grep -cF "$PATH_TARGET" "$TRACKER" 2>/dev/null || echo 0)

# TaskOutput is a deferred tool — must be loaded via ToolSearch before
# the agent can call it. Including the exact ToolSearch query in the
# block / advisory message saves the agent a guess-and-fail cycle.
LOAD_HINT='Load TaskOutput first: ToolSearch(query="select:TaskOutput,TaskList,TaskGet"). Then call TaskOutput with block=true to wait for the background task without polling.'

if [ "$COUNT" -ge 15 ]; then
  echo "BLOCKED: Polled ${PATH_TARGET} ${COUNT}x via Bash this session." >&2
  echo "Use TaskOutput (deferred tool) to wait for background tasks, or Read the file once when ready." >&2
  echo "${LOAD_HINT}" >&2
  exit 2
elif [ "$COUNT" -ge 10 ]; then
  printf '{"additionalContext": "Polled %s %sx via Bash. If waiting for a background task, prefer TaskOutput over polling. %s Next poll will be blocked."}' \
    "$PATH_TARGET" "$COUNT" "$LOAD_HINT"
fi
exit 0
