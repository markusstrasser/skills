---
name: scientific-drawing
description: Generate scientific diagrams, figures, and illustrations using Typst/CeTZ, Asymptote, Penrose, or TikZ. Use when creating mathematical diagrams, technical illustrations, scientific figures, vector graphics, 3D plots, or converting mathematical notation to visual representations. Automatically selects the best tool based on the task.
allowed-tools: Bash, Read, Write, Grep, Glob
---

# Scientific Drawing & Diagram Generation

Comprehensive skill for generating high-quality scientific diagrams using the right tool for the job: Typst/CeTZ, Asymptote, Penrose, or TikZ via node-tikzjax.

## Tool Selection Guide

### When to use each tool

**Typst + CeTZ** - Modern, Fast, Great for Papers
- 2D diagrams with TikZ-like API
- Plotting and charts
- Tree layouts
- Integration with Typst documents
- Millisecond compilation
- ✅ Use for: Quick iterations, modern workflows, integrated documents

**Asymptote** - Powerful 3D Graphics
- 3D scientific visualizations
- Technical drawings with precise coordinates
- LaTeX-quality output
- PostScript/PDF/SVG export
- ✅ Use for: 3D graphics, precise technical drawings, publication figures

**Penrose** - Automatic Layout from Math Notation
- Mathematical diagrams from notation
- Set theory, category theory diagrams
- Graph visualization
- Automatic constraint-based layout
- ✅ Use for: Abstract math diagrams, when you want separation of content/style

**TikZ (via node-tikzjax)** - Most Flexible, Largest Ecosystem
- Circuit diagrams, flowcharts, mind maps
- Huge library ecosystem
- Web rendering via JavaScript
- LaTeX integration
- ✅ Use for: Complex diagrams with existing TikZ code, specialized diagrams

## Prerequisites

### Installation

```bash
# Typst (for CeTZ)
brew install typst  # macOS
# or: curl -fsSL https://typst.app/install.sh | sh

# Asymptote
brew install asymptote  # macOS
# or: apt-get install asymptote  # Linux

# Node dependencies (Penrose, TikZ)
cd ~/Projects/skills/scientific-drawing
bun install

# Python dependencies (if needed for automation)
uv pip install pypdf pdfplumber
```

Check installations:
```bash
./scripts/check-tools.sh
```

## Quick Start

### Helper Scripts

All tools are accessible through unified helper scripts:

```bash
# Generate diagram (auto-detects type)
./scripts/generate.sh input.typ          # Typst/CeTZ
./scripts/generate.sh input.asy          # Asymptote
./scripts/generate.sh input.trio.json    # Penrose
./scripts/generate.sh input.tikz.tex     # TikZ

# Specify output format
./scripts/generate.sh input.typ pdf
./scripts/generate.sh input.asy svg --no-view

# Batch process
./scripts/batch-generate.sh ./diagrams/

# Interactive preview
./scripts/preview.sh input.typ  # Opens watch mode
```

## Detailed Tool Usage

### Typst + CeTZ

CeTZ provides a drawing library for Typst with an API inspired by TikZ.

**Basic diagram:**
```typst
#import "@preview/cetz:0.2.2": canvas, draw, plot

#canvas({
  import draw: *

  // Simple shapes
  circle((0, 0), radius: 1, fill: blue.lighten(80%))
  line((0, 0), (2, 1), stroke: red)

  // With labels
  content((1, 0.5), [Hello])
})
```

**Plotting:**
```typst
#import "@preview/cetz:0.2.2": canvas, plot

#canvas({
  plot.plot(size: (8, 6),
    x-label: [Time],
    y-label: [Value],
    {
      plot.add(
        domain: (0, 2*calc.pi),
        x => calc.sin(x)
      )
    }
  )
})
```

**Compile:**
```bash
typst compile diagram.typ diagram.pdf
# or use helper
./scripts/generate.sh diagram.typ
```

See [examples/typst-cetz/](examples/typst-cetz/) for more examples.

### Asymptote

Powerful vector graphics language with 3D support.

**Basic 2D:**
```asymptote
import graph;
size(200);

draw(unitcircle, blue);
dot((0,0), red);

label("Origin", (0,0), S);
```

