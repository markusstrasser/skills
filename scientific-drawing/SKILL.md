---
name: scientific-drawing
description: Generate scientific diagrams, figures, and illustrations using Typst/CeTZ, Asymptote, Penrose, TikZ, or D2. Use when creating mathematical diagrams, technical illustrations, scientific figures, vector graphics, 3D plots, architecture diagrams, flowcharts, ERDs, network diagrams, or converting mathematical notation to visual representations. Automatically selects the best tool based on the task.
allowed-tools: Bash, Read, Write, Grep, Glob
---

# Scientific Drawing & Diagram Generation

Select the right tool, compile the diagram, verify the output.

## Tool Selection

```
Need diagram?
├─ Software architecture / system / ERD?
│  └─ D2 (see references/d2-guide.md)
├─ Mathematical / abstract algebra?
│  ├─ Need automatic layout from notation?
│  │  └─ Penrose (constraint-based)
│  └─ Need precise control?
│     └─ TikZ (explicit coordinates)
├─ 3D visualization?
│  └─ Asymptote (native 3D)
├─ Typst document integration?
│  └─ CeTZ (native Typst)
└─ Specialized domain (circuits, chemistry, Feynman)?
   └─ TikZ (largest package ecosystem)
```

| Tool | Best for | Compilation |
|------|----------|-------------|
| **TikZ** | Math, circuits, chemistry, Feynman, trees, commutative diagrams | `pdflatex` → PDF/PNG |
| **Typst + CeTZ** | 2D plots, diagrams in Typst docs, fast iteration | `typst compile` → PDF |
| **Asymptote** | 3D surfaces, precise technical drawings | `asy -f pdf -noV` |
| **Penrose** | Set theory, category theory, automatic layout from math notation | `bunx @penrose/roger trio` → SVG |
| **D2** | Architecture, ERDs, flowcharts, network topology | `d2` → SVG/PNG |

## TikZ

### Quick Start

```tex
\documentclass[border=5pt]{standalone}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
  \draw[thick, ->] (0,0) -- (3,0) node[right] {$x$};
  \draw[thick, ->] (0,0) -- (0,3) node[above] {$y$};
  \draw[blue, domain=0:2.5] plot (\x, {0.5*\x*\x});
\end{tikzpicture}
\end{document}
```

### Compile

```bash
pdflatex -interaction=nonstopmode diagram.tex
# Or convert to PNG:
convert -density 300 diagram.pdf diagram.png
```

### Domain Packages (all in TeX Live)

| Package | Use case |
|---------|----------|
| `chemfig` | Molecular structures |
| `mhchem` | Chemical equations (`\ce{2H2 + O2 -> 2H2O}`) |
| `circuitikz` | Circuit diagrams |
| `tikz-feynman` | Feynman diagrams |
| `forest` | Trees, cladograms |
| `tikz-cd` | Commutative diagrams |
| `tikz-optics` | Lenses, mirrors, rays |
| `pgfplots` | Data plots, function graphs |

### Via node-tikzjax (JS rendering, no TeX install)

**Must wrap in document tags** — without them, node-tikzjax silently produces empty output:

```tex
\begin{document}
\begin{tikzpicture}
  % your code
\end{tikzpicture}
\end{document}
```

```bash
# Install
bun add -g node-tikzjax
```

```javascript
import tikzjax from 'node-tikzjax';
const svg = await tikzjax.default(texCode);
```

### Gotchas

- `standalone` document class with `border=5pt` for tight cropping
- `\pgfplotsset{compat=1.18}` to avoid warnings
- tikz-feynman needs LuaLaTeX: `lualatex diagram.tex`
- tikz-cd: use `&` for columns, `\\` for rows

## Typst + CeTZ

### Quick Start

```typst
#import "@preview/cetz:0.2.2": canvas, draw, plot

#canvas({
  import draw: *
  circle((0, 0), radius: 1, fill: blue.lighten(80%))
  line((0, 0), (2, 1), stroke: red)
  content((1, 0.5), [Hello])
})
```

### Plotting

```typst
#canvas({
  plot.plot(size: (8, 6), x-label: [Time], y-label: [Value], {
    plot.add(domain: (0, 2*calc.pi), x => calc.sin(x))
  })
})
```

### Compile

