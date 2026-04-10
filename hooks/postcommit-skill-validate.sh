#!/usr/bin/env bash
# Post-commit hook: validate changed skills after commit to ~/Projects/skills/
# Wired via git post-commit hook or Claude Code notification hook.
# Exit 0 always (advisory, not blocking).

set -euo pipefail

SKILLS_DIR="$HOME/Projects/skills"
META_DIR="$HOME/Projects/agent-infra"

# Only run if we're in the skills repo
if [[ "$(git -C "$SKILLS_DIR" rev-parse --show-toplevel 2>/dev/null)" != "$SKILLS_DIR" ]]; then
    exit 0
fi

# Check if any SKILL.md files changed in last commit
changed=$(git -C "$SKILLS_DIR" diff --name-only HEAD~1 HEAD 2>/dev/null | grep 'SKILL\.md' || true)
if [[ -z "$changed" ]]; then
    exit 0
fi

# Run validator on changed skills only
output=$(cd "$META_DIR" && uv run python3 scripts/skill-validator.py --changed-only 2>&1) || true

if echo "$output" | grep -q "error(s) found"; then
    echo "⚠ Skill validation issues after commit:"
    echo "$output"
fi

exit 0
