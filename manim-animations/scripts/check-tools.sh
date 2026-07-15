#!/usr/bin/env bash
# Check Manim dependencies and setup

set -euo pipefail

echo "🔍 Checking Manim setup..."
echo ""

ERRORS=0

# Check Python
echo "Python:"
if command -v python3 &>/dev/null; then
    version=$(python3 --version)
    echo "  ✅ $version"

    # Check version >= 3.10
    py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if (( $(echo "$py_version < 3.10" | bc -l) )); then
        echo "  ⚠️  Python 3.10+ required, found $py_version"
        ((ERRORS++))
    fi
else
    echo "  ❌ python3 not found"
    ((ERRORS++))
fi
echo ""

# Check uv
echo "uv (Python package manager):"
if command -v uv &>/dev/null; then
    version=$(uv --version)
    echo "  ✅ $version"
else
    echo "  ⚠️  uv not found (recommended)"
    echo "     Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
echo ""

# Check Manim
echo "Manim:"
if command -v manim &>/dev/null; then
    version=$(manim --version 2>&1 || echo "unknown")
    echo "  ✅ Installed globally: $version"
elif [[ -f "pyproject.toml" ]] && grep -q "manim" pyproject.toml; then
    echo "  ✅ Listed in pyproject.toml (use 'uv run manim')"
else
    echo "  ⚠️  Not installed"
    echo "     Install: uv tool install manim"
    echo "     Or run: uvx manim (ephemeral)"
fi
echo ""

# Check FFmpeg
echo "FFmpeg (video encoding):"
if command -v ffmpeg &>/dev/null; then
    version=$(ffmpeg -version | head -n1)
    echo "  ✅ $version"
else
    echo "  ❌ ffmpeg not found"
    echo "     Install (macOS): brew install ffmpeg"
    echo "     Install (Linux): apt-get install ffmpeg"
    ((ERRORS++))
fi
echo ""

# Check Cairo
echo "Cairo (graphics library):"
if python3 -c "import cairo" 2>/dev/null; then
    echo "  ✅ Python cairo bindings found"
else
    echo "  ❌ Python cairo not found"
    echo "     Install (macOS): brew install py3cairo"
    echo "     Install (Linux): apt-get install python3-cairo"
    ((ERRORS++))
fi
echo ""

# Check LaTeX
echo "LaTeX (math rendering):"
if command -v latex &>/dev/null; then
    version=$(latex --version | head -n1)
    echo "  ✅ $version"
else
    echo "  ⚠️  LaTeX not found (required for math equations)"
    echo "     Install (macOS): brew install --cask mactex-no-gui"
    echo "     Install (Linux): apt-get install texlive-full"
    ((ERRORS++))
fi

if command -v pdflatex &>/dev/null; then
    echo "  ✅ pdflatex found"
else
    echo "  ⚠️  pdflatex not found"
fi
echo ""

# Check dvisvgm (for SVG output)
echo "dvisvgm (SVG conversion):"
if command -v dvisvgm &>/dev/null; then
    version=$(dvisvgm --version | head -n1)
    echo "  ✅ $version"
else
    echo "  ⚠️  dvisvgm not found (included in LaTeX distributions)"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $ERRORS -eq 0 ]]; then
    echo "✅ All required dependencies are installed!"
    echo ""
    echo "Get started:"
    echo "  1. Create a scene: cat > hello.py << 'EOF'"
    echo "     from manim import *"
    echo "     class HelloManim(Scene):"
    echo "         def construct(self):"
    echo "             text = Text('Hello, Manim!')"
    echo "             self.play(Write(text))"
    echo "     EOF"
    echo ""
    echo "  2. Render it:"
    echo "     uvx manim -pql hello.py HelloManim"
    echo "     # or: uv run manim -pql hello.py HelloManim"
else
    echo "⚠️  Found $ERRORS missing dependencies"
    echo "Please install the missing components above."
    exit 1
fi
