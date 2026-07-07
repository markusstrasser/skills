#!/usr/bin/env bash
# MessageDisplay — prepend local [HH:MM] to the FIRST line of each assistant
# message on screen. Display-only (stored message + model view untouched).
#
# KNOWN LIMITATION (Claude Code 2.1.202, verified 2026-07-07): the hook fires
# and returns correct displayContent on both the streaming and completed-message
# (izc) paths, but CC does NOT persist the transform into scrollback history —
# the static transcript re-renders from the raw stored message. Result: the
# timestamp flashes while the message finalizes, then vanishes once it scrolls
# into history. Native showMessageTimestamps is separately dead — its render
# prop is `setting && nt("tengu_silk_hinge")`, a server-side Statsig gate that
# is off by default with no client/env override. Neither path is fixable here.
set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

ts="$(date '+%H:%M')"
jq --arg ts "$ts" '
  if .index == 0 then
    {hookSpecificOutput: {hookEventName: "MessageDisplay", displayContent: ("[" + $ts + "] " + .delta)}}
  else
    {hookSpecificOutput: {hookEventName: "MessageDisplay", displayContent: .delta}}
  end
'
