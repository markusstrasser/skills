---
name: scientific-drawing
description: "Use when: 'draw a diagram', 'scientific figure', 'visualize this', 'architecture diagram', 'plot this function'. Typst/CeTZ (fast, default), TikZ (math/circuits/chemistry), D2 (architecture/ERD), Asymptote (3D)."
user-invocable: true
argument-hint: '[description of diagram]'
allowed-tools: [Bash, Read, Write, Grep, Glob]
effort: medium
---

# Scientific Drawing

Select tool, write source, compile to PDF/SVG, verify output.

## Tool Selection

```
Need diagram?
├─ Software architecture / ERD / flowchart?
│  └─ D2 (references/d2-guide.md)
├─ Mathematical / abstract algebra?
│  ├─ Need automatic layout from notation?
│  │  └─ Penrose (constraint-based, references/penrose.md)
│  └─ Need precise control?
│     └─ TikZ (references/tikz.md)
├─ 3D visualization?
│  └─ Asymptote (references/asymptote.md)
└─ Everything else (2D plots, diagrams, fast iteration)?
   └─ Typst + CeTZ (default — millisecond compile)
```

**Default to Typst + CeTZ** unless the task specifically needs TikZ packages (circuits, chemistry, Feynman) or D2 (architecture). Typst compiles in milliseconds vs seconds for LaTeX.

## Typst + CeTZ (Default)

```typst
#import "@preview/cetz:0.2.2": canvas, draw, plot

#canvas({
  import draw: *
  circle((0, 0), radius: 1, fill: blue.lighten(80%))
  line((0, 0), (2, 1), stroke: red)
  content((1, 0.5), [Hello])
})
```

Compile: `typst compile diagram.typ diagram.pdf` (or `.svg`)

Plotting:
```typst
#canvas({
  plot.plot(size: (8, 6), x-label: [Time], y-label: [Value], {
    plot.add(domain: (0, 2*calc.pi), x => calc.sin(x))
  })
})
```

Useful packages (auto-download on first use):
| Package | Use |
|---------|-----|
| `fletcher` | Arrow/commutative diagrams |
| `alchemist` | Molecular formulas |
| `inknertia` | Feynman, spacetime diagrams |

Gotchas: Math uses `$ ... $` not `\( ... \)`. Import version matters (`@preview/cetz:0.2.2`).

## Compile & Convert

```bash
# Typst (fastest)
typst compile diagram.typ diagram.pdf

# TikZ
pdflatex -interaction=nonstopmode diagram.tex

# Asymptote
asy -f pdf -noV diagram.asy

# D2
d2 input.d2 output.svg

# Penrose
bunx @penrose/roger trio trio.json > output.svg

# PDF to PNG (high res)
convert -density 300 diagram.pdf diagram.png
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `typst` not found | `brew install typst` |
| `pdflatex` not found | `brew install --cask mactex-no-gui` |
| `asy` not found | `brew install asymptote` |
| `d2` not found | `brew install d2` |
| TikZ missing package | `tlmgr install <package>` |
| Asymptote opens viewer | `settings.interactiveView=false;` in `~/.asy/config.asy` |
| ImageMagick policy error | Edit `/etc/ImageMagick-7/policy.xml` — allow PDF read |

For detailed tool guides: `references/tikz.md`, `references/d2-guide.md`, `references/asymptote.md`, `references/penrose.md`.

$ARGUMENTS
