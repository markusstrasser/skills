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

uv run --project ~/Projects/agent-infra agentlogs index 2>/dev/null

exit 0
