#!/bin/bash
# PostToolUse:Bash — bgrun watcher-pairing nudge.
#
# Evidence: 2026-08-19 arc-agi session 9fb0b1e4 — three morning bgrun relaunches
# (att1-train3/4, mtp-probe5) launched with NO paired watcher while the previous
# night's lanes all had them; att1-train3 died at 09:27 (modal client disconnect)
# and sat undiscovered 73 minutes until the operator prompted "check status?".
# Operator: "why do i need to prompt you... this should be dynamic, event based"
# → "then make the fucking hook". The pattern (bgrun prints its own watch loop;
# pair it in the same turn) is documented in wakeup-cadence.md and still got
# skipped under momentum — recurring discipline failure → hook (pair-rule).
#
# Iatrogenic guards: advisory only (never blocks); suppressed for subagents
# (their parents own the watch decision); silent when the launching command
# already contains a watcher fragment for the same name.

INPUT=$(cat)

[ -n "$CLAUDE_AGENT_ID" ] && exit 0

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
case "$CMD" in
  *"bgrun "*) ;;
  *) exit 0;;
esac

# First bgrun invocation's name token: `bgrun <name> -- <cmd...>` (also matches
# `... && bgrun <name> ...`). Name charset per bgrun's own contract.
NAME=$(printf '%s' "$CMD" | sed -n 's/.*bgrun  *\([A-Za-z0-9._-][A-Za-z0-9._-]*\).*/\1/p')
[ -z "$NAME" ] && exit 0

# Compound commands that already arm a watcher for this name need no nudge.
case "$CMD" in
  *"$NAME.done"*) exit 0;;
esac

printf '{"additionalContext": "WATCHER-PAIRING: bgrun '\''%s'\'' launched with no watcher in this call. Before this turn ends, arm its exit watcher (Bash run_in_background: until [ -f $TMPDIR/bgrun/%s.done ]; do sleep 20; done; echo \\"%s rc=$(cat $TMPDIR/bgrun/%s.done)\\") or state explicitly why tick sweeps suffice. A detached/remote job additionally needs its server-side liveness read named. (Evidence: 73-min blind training death, 2026-08-19.)"}' "$NAME" "$NAME" "$NAME" "$NAME"
exit 0
