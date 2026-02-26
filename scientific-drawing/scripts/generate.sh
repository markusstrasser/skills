#!/usr/bin/env bash
#
# Universal scientific diagram generation script
# Auto-detects format and uses appropriate tool
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat <<EOF
Usage: $(basename "$0") FILE [FORMAT] [OPTIONS]

Generate scientific diagrams using the appropriate tool.

Arguments:
    FILE          Input file (.typ, .asy, .trio.json, .tikz.tex, .d2)
    FORMAT        Output format (pdf, svg, png) [optional, uses defaults]
    OPTIONS       Tool-specific options

Examples:
    $(basename "$0") diagram.typ
    $(basename "$0") diagram.typ pdf
    $(basename "$0") plot.asy svg --no-view
    $(basename "$0") sets.trio.json
    $(basename "$0") circuit.tikz.tex
    $(basename "$0") architecture.d2
    $(basename "$0") architecture.d2 svg --layout=tala -t 101

Supported formats:
    .typ          Typst/CeTZ diagrams
    .asy          Asymptote graphics
    .trio.json    Penrose diagrams
    .tikz.tex     TikZ diagrams (via node-tikzjax)
    .d2           D2 diagrams
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

detect_format() {
    local file="$1"
    case "$file" in
        *.typ)
            echo "typst"
            ;;
        *.asy)
            echo "asymptote"
            ;;
        *.trio.json)
            echo "penrose"
            ;;
        *.tikz.tex|*.tikz)
            echo "tikz"
            ;;
        *.d2)
            echo "d2"
            ;;
        *)
            error "Unknown file format: $file"
            ;;
    esac
}

generate_typst() {
    local input="$1"
    local format="${2:-pdf}"
    shift 2 || true
    local opts=("$@")

    info "Compiling Typst diagram: $input → $format"

    if ! command -v typst &> /dev/null; then
        error "typst not found. Install with: brew install typst"
    fi

    local output="${input%.typ}.${format}"

    typst compile \
        --format "$format" \
        "${opts[@]}" \
        "$input" \
        "$output"

    info "Generated: $output"
}

generate_asymptote() {
    local input="$1"
    local format="${2:-pdf}"
    shift 2 || true
    local opts=("$@")

    info "Compiling Asymptote graphic: $input → $format"

    if ! command -v asy &> /dev/null; then
        error "asymptote not found. Install with: brew install asymptote"
    fi

    # Check for --no-view flag
    local view_flag=""
    for opt in "${opts[@]}"; do
        if [[ "$opt" == "--no-view" ]]; then
            view_flag="-noV"
            opts=("${opts[@]/$opt}")
        fi
    done

    # Default to no view for automation
    if [[ -z "$view_flag" ]]; then
        view_flag="-noV"
    fi

    asy -f "$format" "$view_flag" "${opts[@]}" "$input"

    local output="${input%.asy}.${format}"
    info "Generated: $output"
}

generate_penrose() {
    local input="$1"
    shift
    local output="${input%.trio.json}.svg"

    info "Compiling Penrose diagram: $input → SVG"

    # Check if bunx is available
    if ! command -v bunx &> /dev/null; then
        error "bunx not found. Install bun from: https://bun.sh"
    fi

    # Generate SVG
    bunx @penrose/roger trio "$input" > "$output"

    info "Generated: $output"
}

generate_tikz() {
    local input="$1"
    shift
    local output="${input%.tikz.tex}.svg"
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    info "Rendering TikZ diagram: $input → SVG"

    # Check if the tikz-render script exists
    if [[ ! -f "$script_dir/tikz-render.js" ]]; then
        error "tikz-render.js not found in $script_dir"
    fi

    # Use bun to run the TikZ renderer
    bun "$script_dir/tikz-render.js" "$input" > "$output"

    info "Generated: $output"
}

generate_d2() {
    local input="$1"
    local format="${2:-svg}"
    shift 2 || true
    local opts=("$@")

    info "Compiling D2 diagram: $input → $format"

    if ! command -v d2 &> /dev/null; then
        error "d2 not found. Install with: curl -fsSL https://d2lang.com/install.sh | sh | sh"
    fi

    local output="${input%.d2}.${format}"

    # D2 args: [input] [output] [flags]
    d2 "${opts[@]}" "$input" "$output"

    info "Generated: $output"
}

main() {
    if [[ $# -lt 1 ]]; then
        usage
    fi

    local input="$1"
    shift

    if [[ ! -f "$input" ]]; then
        error "File not found: $input"
    fi

    local format_type
    format_type=$(detect_format "$input")

    case "$format_type" in
        typst)
            generate_typst "$input" "$@"
            ;;
        asymptote)
            generate_asymptote "$input" "$@"
            ;;
        penrose)
            generate_penrose "$input" "$@"
            ;;
        tikz)
            generate_tikz "$input" "$@"
            ;;
        d2)
            generate_d2 "$input" "$@"
            ;;
        *)
            error "Unsupported format: $format_type"
            ;;
    esac
}

main "$@"
