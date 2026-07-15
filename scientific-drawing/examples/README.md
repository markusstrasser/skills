# Scientific Drawing Examples

This directory contains example diagrams for each supported tool.

## Structure

```
examples/
├── typst-cetz/      # Typst with CeTZ drawing library
├── asymptote/       # Asymptote 2D and 3D graphics
├── penrose/         # Penrose automatic layout diagrams
└── tikz/            # TikZ diagrams via node-tikzjax
```

## Running Examples

### Generate a single example
```bash
cd ~/Projects/skills/scientific-drawing
./scripts/generate.sh examples/typst-cetz/simple-shapes.typ
./scripts/generate.sh examples/asymptote/3d-surface.asy
./scripts/generate.sh examples/penrose/venn-diagram.trio.json
./scripts/generate.sh examples/tikz/flowchart.tikz.tex
```

### Generate all examples
```bash
./scripts/batch-generate.sh examples/
```

## Examples Overview

### Typst/CeTZ Examples
- `simple-shapes.typ` - Basic shapes and lines
- `plot-function.typ` - Function plotting
- `tree-diagram.typ` - Tree layout

### Asymptote Examples
- `circle-and-label.asy` - 2D shapes with labels
- `3d-surface.asy` - 3D surface plot
- `vector-field.asy` - Vector field visualization

### Penrose Examples
- `venn-diagram.trio.json` - Set theory Venn diagram
- `graph-coloring.trio.json` - Graph visualization
- `category-diagram.trio.json` - Category theory diagram

### TikZ Examples
- `flowchart.tikz.tex` - Basic flowchart
- `neural-network.tikz.tex` - Neural network architecture
- `circuit.tikz.tex` - Electronic circuit diagram
