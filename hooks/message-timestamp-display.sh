#!/usr/bin/env bash
# MessageDisplay — prepend local [HH:MM] to the FIRST line of each assistant
# message on screen. Display-only (stored message + model view untouched).
# Native showMessageTimestamps is gated behind the server-side tengu_silk_hinge
# Statsig flag (off by default, no client override), so this hook is the only
# working path. Wired globally in ~/.claude/settings.json → all projects.
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
