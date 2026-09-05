#!/usr/bin/env bash
# Append a skill incident to its dedicated reference without rewriting the router.
# Usage: append-skill-memento.sh <skill-name> "<issue description>"
# The skill must already expose references/known-issues.md; missing targets fail.

set -euo pipefail

SKILL_NAME="${1:?Usage: append-skill-memento.sh <skill-name> \"<description>\"}"
DESCRIPTION="${2:?Usage: append-skill-memento.sh <skill-name> \"<description>\"}"
MEMENTO_DATE=$(date +%Y-%m-%d)

case "$SKILL_NAME" in
    ""|*[!a-z0-9-]*|-*)
        echo "ERROR: skill name must contain lowercase letters, digits or hyphens" >&2
        exit 1
        ;;
esac

SKILLS_DIR="${SKILLS_DIR:-$HOME/Projects/skills}"
SKILL_MD="$SKILLS_DIR/$SKILL_NAME/SKILL.md"
MEMENTO_FILE="$SKILLS_DIR/$SKILL_NAME/references/known-issues.md"

if [ ! -f "$SKILL_MD" ]; then
    echo "ERROR: $SKILL_MD not found" >&2
    exit 1
fi

if [ ! -f "$MEMENTO_FILE" ]; then
    echo "ERROR: $MEMENTO_FILE not found; create it and link it from $SKILL_MD first" >&2
    exit 1
fi

printf '\n- **[%s] %s**\n' "$MEMENTO_DATE" "$DESCRIPTION" >> "$MEMENTO_FILE"
echo "Appended to $MEMENTO_FILE"