**3D Graphics:**
```asymptote
import graph3;
size(200);

currentprojection=orthographic(4,2,3);

// Draw 3D surface
draw(surface(f=(x,y){return x^2+y^2;},
    (-1,-1), (1,1), nx=20, ny=20),
    lightblue+opacity(0.7));

// Add axes
axes3("$x$", "$y$", "$z$");
```

**Compile (non-interactive):**
```bash
asy -f pdf -noV diagram.asy
# or use helper
./scripts/generate.sh diagram.asy pdf --no-view
```

**Configuration for automation:**
Create `~/.asy/config.asy`:
```asymptote
import settings;
settings.outformat="pdf";
settings.interactiveView=false;
settings.batchView=false;
settings.render=4;
```

See [examples/asymptote/](examples/asymptote/) for more examples.

### Penrose

Automatically generate diagrams from mathematical notation.

**Trio structure:**
Three files define a diagram:

1. **Domain** (`.domain`) - Type definitions
2. **Substance** (`.substance`) - Declarations
3. **Style** (`.style`) - Visual rules

**Example - Set theory:**

`setTheory.domain`:
```
type Set
predicate Subset(Set, Set)
predicate Intersect(Set, Set)
```

`diagram.substance`:
```
Set A, B, C
Subset(A, B)
Intersect(B, C)
```

`venn.style`:
```
forall Set x {
    x.shape = Circle {
        strokeWidth: 2
    }
}

forall Set A; Set B
where Subset(A, B) {
    ensure contains(B.shape, A.shape)
}
```

**Trio JSON:**
```json
{
  "domain": "./setTheory.domain",
  "style": ["./venn.style"],
  "substance": "./diagram.substance",
  "variation": "seed-123"
}
```

**Generate:**
```bash
bunx @penrose/roger trio diagram.trio.json > output.svg
# or use helper
./scripts/generate.sh diagram.trio.json
```

**Programmatic usage:**
```javascript
import { compile, optimize, toSVG } from "@penrose/core";

const trio = {
  domain: "type Set\npredicate Subset(Set,Set)",
  substance: "Set A, B\nSubset(A, B)",
  style: "forall Set x { x.shape = Circle { } }"
};

const compiled = await compile(trio);
const optimized = optimize(compiled.value);
const svg = await toSVG(optimized.value, async () => undefined);
```

See [examples/penrose/](examples/penrose/) for more examples.

### TikZ (via node-tikzjax)

Use TikZ with JavaScript/Node rendering.

**Basic usage:**
```javascript
import tikzjax from 'node-tikzjax';

const tikzCode = `
\\begin{document}
\\begin{tikzpicture}
  \\draw[thick, ->] (0,0) -- (2,0) node[right] {$x$};
  \\draw[thick, ->] (0,0) -- (0,2) node[above] {$y$};
  \\draw[color=red] (0,0) circle (1cm);
\\end{tikzpicture}
\\end{document}
`;

const svg = await tikzjax.default(tikzCode);
console.log(svg);  // SVG output
```

**With helper script:**
```bash
./scripts/tikz-render.js diagram.tikz.tex > output.svg
# or use unified helper
./scripts/generate.sh diagram.tikz.tex
```

**Complex diagrams:**
```tex
\\begin{document}
\\begin{tikzpicture}[domain=0:4]
  \\draw[very thin,color=gray] (-0.1,-1.1) grid (3.9,3.9);
  \\draw[->] (-0.2,0) -- (4.2,0) node[right] {$x$};
  \\draw[->] (0,-1.2) -- (0,4.2) node[above] {$f(x)$};
  \\draw[color=red] plot (\\x,\\x) node[right] {$f(x) =x$};
  \\draw[color=blue] plot (\\x,{sin(\\x r)}) node[right] {$f(x) = \\sin x$};
\\end{tikzpicture}
\\end{document}
```

See [examples/tikz/](examples/tikz/) for more examples.

## Scripts Reference

