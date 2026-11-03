#!/bin/bash
# PostToolUse:SendMessage — flag a message to a teammate that was queued, not delivered.
#
# SendMessage to an in-process teammate either resumes it ("was not running; resumed it ... with your message as
# its next prompt") or appends to its inbox ("Message sent to <name>'s inbox"). A busy teammate reads its inbox only
# when its turn ends, and an idle one never does. On 2026-11-03 two sends to idle falsedup-row48 (09:03 and 09:13
# KST) sat unread for 24 min until TaskStop + SendMessage resumed it. Earlier recurrences: 10-27 (58 min), 10-31
# (3 h), 11-02 (2 h); genomics memory feedback_lane_messages_wait_for_turn_end.
#
# Advisory only, never blocks. Main loop only: a subagent's send goes to main, which always reads. The idle check
# runs lane-stall-watch --once on this session's subagents dir; LANE_STALL_WATCH overrides the binary for tests.

INPUT=$(cat)
. "$(dirname "$0")/lib_hook_identity.sh" 2>/dev/null || exit 0
hook_identity "$INPUT"
[ -n "$HOOK_AGENT_ID" ] && exit 0

RESPONSE=$(printf '%s' "$INPUT" | jq -r '.tool_response | tostring' 2>/dev/null)
case $RESPONSE in
  *"inbox"*) ;;
  *) exit 0 ;;
esac
TO=$(printf '%s' "$INPUT" | jq -r '.tool_input.to // ""' 2>/dev/null)
TO=${TO//[^A-Za-z0-9_-]/}
case $TO in "" | main | team-lead) exit 0 ;; esac

TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // ""' 2>/dev/null)
SUBAGENTS="${TRANSCRIPT%.jsonl}/subagents"
WATCH=${LANE_STALL_WATCH:-$HOME/Projects/skills/bin/lane-stall-watch}
STATE=""
if [ -n "$TRANSCRIPT" ] && [ -d "$SUBAGENTS" ] && [ -x "$WATCH" ]; then
  STATE=$(timeout 15 "$WATCH" --once "$SUBAGENTS" "$TO" 2>/dev/null | tail -1)
fi

case $STATE in
  *"-> IDLE"*)
    MSG="UNDELIVERED: $TO is idle, and an idle teammate never reads its inbox, so this message will sit unread ($STATE). TaskStop $TO, then send ONE message restating everything still open."
    ;;
  *)
    MSG="QUEUED, not delivered: $TO reads its inbox only when its current turn ends, which can take hours. If this message changes its current work, TaskStop $TO and resend it as one restating message."
    ;;
esac
jq -n --arg msg "$MSG" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $msg}}'
exit 0
