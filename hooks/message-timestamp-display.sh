#!/usr/bin/env bash
# MessageDisplay — prepend local [HH:MM] to assistant text on screen only.
# Native showMessageTimestamps is gated behind tengu_silk_hinge (off by default).
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
