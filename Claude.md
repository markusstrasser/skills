# Skills Project - Claude Code Instructions

This repository contains custom Claude Code skills for various tasks.

## Project Structure

```
skills/
├── Claude.md                    # This file - project instructions
├── skill-authoring/             # Skill authoring guide and templates
│   ├── SKILL.md                # Main authoring documentation
│   ├── EXAMPLES.md             # Example skills
│   └── TEMPLATES.md            # Skill templates
├── scientific-drawing/          # Scientific diagram generation
│   ├── SKILL.md                # Main skill documentation
│   ├── examples/               # Tool-specific examples
│   │   ├── d2/                 # D2 diagram examples
│   │   ├── typst-cetz/         # Typst/CeTZ examples
│   │   ├── asymptote/          # Asymptote examples
│   │   ├── penrose/            # Penrose examples
│   │   └── tikz/               # TikZ examples
│   └── scripts/                # Helper scripts
│       ├── generate.sh         # Universal diagram generator
│       ├── check-tools.sh      # Verify tool installations
│       ├── d2-validate.sh      # Validate D2 diagrams
│       └── d2-fix.sh           # Debug D2 diagrams
└── [other-skills]/             # Add more skills here
```

## Adding New Skills

When adding a new skill to this repository:

1. **Create skill directory:**
   ```bash
   mkdir -p new-skill-name
   ```

2. **Follow skill-authoring guide:**
   - Read `skill-authoring/SKILL.md` for best practices
   - Use templates from `skill-authoring/TEMPLATES.md`
   - See examples in `skill-authoring/EXAMPLES.md`

3. **Required components:**
   - `SKILL.md` with valid frontmatter (name, description)
   - Clear instructions and examples
   - Any necessary scripts in `scripts/` subdirectory
   - Example files in `examples/` subdirectory

4. **Validation checklist:**
   - [ ] Frontmatter uses valid YAML syntax
   - [ ] Name is lowercase with hyphens (max 64 chars)
   - [ ] Description includes WHAT and WHEN (max 1024 chars)
   - [ ] Description contains trigger words users would say
   - [ ] Instructions are clear and step-by-step
   - [ ] Dependencies are explicitly documented
   - [ ] Examples show realistic usage

5. **Link skill for development:**
   ```bash
   # Use the interactive linking script
   ./skill-authoring/scripts/link-skill.sh
   ```

## Skill Development Guidelines

### Progressive Disclosure
- Keep `SKILL.md` concise
- Move detailed content to separate files (REFERENCE.md, EXAMPLES.md, etc.)
- Claude only reads additional files when needed

### Tool Restrictions
Use `allowed-tools` in frontmatter for focused skills:
```yaml
allowed-tools: Read, Grep, Glob  # Read-only skill
```

### Testing
Test skill discovery with queries matching your trigger words:
```bash
# Start Claude Code and ask questions that should trigger your skill
claude
```

## Scientific Drawing Skill

The `scientific-drawing` skill supports multiple diagram tools:

- **Typst/CeTZ** - Modern 2D diagrams and plots
- **Asymptote** - 3D graphics and technical drawings
- **Penrose** - Automatic layout from mathematical notation
- **TikZ** - Flowcharts, circuits, complex diagrams
- **D2** - Modern architecture diagrams, ERDs, flowcharts

### Quick Start
```bash
cd scientific-drawing

# Check installations
./scripts/check-tools.sh

# Generate diagrams
./scripts/generate.sh examples/d2/system-architecture.d2
./scripts/generate.sh examples/asymptote/circle-and-label.asy
./scripts/generate.sh examples/typst-cetz/simple-shapes.typ

# Validate D2 diagrams
./scripts/d2-validate.sh diagram.d2

# Debug D2 diagrams
./scripts/d2-fix.sh diagram.d2
```

## D2 Reference

The D2 source repository is available at `~/Projects/best/d2` for reference.

### D2 Version 0.7+ Features
- Icons on connections
- Rich content labels (markdown, LaTeX, code)
- Legends
- SQL tables with row-level connections
- suspend/unsuspend for reusable models
- Glob filtering by node properties

### D2 Best Practices
1. Use appropriate layout engine:
   - `dagre` (default) - General diagrams
   - `tala` - Architecture diagrams, SQL tables
   - `elk` - Hierarchical structures

2. Validate before rendering:
   ```bash
   d2 validate diagram.d2
   ```

3. Use themes for professional output:
   ```bash
   d2 themes              # List themes
   d2 -t 0 diagram.d2     # Neutral (good for papers)
   d2 -t 101 diagram.d2   # Grape Soda
   ```

## Resources

- [Claude Code Skills Documentation](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
- [D2 Documentation](https://d2lang.com)
- [Typst Documentation](https://typst.app/docs/)
- [Asymptote Gallery](https://asymptote.sourceforge.io/gallery/)
- [Penrose Documentation](https://penrose.cs.cmu.edu/docs/)
