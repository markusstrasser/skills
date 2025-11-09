# Claude Skills - Centralized Repository

This is the canonical location for all Claude Code skills. Individual projects reference these skills via symlinks.

## Structure

```
Projects/
├── skills/                    # ← Canonical location (this directory)
│   ├── architect/
│   ├── code-research/
│   ├── computer-use/
│   ├── debug-mcp-servers/
│   ├── diagnostics/
│   ├── llmx-guide/
│   ├── scientific-drawing/
│   ├── session-memory/
│   └── skill-authoring/
│
├── evo/skills → ../skills     # ← Symlink
├── publishing/skills → ../skills
├── chats/skills → ../skills
├── demo-app/skills → ../skills
│
└── archived/skills-old/       # ← Old duplicates (archived 2025-11-09)
    ├── evo-skills-20251109/
    └── publishing-skills-20251109/
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
| `scientific-drawing` | TikZ/LaTeX figure generation | Nov 8, 2025 |
| `session-memory` | Semantic search across sessions | Nov 6, 2025 |
| `skill-authoring` | Create and design Agent Skills for Claude Code | Nov 9, 2025 |

## Migration History

**2025-11-09**: Consolidated from distributed skills directories
- Source: `publishing/skills` (newest versions as of Nov 7)
- Migrated projects: `evo`, `publishing`, `chats`, `demo-app`
- Archived: Old duplicates moved to `Projects/archived/skills-old/`

## Adding New Projects

To use these skills in a new project:

```bash
cd /path/to/new-project
ln -s ../skills skills  # If project is in Projects/
# OR
ln -s /Users/alien/Projects/skills skills  # Absolute path
```
