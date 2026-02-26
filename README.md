# Claude Skills - Centralized Repository

This is the canonical location for all Claude Code skills. Individual projects reference these skills via symlinks.

## Structure

```
skills/                    # This repository
├── architect/
├── code-research/
├── computer-use/
├── debug-mcp-servers/
├── diagnostics/
├── llmx-guide/
├── scientific-drawing/
├── session-memory/
└── skill-authoring/
```

**Usage in projects:**

Projects reference these skills via symlinks:
```
your-project/
└── .claude/
    └── skills → /path/to/this/repo
```

## Benefits

1. **Single source of truth** - Update skills once, all projects benefit
2. **No duplication** - Skills evolve independently from projects
3. **Easy maintenance** - Agent improvements to skills propagate automatically
4. **Version control** - Old versions archived with timestamps

## Available Skills

| Skill | Description | Last Updated |
|-------|-------------|--------------|
| `architect` | Tournament-based architectural decision-making | Nov 7, 2025 |
| `code-research` | Codebase exploration and analysis | Nov 6, 2025 |
| `computer-use` | Browser automation and UI control | Nov 6, 2025 |
| `debug-mcp-servers` | MCP server debugging utilities | Nov 7, 2025 |
| `diagnostics` | Error diagnosis and health checks | Nov 6, 2025 |
| `llmx-guide` | LLM provider CLI guide | Nov 7, 2025 |
| `manim-animations` | Mathematical animations and visualizations with Manim | Nov 18, 2025 |
| `scientific-drawing` | TikZ/LaTeX figure generation | Nov 8, 2025 |
| `session-memory` | Semantic search across sessions | Nov 6, 2025 |
| `skill-authoring` | Create and design Agent Skills for Claude Code | Nov 9, 2025 |


## Using in Your Projects

**Option 1: Script (recommended)**

Use the included `link-skill.sh` script for interactive selection:

```bash
cd your-project
/path/to/skills/skill-authoring/scripts/link-skill.sh
```

**Option 2: Manual symlink**

```bash
cd your-project
mkdir -p .claude
ln -s /path/to/skills .claude/skills
```

**Verification:**

```bash
ls .claude/skills/
# Should show: architect, code-research, diagnostics, etc.
```
