#!/usr/bin/env bash
#
# Debug and fix common D2 diagram issues
#

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
    cat <<EOF
Usage: $(basename "$0") FILE

Debug D2 diagram and suggest fixes.

This script will:
  1. Validate the D2 file
  2. Try different layout engines
  3. Suggest common fixes for errors
  4. Generate test outputs

Examples:
    $(basename "$0") diagram.d2
EOF
    exit 1
}

check_syntax() {
    local file="$1"

    echo -e "${BLUE}→${NC} Checking syntax..."

    if d2 validate "$file" 2>&1; then
        echo -e "${GREEN}✓${NC} Syntax is valid"
        return 0
    else
        echo -e "${RED}✗${NC} Syntax errors found"
        echo ""
        echo -e "${YELLOW}Common fixes:${NC}"
        echo "  - Check for missing braces: { }"
        echo "  - Verify arrow syntax: ->, <-, <->"
        echo "  - Check for reserved keywords (wrap in quotes)"
        echo "  - Ensure proper indentation"
        return 1
    fi
}

test_layouts() {
    local file="$1"
    local basename="${file%.d2}"

    echo ""
    echo -e "${BLUE}→${NC} Testing layout engines..."

    local layouts=("dagre" "elk" "tala")
    local working_layouts=()

    for layout in "${layouts[@]}"; do
        echo -n "  Testing $layout... "
        if d2 --layout="$layout" "$file" "${basename}-test-${layout}.svg" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            working_layouts+=("$layout")
        else
            echo -e "${RED}✗${NC}"
        fi
    done

    echo ""
    if [[ ${#working_layouts[@]} -gt 0 ]]; then
        echo -e "${GREEN}Working layouts:${NC} ${working_layouts[*]}"
        echo ""
        echo -e "${YELLOW}Tip:${NC} Use --layout flag to specify:"
        for layout in "${working_layouts[@]}"; do
            echo "  d2 --layout=$layout $file output.svg"
        done
    else
        echo -e "${RED}No layouts working!${NC} Check syntax errors above."
    fi

    # Clean up test files
    rm -f "${basename}-test-"*.svg
}

analyze_features() {
    local file="$1"

    echo ""
    echo -e "${BLUE}→${NC} Analyzing features used..."

    # Check for v0.7+ features
    if grep -q "constraint:" "$file"; then
        echo -e "${YELLOW}!${NC} SQL tables detected - use ${GREEN}--layout=tala${NC} or ${GREEN}--layout=elk${NC}"
    fi

    if grep -q "|md" "$file"; then
        echo -e "${GREEN}✓${NC} Markdown labels found (v0.7+ feature)"
    fi

    if grep -q "legend:" "$file"; then
        echo -e "${GREEN}✓${NC} Legend found (v0.7+ feature)"
    fi

    if grep -q "suspend:" "$file"; then
        echo -e "${GREEN}✓${NC} suspend/unsuspend found (v0.7+ feature)"
    fi

    # Count connections
    local conn_count
    conn_count=$(grep -c -- '->' "$file" 2>/dev/null || echo "0")
    echo -e "${BLUE}→${NC} Connections: $conn_count"

    # Count shapes
    local shape_count
    shape_count=$(grep -c 'shape:' "$file" 2>/dev/null || echo "0")
    echo -e "${BLUE}→${NC} Explicit shapes: $shape_count"
}

suggest_improvements() {
    local file="$1"

    echo ""
    echo -e "${BLUE}→${NC} Suggestions for improvement..."

    # Check if using default theme
    echo -e "${YELLOW}Themes:${NC}"
    echo "  Try different themes with: d2 -t <theme_id> $file output.svg"
    echo "  List themes with: d2 themes"
    echo "  Recommended for papers: -t 0 (Neutral), -t 3 (Cool classics)"

    # Check for legend
    if ! grep -q "legend:" "$file"; then
        echo ""
        echo -e "${YELLOW}Consider adding a legend:${NC}"
        cat <<'EOF'
  legend: {
    component1: {label: "Description"; style.fill: color1}
    component2: {label: "Description"; style.fill: color2}
  }
EOF
    fi

    # Check for markdown usage
    if ! grep -q "|md" "$file"; then
        echo ""
        echo -e "${YELLOW}Consider using markdown labels (v0.7+):${NC}"
        cat <<'EOF'
  node: |md
    ## Title
    - Point 1
    - Point 2

    Math: $f(x) = x^2$
  |
EOF
    fi
}

main() {
    if [[ $# -ne 1 ]]; then
        usage
    fi

    local file="$1"

    if [[ ! -f "$file" ]]; then
        echo -e "${RED}Error:${NC} File not found: $file"
        exit 1
    fi

    if ! command -v d2 &> /dev/null; then
        echo -e "${RED}Error:${NC} d2 not found. Install with: curl -fsSL https://d2lang.com/install.sh | sh | sh"
        exit 1
    fi

    echo -e "${GREEN}D2 Diagram Debugger${NC}"
    echo "File: $file"
    echo ""

    check_syntax "$file"
    test_layouts "$file"
    analyze_features "$file"
    suggest_improvements "$file"

    echo ""
    echo -e "${GREEN}Done!${NC}"
}

main "$@"