```bash
typst compile diagram.typ diagram.pdf
typst compile diagram.typ diagram.svg  # Direct SVG
```

### Useful Typst Packages

| Package | Use case |
|---------|----------|
| `fletcher` | Arrow/pathway/commutative diagrams |
| `alchemist` | Skeletal molecular formulas |
| `typsium` | Chemical equations |
| `inknertia` | Feynman, spacetime, free-body diagrams |
| `physica` | Physics math notation (brakets, tensors) |

All auto-download on first use.

### Gotchas

- CeTZ import: `@preview/cetz:0.2.2` — check for latest version
- Math: `$ ... $` not `\( ... \)`
- Millisecond compilation — great for iteration

## Asymptote

### Quick Start (2D)

```asymptote
import graph;
size(200);
draw(unitcircle, blue);
dot((0,0), red);
label("Origin", (0,0), S);
```

### 3D

```asymptote
import graph3;
size(200);
currentprojection=orthographic(4,2,3);
draw(surface((x,y) => x^2+y^2, (-1,-1), (1,1), nx=20, ny=20),
    lightblue+opacity(0.7));
axes3("$x$", "$y$", "$z$");
```

### Compile

```bash
asy -f pdf -noV diagram.asy
asy -f svg -noV diagram.asy
```

### Gotchas

- For headless/batch: `settings.interactiveView=false; settings.batchView=false;` in `~/.asy/config.asy`
- 3D rendering needs OpenGL or `-render 0` for vector output

## Penrose

Three-file architecture: domain (types) + substance (instances) + style (rendering).

### Example

`sets.domain`:
```
type Set
predicate Subset(Set, Set)
```

`diagram.substance`:
```
Set A, B
Subset(A, B)
```

`venn.style`:
```
forall Set x {
  x.shape = Circle { strokeWidth: 2 }
}
forall Set A; Set B where Subset(A, B) {
  ensure contains(B.shape, A.shape)
}
```

`trio.json`:
```json
{
  "domain": "./sets.domain",
  "style": ["./venn.style"],
  "substance": "./diagram.substance",
  "variation": "seed-42"
}
```

### Compile

```bash
bunx @penrose/roger trio trio.json > output.svg
```

### Gotchas

- Constraint-based: declare relationships, optimizer finds positions
- If optimization fails, try different `"variation"` seeds
- Best for: set theory, category theory, graph theory — where logical relationships matter more than exact coordinates

## D2

Architecture diagrams, ERDs, flowcharts. For the full reference with design patterns, layout engines, and debugging, see `references/d2-guide.md`.

### Quick Start

```d2
frontend -> backend: API calls
backend -> database: queries
database: PostgreSQL {shape: cylinder}
```

### Compile

```bash
d2 input.d2 output.svg
d2 --layout=elk input.d2 output.svg    # Better for hierarchical
d2 -t 101 input.d2 output.svg          # With theme
d2 --watch input.d2 output.svg         # Live preview
```

### Gotchas

- Default layout (dagre) is fine for simple diagrams
- ELK: better for vertical hierarchies, respects explicit dimensions
- TALA: best features but requires Pro license
- Use `near: top-center` to pin nodes when feedback loops confuse layout

## Format Conversion

```bash
# PDF to PNG (high res)
convert -density 300 diagram.pdf diagram.png

# SVG to PNG
convert -density 150 -background white diagram.svg diagram.png

# SVG to PDF
convert diagram.svg diagram.pdf
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pdflatex` not found | Install TeX Live: `brew install --cask mactex-no-gui` |
| `typst` not found | `brew install typst` |
| `asy` not found | `brew install asymptote` |
| `d2` not found | `brew install d2` |
| `bunx @penrose/roger` fails | `bun add -g @penrose/roger` |
| TikZ missing package | `tlmgr install <package>` |
| Asymptote opens viewer | Add `settings.interactiveView=false;` to `~/.asy/config.asy` |
| Penrose optimization fails | Change `"variation"` seed in trio.json |
| D2 overlapping labels | Try `--layout=elk`, or use `near:` constraints |
| ImageMagick policy error | Edit `/etc/ImageMagick-7/policy.xml` — allow PDF read |

## Advanced Workflows

For CI/CD integration, Docker builds, Makefile automation, and batch processing, see `references/advanced-workflows.md`.
