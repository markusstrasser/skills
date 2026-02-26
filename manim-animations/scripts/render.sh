#!/usr/bin/env bash
# Render a Manim scene with smart uv/uvx detection

set -euo pipefail

# Usage
usage() {
    cat <<EOF
Usage: $0 FILE SCENE [QUALITY]

Render a Manim animation scene.

Arguments:
  FILE      Python file containing scene (e.g., hello.py)
  SCENE     Scene class name (e.g., HelloManim)
  QUALITY   Quality preset (default: pql)
            pql - Preview low quality (fast, 480p15, auto-play)
            ql  - Low quality (854x480@15fps)
            qm  - Medium quality (1280x720@30fps)
            qh  - High quality (1920x1080@60fps)
            qk  - 4K quality (3840x2160@60fps)

Examples:
  $0 hello.py HelloManim
  $0 hello.py HelloManim qh
  $0 animations/intro.py IntroScene pql

Environment:
  UV_RUN   Set to 'force' to use uv run even without pyproject.toml
  UV_BIN   Override manim binary path
EOF
    exit 1
}

# Check arguments
if [[ $# -lt 2 ]]; then
    usage
fi

FILE="$1"
SCENE="$2"
QUALITY="${3:-pql}"

# Validate file exists
if [[ ! -f "$FILE" ]]; then
    echo "Error: File not found: $FILE" >&2
    exit 1
fi

# Determine how to run manim
run_manim() {
    local quality_flag="-${QUALITY}"

    # Check if we're in a uv project
    if [[ "${UV_RUN:-}" == "force" ]] || [[ -f "pyproject.toml" ]]; then
        echo "🎬 Rendering with uv run (project mode)..." >&2
        uv run manim "$quality_flag" "$FILE" "$SCENE"
    elif command -v manim &>/dev/null; then
        echo "🎬 Rendering with installed manim..." >&2
        manim "$quality_flag" "$FILE" "$SCENE"
    else
        echo "🎬 Rendering with uvx (ephemeral)..." >&2
        uvx manim "$quality_flag" "$FILE" "$SCENE"
    fi
}

# Run rendering
echo "File:    $FILE"
echo "Scene:   $SCENE"
echo "Quality: $QUALITY"
echo ""

if run_manim; then
    echo ""
    echo "✅ Rendering complete!"

    # Show output location
    output_dir="media/videos/$(basename "$FILE" .py)/${QUALITY}"
    if [[ -d "$output_dir" ]]; then
        echo "📁 Output: $output_dir"
        ls -lh "$output_dir"/*.mp4 2>/dev/null || true
    fi
else
    echo ""
    echo "❌ Rendering failed!" >&2
    exit 1
fi
