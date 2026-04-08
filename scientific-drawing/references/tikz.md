<!-- Reference file for scientific-drawing skill. Loaded on demand. -->
# TikZ Reference

## Quick Start

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

Compile: `pdflatex -interaction=nonstopmode diagram.tex`

## Domain Packages (all in TeX Live)

| Package | Use case |
|---------|----------|
| `chemfig` | Molecular structures |
| `mhchem` | Chemical equations (`\ce{2H2 + O2 -> 2H2O}`) |
| `circuitikz` | Circuit diagrams |
| `tikz-feynman` | Feynman diagrams (**needs LuaLaTeX**: `lualatex diagram.tex`) |
| `forest` | Trees, cladograms |
| `tikz-cd` | Commutative diagrams (`&` for columns, `\\` for rows) |
| `tikz-optics` | Lenses, mirrors, rays |
| `pgfplots` | Data plots, function graphs |

## Via node-tikzjax (JS rendering, no TeX install)

**Must wrap in document tags** — without them, node-tikzjax silently produces empty output:

```tex
\begin{document}
\begin{tikzpicture}
  % your code
\end{tikzpicture}
\end{document}
```

```bash
bun add -g node-tikzjax
```

```javascript
import tikzjax from 'node-tikzjax';
const svg = await tikzjax.default(texCode);
```

## Gotchas

- `standalone` document class with `border=5pt` for tight cropping
- `\pgfplotsset{compat=1.18}` to avoid warnings
- tikz-feynman needs LuaLaTeX
- tikz-cd: use `&` for columns, `\\` for rows
