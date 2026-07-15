#!/usr/bin/env bash
# d2-fix-overlap.sh - Fix overlapping label in D2 SVG output
#
# Usage:
#   ./d2-fix-overlap.sh input.svg output.svg label old_y new_y
#
# Arguments:
#   input.svg  - Input SVG file
#   output.svg - Output SVG file
#   label      - Text content of the label to move
#   old_y      - Current y coordinate
#   new_y      - New y coordinate
#
# Example:
#   ./d2-fix-overlap.sh diagram.svg diagram-fixed.svg "revise" "-5.000000" "-32.000000"

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check arguments
if [[ $# -ne 5 ]]; then
    echo "Usage: $0 <input.svg> <output.svg> <label> <old_y> <new_y>"
    echo ""
    echo "Example:"
    echo "  $0 diagram.svg fixed.svg \"revise\" \"-5.000000\" \"-32.000000\""
    exit 1
fi

input="$1"
output="$2"
label="$3"
old_y="$4"
new_y="$5"

if [[ ! -f "$input" ]]; then
    echo -e "${RED}Error: Input file not found: $input${NC}"
    exit 1
fi

echo -e "${YELLOW}Fixing label overlap...${NC}"
echo "  Label: \"$label\""
echo "  Old Y: $old_y"
echo "  New Y: $new_y"
echo ""

# Use sed to replace the y coordinate for the specific label
# Pattern matches: <text x="..." y="OLD_Y" ...>LABEL</text>
sed "s/\(<text [^>]*y=\"\)${old_y}\(\"[^>]*>${label}<\/text>\)/\1${new_y}\2/" "$input" > "$output"

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✓ Fixed SVG saved to: $output${NC}"
    echo ""

    # Verify the change was made
    if grep -q "y=\"${new_y}\"[^>]*>${label}<" "$output"; then
        echo -e "${GREEN}✓ Verified: Label \"$label\" now at y=$new_y${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: Could not verify the change. Check the output file.${NC}"
    fi
else
    echo -e "${RED}✗ Error: Failed to create output file${NC}"
    exit 1
fi
