#!/usr/bin/env bash
# precompact-log.sh — Preserve epistemic content + context before compaction.
# PreCompact hook. Side-effect only (no decision control). Fails open.
# Outputs:
#   1. ~/.claude/compact-log.jsonl — append-only compaction metrics
#   2. <project>/.claude/checkpoint.md — resume checkpoint with epistemic content
#
# The key insight: compaction destroys hedged claims, negative results, open
# questions, and decision rationale — flattening them into confident assertions.
# This hook extracts the CONTENT (not just counts) so it survives.

trap 'exit 0' ERR

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cat | python3 "$SCRIPT_DIR/precompact-extract.py"

exit 0
