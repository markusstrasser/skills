#!/usr/bin/env bash
# PostToolUse:Read — track reads of skill reference files for L3 adoption measurement
# Lightweight: logs to ~/.claude/l3-reads.jsonl
# Advisory only (exit 0)

[[ "$CLAUDE_TOOL_NAME" != "Read" ]] && exit 0

# Extract file_path from tool input (jq for reliable JSON parsing)
file_path=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // empty' 2>/dev/null)
[ -z "$file_path" ] && exit 0

# Only care about skill references/ directories
echo "$file_path" | grep -q '/skills/.*/references/' || exit 0

# Extract skill name and reference file
skill_name=$(echo "$file_path" | sed -n 's|.*/skills/\([^/]*\)/references/.*|\1|p')
ref_file=$(basename "$file_path")
[ -z "$skill_name" ] && exit 0

echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"skill\":\"$skill_name\",\"ref\":\"$ref_file\",\"session\":\"${CLAUDE_SESSION_ID:-unknown}\"}" >> ~/.claude/l3-reads.jsonl

exit 0
