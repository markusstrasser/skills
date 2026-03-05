#!/usr/bin/env bash
# posttool-research-reformat.sh — PostToolUse hook for research MCP output cleanup.
# Uses updatedMCPToolOutput to quarantine noisy paper/search MCP output
# before Claude sees it. Preserves raw output in ~/.claude/tool-output-archive/.
#
# Deploy to research/search-style MCPs in PostToolUse.
# Fails open (exit 0 on any error).

trap 'exit 0' ERR

INPUT=$(cat)

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "$INPUT" | python3 "$HOOK_DIR/posttool_research_reformat.py" 2>/dev/null

exit 0
