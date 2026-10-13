Folded from the anki project skill `card-diagrams` (`~/Projects/anki/.claude/skills/card-diagrams/SKILL.md` at 6b13f4a), 2026-10-14. Paths point at `~/Projects/spaced/lab/diagrams`; run every command from `~/Projects/spaced`.

# Card diagrams

Visuals for cards in two forms: **TikZ**, compiled to a PNG, or **SVG**, generated or written by
hand. Pick the path, make the file, check it, then hand it over for the card.

## Path selection

| Need | Path |
|------|------|
| LaTeX math, 3D, biological structures, circuits, commutative diagrams | **TikZ** |
| Bar comparisons, process flows, gradients, number lines, thresholds | **SVG** |
| Small inline molecule glyph (H₂O, CO₂ …) | `lab/diagrams/molecule_svgs.py` (`get_molecule_svg("H2O")`) |
| Molecular structure from a name or SMILES | **RDKit**, `uv run --with rdkit` (see `domain-tools.md`) |
| Uncertain | **TikZ** (proven reliable) |

Some older diagrams are Typst (`lab/diagrams/sources/*.typ`). 17 of the 18 pin cetz 0.3.2, which
the 2026-10-14 consolidation plan lists as a known break under Typst 0.15 (installed: 0.15.1);
compile one before relying on it.

## TikZ path

1. **Start from a template** in `lab/diagrams/templates/`: `bar_comparison.tex`, `process_flow.tex`,
   `number_line.tex`, `cycle_diagram.tex`, `bipolar_axis.tex`. Keep sources in
   `lab/diagrams/sources/`.
2. **Adapt** it, using only the `anki*` colour names from `lab/diagrams/preamble.tex`:
   `ankihighlight`, `ankisecondary`, `ankiaccent`, `ankiaccent2`, `ankimuted`, `ankianswer` (the names
   predate Spaced; they map to the card CSS variables).
3. **Compile:**
   ```bash
   uv run --project lab python lab/diagrams/tikz.py compile lab/diagrams/sources/<file>.tex --verify
   ```
4. **Inspect** the PNG for scientific accuracy, not just that it renders.
5. **Iterate** at most 3 rounds, then hand the file over for the card (below).

| Error | Fix |
|-------|-----|
| `pdflatex` not found | `brew install --cask mactex-no-gui` |
| Missing package | Add `\usepackage{...}`; common: `chemfig`, `circuitikz`, `tikz-feynman`, `forest` |
| `magick` fails (ImageMagick) | Check `magick --version`; a policy issue → edit ImageMagick's `policy.xml` |
| Renders but wrong | Read the template source; check coordinates and data values |
| Colours look wrong | Only `anki*` names from `preamble.tex`; never hard-coded hex |

Rules:
- `\input{../preamble}` right after `\documentclass` (from `templates/` or `sources/`).
- The background stays transparent; the card provides it. Never `\pagecolor`.
- Use the preamble's `anki node`, `anki bar`, `anki arrow` and `anki label` styles.
- `tikz.py themes` lists the colour themes; vary themes across topics so similar diagrams stay
  distinct (principles § Theme Variety).

## SVG path

**Generator** for the standard patterns:
```bash
uv run --project lab python lab/diagrams/generate_card_svg.py bar --values "36,32,2" --labels "A,B,C"
uv run --project lab python lab/diagrams/generate_card_svg.py flow --steps "Glucose,Pyruvate,Acetyl-CoA"
uv run --project lab python lab/diagrams/generate_card_svg.py numberline --range "0,14" --markers "7:neutral"
uv run --project lab python lab/diagrams/generate_card_svg.py gradient --range "380,700" --markers "450:blue"
uv run --project lab python lab/diagrams/generate_card_svg.py fold --baseline "4" --fold "34" --labels "A,B"
```

**By hand**, when no pattern fits: follow `~/Projects/spaced/docs/cards/design-language.md` and
`svg-rules.md`. The rules that matter most:
- Colours go in `style="fill:var(--color-highlight);opacity:0.6"`, never in `fill=`/`stroke=`
  attributes, where a CSS variable does not resolve. The same holds for `<stop>` in gradients.
- Root: `<svg viewBox="0 0 500 105" class="vis">`, 500 wide and 100–110 tall; `system-ui` labels
  at 11–13px.
- No hard-coded hex colours, no dark panel backgrounds, `--svg-track` at opacity 0.2 or more.

**Validate:**
```bash
uv run --project lab python lab/diagrams/validate_card_svg.py <file.svg>
echo '<svg ...>' | uv run --project lab python lab/diagrams/validate_card_svg.py -
```
Errors must be fixed (hard-coded colours, missing `.vis`, dark backgrounds, missing viewBox).
Warnings are for review (viewBox size, font size, track opacity). Spaced's `svg-theme` lint checks
the theme rules again on every card that shows an SVG.

## Putting it on a card

- Agents cannot write to `~/cards`. Render into your scratch directory and hand the file to the
  session that files your edits, to be placed in the deck's `media/` directory.
- The edit then references it on the answer side: `![alt](media/<file>.svg)`. Spaced inlines an SVG
  file, so its CSS variables follow the theme. A referenced file that is missing is an error.
- Formats: SVG stays as it is; raster stills are kept as AVIF and animations as H.264 MP4
  (`docs/PLAN.md`, Media policy).
- Tag the card `.ai-visual` (and `.ai-modified`) in its attribute block.

## Quality gates

Every card diagram passes all of these:

1. **Compiles or validates:** TikZ compiles on the first try; SVG validates with 0 errors.
2. **Scientifically accurate:** values, labels and relationships are right, not just rendered.
3. **Reconstruction test:** "When I blank on the answer, does seeing this make me go 'oh right'?"
   - Pass: the geometry is the concept (a voltage axis, d² scaling, process topology).
   - Fail: the visual decorates text (a bar chart restating a number, a split bar for a ratio).
   - 6 of 8 candidates failed this test historically. Be ruthlessly honest.
4. **Theme-aware:** no hard-coded colours; it works on Paper (light) and Dusk (dark).
5. **Within the budget:** about 30–50 visuals per 1,000 cards; the `media-budget` lint counts them.

## Troubleshooting

- **SVG has no panel or sizing:** the root lacks `class="vis"`.
- **Colours wrong on Dusk:** `fill="..."` instead of `style="fill:var(--...)"`.
- **Text unreadable:** the viewBox should be 500 × 100–110 with 11–13px labels; 260×35 and 400×70
  were too small.
- **TikZ looks wrong on the card:** check `\input{../preamble}` and the `anki*` colour names.
