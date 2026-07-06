#!/usr/bin/env bash
# userprompt-clock.sh — inject current local wall-clock time into every user turn.
# Gov-ID: hook:userprompt-clock
# goal: long event-driven autonomous sessions drift on time-of-day — the harness injects the
#       DATE only, so notification bursts carry no time anchor and step-timer arithmetic goes wrong
#       (arc-agi 5e29ecd4: agent believed ~15:30 at 19:53, mis-prioritized limit-reset/farm-ETA work).
# verifier: skills/hooks/test_userprompt_clock.py
# blast_radius: shared
#
# UserPromptSubmit hook. Advisory/additive ONLY — emits hookSpecificOutput.additionalContext,
# never blocks, no state mutation. Read-only `date`. Reversibility: delete the hook + registration.
trap 'exit 0' ERR

NOW=$(date '+%Y-%m-%d %H:%M %Z')
printf '{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "[clock: %s]"}}\n' "$NOW"
exit 0
