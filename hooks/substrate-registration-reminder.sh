#!/bin/bash
# Advisory hook: remind agents to register in knowledge substrate when writing canonical docs.
# PostToolUse on Write/Edit. Does not block — just prints a reminder.
#
# Canonical directories per project:
#   intel:    analysis/investments/entities/, analysis/investments/thesis_checks/
#   selve:    docs/research/, docs/entities/, interpreted/
#   genomics: scripts/curate_*, docs/research/
#
# Install: add to settings.json PostToolUse hooks for Write and Edit.

file=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // .file // ""' 2>/dev/null)
[ -z "$file" ] && exit 0

# Check if file is in a canonical directory
if echo "$file" | grep -qE '(entities/|thesis_checks/|case_library/cases/|docs/research/|interpreted/|curate_)'; then
    echo "SUBSTRATE: You modified a canonical doc. If you haven't already, register assertions and evidence in the knowledge substrate (register_assertion, register_evidence, add_dependency)."
fi

exit 0
