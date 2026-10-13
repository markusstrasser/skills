Moved from `~/Projects/anki/.claude/skills/card-diagrams/references/svg-rules.md` at 6b13f4a, 2026-10-14. Paths point at `~/Projects/spaced/lab/diagrams`; run commands from `~/Projects/spaced`.

# SVG Design Rules for Cards

Detailed implementation rules from `~/Projects/spaced/docs/cards/design-language.md` and hard-won debugging sessions.

## Color Variable Mapping

| SVG element | CSS variable | Purpose |
|-------------|-------------|---------|
| Background | `--svg-bg` (via CSS on `svg.vis`) | Subtle panel container |
| Track bar | `--svg-track` | Visible but subtle base track |
| Safe/resting zones | `--color-secondary` | Teal (Paper) / Gold (Dusk) |
| Thresholds, danger | `--color-accent` | Red (Paper) / Blue (Dusk) |
| Highlights, emphasis | `--color-highlight` | Blue (Paper) / Rose (Dusk) |
| Muted labels, axes | `--color-muted` | Grey on both themes |
| Answer text in SVG | `--color-answer` | Matches card text color |
| Purple accent | `--color-accent2` | Purple on both themes |

The values for Paper (light) and Dusk (dark) live in `~/Projects/spaced/ui/styles.css`; always use the variable, never the value.

## Critical: CSS Variables in SVG

CSS variables do NOT work in SVG presentation attributes — only in `style`:

```html
<!-- WRONG — variable won't resolve -->
<rect fill="var(--color-secondary)"/>
<stop stop-color="var(--color-accent)"/>
<text fill="var(--color-muted)">Label</text>
<line stroke="var(--color-highlight)"/>

<!-- CORRECT — use style attribute -->
<rect style="fill:var(--color-secondary);opacity:0.2"/>
<stop style="stop-color:var(--color-accent);stop-opacity:0.15"/>
<text style="fill:var(--color-muted);font-size:11px;font-family:system-ui">Label</text>
<line style="stroke:var(--color-highlight);stroke-width:2"/>
```

This applies to ALL SVG elements including `<stop>` in gradients.

## SVG Skeleton

```html
<svg viewBox="0 0 500 105" class="vis" xmlns="http://www.w3.org/2000/svg">
  <!-- track (base bar) -->
  <rect x="40" y="45" width="420" height="12" rx="6"
        style="fill:var(--svg-track);opacity:0.2"/>

  <!-- data element -->
  <rect x="40" y="45" width="200" height="12" rx="6"
        style="fill:var(--color-highlight);opacity:0.6"/>

  <!-- label -->
  <text x="40" y="38"
        style="fill:var(--color-muted);font-size:11px;font-family:system-ui">
    Label text
  </text>

  <!-- value -->
  <text x="245" y="54"
        style="fill:var(--color-answer);font-size:13px;font-family:system-ui;font-weight:bold">
    42
  </text>
</svg>
```

## Sizing Rules

| Property | Value | Why |
|----------|-------|-----|
| ViewBox width | 500 | Matches card content width |
| ViewBox height | 100-110 | Generous — not sparkline. Earlier attempts at 35 and 70 were too small |
| Font size | 11-13px | Below 11px is unreadable at card scale |
| Root class | `vis` | Spaced's CSS (`.content svg.vis` in `ui/styles.css`) handles background, padding, width and margins |
| Max width | 520px (via CSS) | Prevents overflow on wide screens |

## Things That Look Bad

- **Dark panel backgrounds** (`fill="#2a2a2e"` rect) — terrible on Paper (light) theme. The `svg.vis` CSS class handles the panel bg.
- **Track opacity 0.1** — invisible on Paper. Use **0.2 minimum** for `--svg-track`.
- **Tiny viewboxes** (`260×35`, `400×70`) — text becomes unreadable, bars become meaningless.
- **Hardcoded colors** — break on theme switch. Always CSS variables.
- **Internal background rect** — don't add a `<rect>` for background. `svg.vis` CSS does this.

## Visual Pattern Selection

10 patterns available. See `~/Projects/spaced/docs/cards/design-language.md` for full specs.

**Reconstruction Test**: "When I blank on the answer, does seeing this image make me go 'oh right'?"

Historically, **6 of 8 candidates failed**. Most bar charts for numbers are useless decoration.

**Passes** (geometry IS the concept):
- Bipolar axes (membrane potential: rest/threshold/peak zones)
- Fold-change bars (diffusion d² scaling)
- Process topology where layout carries meaning
- Threshold markers (safe/danger boundary)

**Fails** (visual decorates text):
- Bar chart showing a single number (`2-4 μm³`)
- Split bar for a ratio (`1.3:1`)
- Comparison ladder restating a ranking already in text
- Any chart where removing the visual loses zero recall power

Visual budget: ~30-50 slots in a 1000-card deck.

## Validator Reference

```bash
# Single file
uv run --project lab python lab/diagrams/validate_card_svg.py diagram.svg

# Directory
uv run --project lab python lab/diagrams/validate_card_svg.py lab/diagrams/sources/svg/

# From stdin (pipe from generator)
echo '<svg ...>' | uv run --project lab python lab/diagrams/validate_card_svg.py -
```

**Errors** (exit code 1, must fix):
- Hardcoded fill/stroke with hex colors
- Missing `class="vis"` on root `<svg>`
- Dark background on root or `<rect>`
- Missing `viewBox`

**Warnings** (exit code 0, review):
- ViewBox outside 400-520 width or 80-130 height
- Font size below 11px
- Track opacity below 0.2
- `stop-color` as attribute on `<stop>`

## Generator Quick Reference

```bash
# Bar comparison (Comparison Ladder)
uv run --project lab python lab/diagrams/generate_card_svg.py bar --values "36,32,2" --labels "A,B,C"

# Process flow (Process Arrow)
uv run --project lab python lab/diagrams/generate_card_svg.py flow --steps "Glucose,Pyruvate,Acetyl-CoA"

# Number line (Range Bar / Bipolar Axis)
uv run --project lab python lab/diagrams/generate_card_svg.py numberline --range "0,14" --markers "7:neutral"

# Gradient bar
uv run --project lab python lab/diagrams/generate_card_svg.py gradient --range "380,700" --markers "450:blue"

# Fold-change bar
uv run --project lab python lab/diagrams/generate_card_svg.py fold --baseline "4" --fold "34" --labels "A,B"
```

Color rotation for multi-element charts: `--color-highlight`, `--color-secondary`, `--color-accent`, `--color-accent2`.
