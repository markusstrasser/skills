#!/usr/bin/env bash
# Live preview for Manim scenes with file watching

set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 FILE SCENE [QUALITY]

Live preview Manim scene with auto-reload on file changes.

Arguments:
  FILE      Python file containing scene
  SCENE     Scene class name
  QUALITY   Quality preset (default: ql for speed)

Examples:
  $0 hello.py HelloManim
  $0 animations/intro.py IntroScene qm
EOF
    exit 1
}

if [[ $# -lt 2 ]]; then
    usage
fi

FILE="$1"
SCENE="$2"
QUALITY="${3:-ql}"

if [[ ! -f "$FILE" ]]; then
    echo "Error: File not found: $FILE" >&2
    exit 1
fi

echo "🔄 Live preview mode"
echo "File:    $FILE"
echo "Scene:   $SCENE"
echo "Quality: $QUALITY"
echo ""
echo "Watching for changes... (Press Ctrl+C to stop)"
echo ""

# Determine manim command
get_manim_cmd() {
    if [[ -f "pyproject.toml" ]]; then
        echo "uv run manim"
    elif command -v manim &>/dev/null; then
        echo "manim"
    else
        echo "uvx manim"
    fi
}

MANIM_CMD=$(get_manim_cmd)

# Initial render
$MANIM_CMD -p${QUALITY} "$FILE" "$SCENE"

# Watch for changes (requires fswatch on macOS or inotifywait on Linux)
if command -v fswatch &>/dev/null; then
    # macOS
    fswatch -o "$FILE" | while read -r; do
        echo "🔄 File changed, re-rendering..."
        $MANIM_CMD -p${QUALITY} "$FILE" "$SCENE"
    done
elif command -v inotifywait &>/dev/null; then
    # Linux
    while inotifywait -e modify "$FILE"; do
        echo "🔄 File changed, re-rendering..."
        $MANIM_CMD -p${QUALITY} "$FILE" "$SCENE"
    done
else
    echo ""
    echo "⚠️  File watching not available"
    echo "Install fswatch (macOS): brew install fswatch"
    echo "Install inotify-tools (Linux): apt-get install inotify-tools"
    echo ""
    echo "Manual mode: Press Enter to re-render, Ctrl+C to quit"

    while true; do
        read -r
        echo "🔄 Re-rendering..."
        $MANIM_CMD -p${QUALITY} "$FILE" "$SCENE"
    done
fi
