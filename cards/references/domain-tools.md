Moved from `~/Projects/anki/.claude/skills/card-diagrams/references/domain-tools.md` at 6b13f4a, 2026-10-14. Paths point at `~/Projects/spaced/lab/diagrams`; run commands from `~/Projects/spaced`.

# Domain-Specific Diagram Tools

Code examples for specialized scientific domains. All TikZ packages are installed in TeX Live. RDKit is not a lab dependency: run it with `uv run --with rdkit`.

## Chemistry

### RDKit — SMILES to SVG (preferred for structural formulas)

```python
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

mol = Chem.MolFromSmiles('CN1C=NC2=C1C(=O)N(C(=O)N2C)C')  # caffeine
d = rdMolDraw2D.MolDraw2DSVG(400, 300)
d.DrawMolecule(mol)
d.FinishDrawing()
svg = d.GetDrawingText()
```

Run: `uv run --with rdkit python -c "..."`. For tiny inline glyphs of common molecules without RDKit, `lab/diagrams/molecule_svgs.py` has hand-made templates (`get_molecule_svg("H2O")`).

Common SMILES:
| Molecule | SMILES |
|----------|--------|
| Ethanol | `CCO` |
| Benzene | `c1ccccc1` |
| Acetic acid | `CC(=O)O` |
| Glucose | `OC[C@@H](O1)[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O` |
| Caffeine | `CN1C=NC2=C1C(=O)N(C(=O)N2C)C` |
| ATP | `c1nc(c2c(n1)n(cn2)[C@@H]3[C@@H]([C@@H]([C@H](O3)COP(=O)(O)OP(=O)(O)OP(=O)(O)O)O)O)N` |

### chemfig (TikZ) — hand-coded molecular structures

```tex
\usepackage{chemfig}
\chemfig{H-C(-[2]H)(-[6]H)-C(=O)-OH}  % acetic acid
```

### mhchem (LaTeX) — chemical equation typesetting

```tex
\usepackage[version=4]{mhchem}
\ce{2H2 + O2 -> 2H2O}
\ce{[Cu(H2O)4]^{2+} + 4NH3 -> [Cu(NH3)4]^{2+} + 4H2O}
```

## Physics

### tikz-feynman — Feynman diagrams

```tex
\usepackage{tikz-feynman}
\feynmandiagram[horizontal=a to b]{
  i1 -- [fermion] a -- [fermion] i2,
  a -- [photon, edge label=\(\gamma\)] b,
  f1 -- [fermion] b -- [fermion] f2,
};
```

### circuitikz — circuit diagrams

```tex
\usepackage{circuitikz}
\begin{circuitikz}
  \draw (0,0) to[R=$R_1$] (2,0) to[C=$C_1$] (2,-2) -- (0,-2) to[battery1] (0,0);
\end{circuitikz}
```

### tikz-optics — lenses, mirrors, ray diagrams

```tex
\usepackage{tikz-optics}
% Converging lens with ray diagram
```

## Biology

### forest (TikZ) — phylogenetic trees, cladograms

```tex
\usepackage{forest}
\begin{forest}
  [Eukaryota
    [Animalia [Chordata] [Arthropoda]]
    [Plantae [Angiosperms] [Gymnosperms]]
  ]
\end{forest}
```

### RDKit for biochemistry

Same SMILES pipeline works for amino acids, nucleotides, drug molecules, cofactors.

## Math

### tikz-cd — commutative diagrams

```tex
\usepackage{tikz-cd}
\begin{tikzcd}
  A \arrow[r, "f"] \arrow[d, "g"'] & B \arrow[d, "h"] \\
  C \arrow[r, "k"'] & D
\end{tikzcd}
```

Also: [quiver.app](https://q.uiver.app/) GUI generates tikz-cd code interactively.

### neuralnetwork (TikZ) — feedforward network diagrams

```tex
\usepackage{neuralnetwork}
% Layer-based network visualization
```

## Compilation

All domain tools use the same TikZ compilation pipeline:

```bash
# Single diagram
uv run --project lab python lab/diagrams/tikz.py compile <file.tex> --verify

# Batch compile directory
uv run --project lab python lab/diagrams/tikz.py compile lab/diagrams/sources/
```

Remember to `\input{../preamble}` (from `lab/diagrams/templates/` or `sources/`) for the card colours, and add the relevant `\usepackage{...}` for the domain package.
