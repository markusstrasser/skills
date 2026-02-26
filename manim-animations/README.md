# Manim Animations Skill

Claude Code skill for creating mathematical animations using Manim.

## Quick Start

This skill is automatically available in projects that link to the skills directory.

**In your manimations project:**
```bash
cd ~/Projects/manimations

# The skill is already linked via .claude/skills symlink
# Just ask Claude to create animations!
```

## Example Usage

Ask Claude:
- "Create a Manim animation showing the quadratic formula"
- "Animate a function transformation from x² to -x²"
- "Make a 3D visualization of a paraboloid"
- "Show me how to plot sine and cosine together"

## What This Skill Provides

1. **Smart uv/uvx integration** - Automatically uses the right tool
2. **Helper scripts** - render.sh, preview.sh, check-tools.sh
3. **Templates** - Pre-built examples for common patterns
4. **Best practices** - Following Manim community standards

## Directory Structure

```
manim-animations/
├── SKILL.md              # Main skill (read by Claude)
├── README.md             # This file
├── scripts/
│   ├── render.sh         # Smart rendering with uv/uvx
│   ├── preview.sh        # Live preview with file watching
│   └── check-tools.sh    # Dependency checker
├── templates/
│   ├── basic-scene.py    # Simple shapes and text
│   ├── math-equation.py  # LaTeX equations
│   ├── graph-plot.py     # Function plotting
│   └── 3d-scene.py       # 3D visualizations
└── examples/
    └── README.md         # Examples documentation
```

## Tools Used

- **uv/uvx**: Modern Python package management
- **Manim**: Mathematical animation engine
- **LaTeX**: Math typesetting
- **FFmpeg**: Video encoding

## Rendering Commands

```bash
# Quick preview (fast)
uvx manim -pql myfile.py MyScene

# High quality
uvx manim -qh myfile.py MyScene

# With project dependencies
cd ~/Projects/manimations
uv run manim -pql myfile.py MyScene
```

## Learning Resources

- [Manim Docs](https://docs.manim.community/)
- [3Blue1Brown](https://www.youtube.com/c/3blue1brown) - Original creator
- Templates in `templates/` directory

## Skill Activation

This skill activates when Claude detects:
- Mentions of "manim", "animations", "mathematical visualizations"
- "3Blue1Brown-style videos"
- "animate equations", "explain math visually"
- Working with `.py` files containing Manim code

The skill uses these tools: Bash, Read, Write, Edit, Grep, Glob
