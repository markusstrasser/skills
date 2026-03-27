#!/usr/bin/env bash
# Safely append a Known Issues entry to a skill's SKILL.md.
# Usage: append-skill-memento.sh <skill-name> "<issue description>"
#
# Appends below the "## Known Issues" header without touching frontmatter
# or other sections. Creates the section if missing.

set -euo pipefail

SKILL_NAME="${1:?Usage: append-skill-memento.sh <skill-name> \"<description>\"}"
DESCRIPTION="${2:?Usage: append-skill-memento.sh <skill-name> \"<description>\"}"
DATE=$(date +%Y-%m-%d)

SKILLS_DIR="${SKILLS_DIR:-$HOME/Projects/skills}"
SKILL_MD="$SKILLS_DIR/$SKILL_NAME/SKILL.md"

if [ ! -f "$SKILL_MD" ]; then
    echo "ERROR: $SKILL_MD not found" >&2
    exit 1
fi

ENTRY="- **[$DATE] $DESCRIPTION**"

# Check if ## Known Issues section exists
if grep -q '^## Known Issues' "$SKILL_MD"; then
    # Find the line number of ## Known Issues
    LINE=$(grep -n '^## Known Issues' "$SKILL_MD" | head -1 | cut -d: -f1)
    # Find the next section header after Known Issues (or EOF)
    NEXT=$(tail -n +"$((LINE + 1))" "$SKILL_MD" | grep -n '^## ' | head -1 | cut -d: -f1)
    if [ -n "$NEXT" ]; then
        # Insert before next section (NEXT is relative to LINE+1)
        INSERT_AT=$((LINE + NEXT - 1))
        # Use ed for atomic insert (avoids sed -i portability issues)
        printf '%s\n' "${INSERT_AT}i" "$ENTRY" "" "." "w" | ed -s "$SKILL_MD" >/dev/null
    else
        # No next section — append at end of file
        printf '\n%s\n' "$ENTRY" >> "$SKILL_MD"
    fi
else
    # Section doesn't exist — append at end of file
    printf '\n## Known Issues\n<!-- Append-only. Session-analyst may suggest additions. -->\n%s\n' "$ENTRY" >> "$SKILL_MD"
fi

echo "Appended to $SKILL_MD: $ENTRY"