### generate.sh
Universal generation script - auto-detects format:
```bash
./scripts/generate.sh FILE [FORMAT] [OPTIONS]

# Examples:
./scripts/generate.sh diagram.typ pdf
./scripts/generate.sh plot.asy svg --no-view
./scripts/generate.sh sets.trio.json
./scripts/generate.sh circuit.tikz.tex
```

### batch-generate.sh
Process all diagrams in a directory:
```bash
./scripts/batch-generate.sh DIRECTORY [FORMAT]

# Example:
./scripts/batch-generate.sh ./paper-figures/ pdf
```

### preview.sh
Live preview with auto-reload:
```bash
./scripts/preview.sh FILE

# Supports: .typ, .asy (with polling)
```

### convert.sh
Convert between formats:
```bash
./scripts/convert.sh INPUT.svg OUTPUT.pdf
./scripts/convert.sh INPUT.pdf OUTPUT.png --dpi 300
```

### check-tools.sh
Verify all tools are installed:
```bash
./scripts/check-tools.sh
```

## Advanced Workflows

### CI/CD Integration

```yaml
# .github/workflows/generate-figures.yml
name: Generate Figures
on: [push]
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: typst-community/setup-typst@v4
      - uses: oven-sh/setup-bun@v1

      - name: Install dependencies
        run: |
          sudo apt-get install -y asymptote
          cd skills/scientific-drawing && bun install

      - name: Generate all figures
        run: ./skills/scientific-drawing/scripts/batch-generate.sh figures/

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: figures
          path: figures/*.pdf
```

### Makefile Integration

```makefile
# Automatic figure generation
TYPST_FIGS := $(wildcard figures/*.typ)
ASY_FIGS := $(wildcard figures/*.asy)
PENROSE_FIGS := $(wildcard figures/*.trio.json)

PDFS := $(TYPST_FIGS:.typ=.pdf) $(ASY_FIGS:.asy=.pdf)
SVGS := $(PENROSE_FIGS:.trio.json=.svg)

all: $(PDFS) $(SVGS)

%.pdf: %.typ
	typst compile $< $@

%.pdf: %.asy
	asy -f pdf -noV $<

%.svg: %.trio.json
	bunx @penrose/roger trio $< > $@

clean:
	rm -f $(PDFS) $(SVGS)

.PHONY: all clean
```

### Reproducible Builds

```bash
# Typst: Fixed timestamps and fonts
typst compile \
  --ignore-system-fonts \
  --font-path ./fonts \
  --creation-timestamp $(git log -1 --format=%ct) \
  diagram.typ

# Asymptote: Configured output
asy -f pdf -noV -render 8 diagram.asy

# Penrose: Fixed variation seed
# In trio.json: "variation": "fixed-seed-123"
```

### Docker Usage

```dockerfile
FROM ubuntu:24.04

# Install all tools
RUN apt-get update && apt-get install -y \
    curl \
    asymptote \
    && curl -fsSL https://typst.app/install.sh | sh

# Install bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"

WORKDIR /work
COPY package.json bun.lock ./
RUN bun install

# Generate diagrams
CMD ["./scripts/batch-generate.sh", "/work/diagrams/"]
```

## Common Patterns

### Mathematical Notation

**Typst:**
```typst
$ f(x) = sum_(i=0)^n a_i x^i $
```

**Asymptote:**
```asymptote
label("$\\sum_{i=0}^n a_i x^i$", (0,0));
```

**TikZ:**
```tex
\\node at (0,0) {$\\sum_{i=0}^n a_i x^i$};
```

### Data Visualization

**From CSV (Typst):**
```typst
#let data = csv("data.csv")
#import "@preview/cetz:0.2.2": canvas, plot

#canvas({
  plot.plot({
    plot.add(data.map(row => (
      float(row.at(0)),
      float(row.at(1))
    )))
  })
})
```

**From Arrays (Asymptote):**
```asymptote
import graph;
real[] x = {0, 1, 2, 3, 4};
real[] y = {0, 1, 4, 9, 16};
draw(graph(x, y), red);
```

### Export Formats

