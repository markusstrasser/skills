#!/usr/bin/env bash
#
# Validate D2 diagrams and provide helpful error messages
#

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    cat <<EOF
Usage: $(basename "$0") FILE [FILE...]

Validate D2 diagram files.

Examples:
    $(basename "$0") diagram.d2
    $(basename "$0") *.d2
EOF
    exit 1
}

validate_file() {
    local file="$1"

    echo -e "${YELLOW}Validating:${NC} $file"

    if [[ ! -f "$file" ]]; then
        echo -e "${RED}✗ Error:${NC} File not found: $file"
        return 1
    fi

    if ! command -v d2 &> /dev/null; then
        echo -e "${RED}✗ Error:${NC} d2 not found. Install with: curl -fsSL https://d2lang.com/install.sh | sh | sh"
        return 1
    fi

    # Run d2 validate
    if d2 validate "$file" 2>&1; then
        echo -e "${GREEN}✓ Valid:${NC} $file"
        return 0
    else
        echo -e "${RED}✗ Invalid:${NC} $file"
        return 1
    fi
}

main() {
    if [[ $# -lt 1 ]]; then
        usage
    fi

    local all_valid=true
    local total=0
    local valid=0

    for file in "$@"; do
        total=$((total + 1))
        if validate_file "$file"; then
            valid=$((valid + 1))
        else
            all_valid=false
        fi
        echo ""
    done

    echo "Summary: $valid/$total files valid"

    if $all_valid; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
