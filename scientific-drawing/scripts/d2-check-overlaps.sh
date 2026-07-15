#!/usr/bin/env bash
# d2-check-overlaps.sh - Find overlapping text in D2 SVG output
#
# Usage:
#   ./d2-check-overlaps.sh diagram.svg [threshold]
#
# Arguments:
#   diagram.svg - SVG file to check
#   threshold   - Minimum distance (pixels) before considering overlap (default: 20)
#
# Example:
#   ./d2-check-overlaps.sh output.svg
#   ./d2-check-overlaps.sh output.svg 15

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check arguments
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <svg-file> [threshold]"
    echo "  threshold: minimum distance in pixels (default: 20)"
    exit 1
fi

svg="$1"
threshold="${2:-20}"  # Default 20 pixels

if [[ ! -f "$svg" ]]; then
    echo -e "${RED}Error: File not found: $svg${NC}"
    exit 1
fi

echo -e "${YELLOW}Checking for overlapping labels in: $svg${NC}"
echo -e "${YELLOW}Overlap threshold: ${threshold}px${NC}"
echo ""

# Extract all text positions and labels, then check for overlaps
overlaps_found=0

grep '<text' "$svg" | \
  sed -n 's/.*x="\([^"]*\)" y="\([^"]*\)".*>\([^<]*\)<\/text>/\1 \2 \3/p' | \
  sort -n -k2 | \
  awk -v thresh="$threshold" -v red="$RED" -v nc="$NC" -v yellow="$YELLOW" '
    NR > 1 {
      diff = $2 - prev_y
      abs_diff = (diff < 0) ? -diff : diff

      if (abs_diff < thresh) {
        print red "OVERLAP:" nc " \"" prev_label "\" (y=" prev_y ") and \"" $3 "\" (y=" $2 ")"
        print yellow "  Distance: " abs_diff "px (threshold: " thresh "px)" nc
        print ""
        overlaps++
      }
    }
    { prev_y = $2; prev_label = $3 }
    END {
      exit overlaps
    }
  '

exit_code=$?

echo ""
if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}✓ No overlapping labels found!${NC}"
else
    echo -e "${RED}✗ Found $exit_code overlapping label(s)${NC}"
    echo ""
    echo "To fix overlaps, manually edit the SVG:"
    echo "  1. Find the overlapping <text> elements in the SVG"
    echo "  2. Adjust the y coordinate to separate them"
    echo "  3. Use sed to make the change programmatically"
    echo ""
    echo "Example:"
    echo "  sed 's/\\(<text.*y=\"\\)OLD_Y\\(\".*>LABEL<\\/text>\\)/\\1NEW_Y\\2/' input.svg > output.svg"
fi

exit $exit_code
