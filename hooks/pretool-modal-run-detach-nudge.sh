#!/bin/bash
# PreToolUse:Bash — advisory nudge when `modal run` is launched WITHOUT --detach.
#
# Evidence: 2026-08-19 arc-agi 9fb0b1e4 — a healthy $4.54/h H200 training run was
# killed at step 350 by the LOCAL client's disconnect (laptop sleep drops the gRPC
# heartbeat; server cancels: "Stopping app - local client disconnected"). The fix was
# printed in the error itself (--detach) and already implied by modal-skill gotcha 10;
# neither was consulted at launch-command time. Gotcha 23 documents the class; this
# nudge surfaces it AT the decision point, which is the only place it helps.
#
# Advisory only — never blocks (short local `modal run` without --detach is legitimate,
# e.g. dry-runs, smokes). Suppressed for subagents (parents own launch discipline).

INPUT=$(cat)

[ -n "$CLAUDE_AGENT_ID" ] && exit 0

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
case "$CMD" in
  *"modal run "*) ;;
  *) exit 0;;
esac
case "$CMD" in
  *"--detach"*|*"--dry-run"*|*"--help"*) exit 0;;
esac

printf '{"additionalContext": "MODAL-DETACH: this `modal run` has no --detach — if the remote wall exceeds minutes, a laptop sleep or network blip kills the healthy remote run (client heartbeat drop => server cancels; measured 2026-08-19, $3.5 training run killed at step 350). Add --detach for anything long (monitor via app logs + volume artifacts; client log then reflects CLIENT state, not job state), or state that this run is short/interactive on purpose."}'
exit 0
