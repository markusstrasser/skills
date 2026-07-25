#!/usr/bin/env bash
# sessionend-index-sessions.sh — Incrementally update agentlogs search index.
# SessionEnd hook (async). Runs after sessionend-log.sh writes the receipt.
# Fails open — index staleness is annoying but not dangerous.
#
# Note: launchd WatchPaths (com.agent-infra.agentlogs-index) also triggers on
# session JSONL writes. This hook is a belt-and-suspenders guarantee that the
# just-closed session is indexed before the user's next invocation, without
# waiting on the launchd ThrottleInterval window.

trap 'exit 0' ERR

# Small delay to let sessionend-log.sh finish writing the receipt
sleep 1

# BOUNDED, not a full pass. This hook's job is only "get the session that just
# closed into the index" — but an unflagged `agentlogs index` enumerates the ENTIRE
# raw corpus (16k+ files across claude/codex/cursor) under the 600s default budget,
# once per session end. At ~1400 sessions/week that is 1400 full enumerations all
# contending for the single writer lock, which is how the launchd job ended up
# starved behind a permanent queue (2026-07-25: 16h with no successful index).
# Newest-first ordering means a 1-day window reaches the just-closed session first.
uv run --project ~/Projects/agent-infra agentlogs index \
  --since-days 1 --limit-sources 5 --max-run-seconds 60 2>/dev/null

exit 0
