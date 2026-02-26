#!/usr/bin/env bash
#
# Check if all scientific drawing tools are installed
#

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_cmd() {
    local cmd="$1"
    local install_hint="$2"

    if command -v "$cmd" &> /dev/null; then
        local version
        version=$($3 2>&1 || echo "unknown")
        echo -e "${GREEN}✓${NC} $cmd: $version"
        return 0
    else
        echo -e "${RED}✗${NC} $cmd: not found"
        echo -e "  ${YELLOW}Install:${NC} $install_hint"
        return 1
    fi
}

main() {
    echo "Checking scientific drawing tools..."
    echo ""

    local all_ok=true

    # Check Typst
    if ! check_cmd "typst" "brew install typst" "typst --version"; then
        all_ok=false
    fi

    # Check Asymptote
    if ! check_cmd "asy" "brew install asymptote" "asy --version | head -1"; then
        all_ok=false
    fi

    # Check D2
    if ! check_cmd "d2" "curl -fsSL https://d2lang.com/install.sh | sh | sh" "d2 --version"; then
        all_ok=false
    fi

    # Check Bun (for Penrose and TikZ)
    if ! check_cmd "bun" "curl -fsSL https://bun.sh/install | bash" "bun --version"; then
        all_ok=false
    fi

    # Check bunx
    if ! check_cmd "bunx" "bun is already installed, bunx should be available" "bunx --version"; then
        all_ok=false
    fi

    echo ""

    # Check Node packages
    echo "Checking Node packages..."
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local project_dir="$(dirname "$script_dir")"

    if [[ -f "$project_dir/package.json" ]]; then
        if [[ -d "$project_dir/node_modules" ]]; then
            echo -e "${GREEN}✓${NC} node_modules exists"

            # Check specific packages
            if [[ -d "$project_dir/node_modules/node-tikzjax" ]]; then
                echo -e "${GREEN}✓${NC} node-tikzjax installed"
            else
                echo -e "${RED}✗${NC} node-tikzjax not installed"
                echo -e "  ${YELLOW}Run:${NC} cd $project_dir && bun install"
                all_ok=false
            fi
        else
            echo -e "${RED}✗${NC} node_modules not found"
            echo -e "  ${YELLOW}Run:${NC} cd $project_dir && bun install"
            all_ok=false
        fi
    else
        echo -e "${YELLOW}!${NC} package.json not found"
        echo -e "  ${YELLOW}Run:${NC} cd $project_dir && bun init"
    fi

    echo ""

    if $all_ok; then
        echo -e "${GREEN}✓${NC} All tools are installed!"
        return 0
    else
        echo -e "${RED}✗${NC} Some tools are missing. Install them and try again."
        return 1
    fi
}

main "$@"
