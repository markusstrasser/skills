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

# Reset dup-read counter — post-compaction re-reads are legitimate.
# Subagent trackers are named claude-reads-<agent_id>-$PPID (pretool-universal-dispatch.py
# agent_scope); the compacting agent is not identified here, so clear every tracker this CLI
# process owns. Over-clearing only loosens an advisory guard.
STATE_DIR="${CLAUDE_HOOK_STATE_DIR:-/tmp}"
rm -f "$STATE_DIR/claude-reads-$PPID" "$STATE_DIR/claude-toolcount-$PPID" \
      "$STATE_DIR"/claude-reads-*-"$PPID" "$STATE_DIR"/claude-toolcount-*-"$PPID"
# posttool-dup-read.sh keeps its own region tracker, which this reset used to miss.
rm -f "/tmp/claude-read-tracker-$PPID" /tmp/claude-read-tracker-*-"$PPID"

cat | python3 "$SCRIPT_DIR/precompact-extract.py"

exit 0
