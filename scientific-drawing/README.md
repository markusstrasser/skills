# Scientific Drawing Skill

A comprehensive Claude Code skill for generating scientific diagrams, figures, and illustrations using Typst/CeTZ, Asymptote, Penrose, or TikZ.

## Installation

```bash
cd ~/Projects/skills/scientific-drawing

# Install Node/JS dependencies
bun install

# Verify all tools are installed
./scripts/check-tools.sh
```

## Quick Start

```bash
# Generate a diagram (auto-detects format)
./scripts/generate.sh examples/asymptote/circle-and-label.asy

# Batch generate all examples
./scripts/batch-generate.sh examples/

# Run tests
bun test
```

## Tool Selection

- **Typst + CeTZ** - Modern 2D diagrams, plots, charts (fast compilation)
- **Asymptote** - 3D graphics, precise technical drawings, scientific visualizations
- **Penrose** - Automatic layout from mathematical notation (set theory, graphs)
- **TikZ** - Flowcharts, org charts, circuits (largest ecosystem)

## Project Structure

```
scientific-drawing/
├── SKILL.md                 # Main skill documentation
├── README.md                # This file
├── package.json             # Node dependencies
├── scripts/
│   ├── generate.sh          # Universal diagram generator
│   ├── batch-generate.sh    # Batch processing
│   ├── check-tools.sh       # Verify tool installation
│   ├── tikz-render.js       # TikZ → SVG renderer
│   └── test.ts              # Test suite
├── examples/
│   ├── typst-cetz/         # Typst examples
│   ├── asymptote/          # Asymptote examples
│   ├── penrose/            # Penrose examples
│   └── tikz/               # TikZ examples
└── templates/               # Reusable templates
```

## Usage Examples

### Asymptote (3D Graphics)

```bash
# Create a 3D surface plot
cat > plot3d.asy <<'EOF'
import graph3;
size(200);

currentprojection=orthographic(4,2,3);

draw(surface(f=(x,y){return x^2+y^2;},
    (-1,-1), (1,1), nx=20, ny=20),
    lightblue+opacity(0.7));

axes3("$x$", "$y$", "$z$");
EOF

./scripts/generate.sh plot3d.asy pdf
```

### TikZ (Flowcharts)

```bash
# Generate from TikZ file
./scripts/generate.sh diagram.tikz.tex
```

### Penrose (Set Theory)

```bash
# Create trio files (domain, substance, style)
# Then generate:
bunx @penrose/roger trio diagram.trio.json > output.svg
```

## Concept Diagrams

Example concept diagrams have been generated in `~/Downloads/` including:

1. **01-nested-search-levels.pdf** - Creation as nested search (macro/meso/micro)
2. **02-conways-law-org-to-system.svg** - Conway's Law visualization
3. ... (more to come)

Each diagram includes a caption explaining the concept being illustrated.

## CI/CD Integration

```yaml
# .github/workflows/generate-figures.yml
- uses: typst-community/setup-typst@v4
- uses: oven-sh/setup-bun@v1
- run: ./skills/scientific-drawing/scripts/batch-generate.sh figures/
```

## Testing

```bash
# Run full test suite
bun test

# Check tool availability
./scripts/check-tools.sh
```

## Tool Versions

- Typst: 0.14.0
- Asymptote: 3.05
- Bun: 1.3.1
- @penrose/core: 3.3.0
- node-tikzjax: 1.0.3

## Best Practices

1. **Version control sources** (.typ, .asy, .trio.json), not outputs
2. **Use appropriate tool** for each diagram type
3. **Automate generation** in CI/CD pipelines
4. **Reproducible builds** with fixed timestamps and fonts
5. **Cache outputs** when possible

## Troubleshooting

### Typst/CeTZ coordinate errors

Update to latest CeTZ version or check coordinate syntax in [CeTZ docs](https://typst.app/universe/package/cetz/).

### Asymptote viewer opens automatically

Add to `~/.asy/config.asy`:
```asymptote
import settings;
settings.interactiveView=false;
settings.batchView=false;
```

### TikZ rendering fails

Check node-tikzjax is installed:
```bash
bun install node-tikzjax
```

### Penrose optimization doesn't converge

Try different variation seeds in trio.json.

## References

- [Typst Documentation](https://typst.app/docs/)
- [CeTZ Package](https://typst.app/universe/package/cetz/)
- [Asymptote Gallery](https://asymptote.sourceforge.io/gallery/)
- [Penrose Documentation](https://penrose.cs.cmu.edu/docs/)
- [TikZ Manual](https://tikz.dev/)

## License

This skill is part of the Claude Code skills ecosystem.