```bash
# PDF (publication quality)
./scripts/generate.sh diagram.typ pdf
./scripts/generate.sh diagram.asy pdf

# SVG (web, editing)
./scripts/generate.sh diagram.typ svg
./scripts/generate.sh diagram.trio.json  # Always SVG

# PNG (raster, presentations)
./scripts/generate.sh diagram.typ png --ppi 300
./scripts/generate.sh diagram.asy png --dpi 300

# Multiple formats
./scripts/generate.sh diagram.typ pdf,svg,png
```

## Templates

See [templates/](templates/) for:
- `paper-figure.typ` - Scientific paper figure template
- `3d-plot.asy` - 3D visualization template
- `set-theory.trio.json` - Penrose diagram template
- `flowchart.tikz.tex` - TikZ flowchart template
- `neural-network.tikz.tex` - Neural network diagram
- `circuit.tikz.tex` - Circuit diagram

## Testing

Run the test suite:
```bash
cd scripts
bun test
```

Tests verify:
- Tool installations
- Basic compilation for each format
- Helper script functionality
- Format conversions
- Error handling

## Troubleshooting

### Typst compilation fails

```bash
# Check installation
typst --version

# Verify CeTZ package
typst fonts  # Should show available fonts
```

### Asymptote won't run headless

```bash
# Build with offscreen support
./configure --enable-offscreen
make
sudo make install

# Or configure for batch mode
echo 'import settings; settings.interactiveView=false; settings.batchView=false;' > ~/.asy/config.asy
```

### Penrose optimization fails

Try different variation seeds or simplify constraints:
```json
{
  "variation": "try-different-seed"
}
```

### Node/Bun dependencies

```bash
# Reinstall
rm -rf node_modules bun.lock
bun install
```

## Best Practices

1. **Choose the right tool** - Use the tool selection guide above
2. **Version control sources** - Commit `.typ`, `.asy`, `.trio.json`, not PDFs
3. **Automate generation** - Use Makefiles or scripts in CI/CD
4. **Use templates** - Start from templates directory
5. **Reproducible builds** - Fix timestamps, fonts, seeds
6. **Separate content from style** - Especially with Penrose
7. **Test across platforms** - Use Docker for consistency
8. **Cache when possible** - Only regenerate changed diagrams

## Real-World Examples

### Example 1: Conference Paper Figures

```bash
# Generate all paper figures
./scripts/batch-generate.sh paper-figures/ pdf

# Individual figures
./scripts/generate.sh paper-figures/architecture.typ pdf
./scripts/generate.sh paper-figures/results-3d.asy pdf
./scripts/generate.sh paper-figures/category-diagram.trio.json
```

### Example 2: Interactive Documentation

```bash
# Generate SVGs for web
./scripts/batch-generate.sh docs/diagrams/ svg

# Embed in HTML
cat docs/index.html
```

### Example 3: Presentation Slides

```bash
# High-resolution PNGs
./scripts/generate.sh slides/diagram1.typ png --ppi 300
./scripts/generate.sh slides/diagram2.asy png --dpi 300
```

## References

### Documentation
- [Typst Documentation](https://typst.app/docs/)
- [CeTZ Package](https://typst.app/universe/package/cetz/)
- [Asymptote Documentation](https://asymptote.sourceforge.io/)
- [Asymptote Gallery](https://asymptote.sourceforge.io/gallery/)
- [Penrose Documentation](https://penrose.cs.cmu.edu/docs/)
- [Penrose Examples](https://github.com/penrose/penrose/tree/main/packages/examples)
- [TikZ & PGF Manual](https://tikz.dev/)
- [node-tikzjax](https://www.npmjs.com/package/node-tikzjax)

### Example Galleries
- [CeTZ Examples](https://github.com/johannes-wolf/cetz/tree/master/gallery)
- [Asymptote Gallery](http://asymptote.sourceforge.net/gallery/)
- [Penrose Registry](https://github.com/penrose/penrose/tree/main/packages/examples/src)
- [TikZ Examples](https://tikz.net/)

### Community
- [Typst Discord](https://discord.gg/typst)
- [Asymptote Forum](https://sourceforge.net/p/asymptote/discussion/)
- [Penrose GitHub Discussions](https://github.com/penrose/penrose/discussions)
