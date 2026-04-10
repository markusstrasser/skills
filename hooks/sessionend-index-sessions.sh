#!/usr/bin/env bash
# sessionend-index-sessions.sh — Incrementally update session search index.
# SessionEnd hook (async). Runs after sessionend-log.sh writes the receipt.
# Fails open — index staleness is annoying but not dangerous.

trap 'exit 0' ERR

# Small delay to let sessionend-log.sh finish writing the receipt
sleep 1

uv run --project ~/Projects/agent-infra python3 ~/Projects/agent-infra/scripts/sessions.py index 2>/dev/null

exit 0
