#!/bin/bash
# PostToolUse:Bash — bgrun watcher-pairing nudge.
#
# Evidence: 2026-08-19 arc-agi session 9fb0b1e4 — three morning bgrun relaunches
# (att1-train3/4, mtp-probe5) launched with NO paired watcher while the previous
# night's lanes all had them; att1-train3 died at 09:27 (modal client disconnect)
# and sat undiscovered 73 minutes until the operator prompted "check status?".
# Operator: "why do i need to prompt you... this should be dynamic, event based"
# → "then make the fucking hook". The pattern (bgrun prints its native wait command;
# pair it in the same turn) is documented in wakeup-cadence.md and still got
# skipped under momentum — recurring discipline failure → hook (pair-rule).
#
# Iatrogenic guards: advisory only (never blocks); suppressed for subagents
# (their parents own the watch decision); silent when the launching command
# already contains a watcher fragment for the same name.

INPUT=$(cat)

. "$(dirname "$0")/lib_hook_identity.sh" 2>/dev/null || exit 0
hook_identity "$INPUT"
[ -n "$HOOK_AGENT_ID" ] && exit 0

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
STDOUT=$(printf '%s' "$INPUT" | jq -r '
  .tool_response // "" |
  if type == "object" then .stdout // ""
  elif type == "string" then . else "" end' 2>/dev/null)

# Prefer the launch output: it supplies the resolved, shell-quoted BGRUN_DIR.
NAME=$(printf '%s\n' "$STDOUT" | sed -n 's/^bgrun: \([A-Za-z0-9._-][A-Za-z0-9._-]*\) pid=.*/\1/p' | head -n 1)
if [ -z "$NAME" ]; then
  # A launch is `bgrun NAME -- cmd`; a name never starts with "-" (`bgrun --wait x`
  # was read as a launch of '--wait' 77 times, hook audit 2026-10-24).
  NAME=$(printf '%s' "$CMD" | sed -nE 's/(^|.*[[:space:];&|/])bgrun[[:space:]]+([A-Za-z0-9_][A-Za-z0-9._-]*)[[:space:]]+--([[:space:]].*|$)/\2/p' | head -n 1)
fi
[ -z "$NAME" ] && exit 0
WATCH=$(printf '%s\n' "$STDOUT" | sed -n 's/^  watch: //p' | head -n 1)
case "$WATCH" in
  "BGRUN_DIR="*" --wait $NAME") ;;
  *) WATCH="";;
esac

# The printed native command binds both directory and name without shell evaluation.
[[ -n "$WATCH" && "$CMD" == *"$WATCH"* ]] && exit 0

# A bare same-name wait shares the launch directory only with unchanged settings.
# Assignment scope, exports and unsets are uncertain here; keep the advisory nudge.
WAIT_NAME=${NAME//./\\.}
WAIT_PATTERN="bgrun[\"']?[[:space:]]+--wait[[:space:]]+[\"']?${WAIT_NAME}[\"']?([[:space:];|&)]|$)"
DIRECTORY_UNCERTAIN=false
if [[ "$CMD" =~ $WAIT_PATTERN ]]; then
  case "$CMD" in
    *BGRUN_DIR*|*TMPDIR*) DIRECTORY_UNCERTAIN=true;;
    *) exit 0;;
  esac
fi

if [ -n "$WATCH" ]; then
  ADVICE="arm its native exit watcher (Bash run_in_background: $WATCH)"
else
  ADVICE="[DEGRADED] read this launch's missing stdout and arm its printed watch: command, which supplies the exact BGRUN_DIR for bgrun --wait $NAME"
fi
if [ "$DIRECTORY_UNCERTAIN" = true ]; then
  ADVICE="[DEGRADED] the same-name wait's directory is unproven; $ADVICE"
fi
jq -cn --arg message "WATCHER-PAIRING: bgrun '$NAME' launched with no proved matching native watcher in this call. Before this turn ends, $ADVICE or state explicitly why tick sweeps suffice. A detached/remote job additionally needs its server-side liveness read named. (Evidence: 73-min blind training death, 2026-08-19.)" '{additionalContext: $message}'
exit 0
