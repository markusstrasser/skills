#!/usr/bin/env bash
#
# Batch generate all scientific diagrams in a directory
#

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    cat <<EOF
Usage: $(basename "$0") DIRECTORY [FORMAT]

Batch generate all scientific diagrams in a directory.

Arguments:
    DIRECTORY     Directory containing diagram source files
    FORMAT        Output format (pdf, svg, png) [optional]

Examples:
    $(basename "$0") ./figures/
    $(basename "$0") ./paper-diagrams/ pdf

Processes:
    - .typ files (Typst/CeTZ)
    - .asy files (Asymptote)
    - .trio.json files (Penrose)
    - .tikz.tex files (TikZ)
EOF
    exit 1
}

error() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

info() {
    echo -e "${GREEN}→${NC} $1"
}

warn() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

main() {
    if [[ $# -lt 1 ]]; then
        usage
    fi

    local dir="$1"
    local format="${2:-}"

    if [[ ! -d "$dir" ]]; then
        error "Directory not found: $dir"
    fi

    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local generate_script="$script_dir/generate.sh"

    if [[ ! -f "$generate_script" ]]; then
        error "generate.sh not found in $script_dir"
    fi

    info "Batch generating diagrams in: $dir"
    echo ""

    local count=0
    local failed=0

    # Process each type of file
    for ext in "typ" "asy" "trio.json" "tikz.tex"; do
        while IFS= read -r -d '' file; do
            echo -e "${GREEN}Processing:${NC} $(basename "$file")"

            if [[ -n "$format" ]]; then
                if bash "$generate_script" "$file" "$format"; then
                    ((count++))
                else
                    warn "Failed to generate: $file"
                    ((failed++))
                fi
            else
                if bash "$generate_script" "$file"; then
                    ((count++))
                else
                    warn "Failed to generate: $file"
                    ((failed++))
                fi
            fi
            echo ""
        done < <(find "$dir" -name "*.$ext" -print0)
    done

    echo ""
    info "Batch generation complete!"
    echo -e "  ${GREEN}✓${NC} Generated: $count"

    if [[ $failed -gt 0 ]]; then
        echo -e "  ${RED}✗${NC} Failed: $failed"
        exit 1
    fi
}

main "$@"
