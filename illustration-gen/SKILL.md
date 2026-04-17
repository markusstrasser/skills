---
name: illustration-gen
description: "Generate designer-style SVGs from text prompts via Quiver Arrow API (paid). Use when: 'make a logo', 'generate an icon', 'illustrate this concept as SVG'. NOT for precise scientific/technical diagrams — use scientific-drawing instead."
user-invocable: true
argument-hint: '[description of illustration]'
allowed-tools: [Bash, Read, Write]
effort: low
---

# Illustration Generation (Quiver Arrow)

Prompt-to-SVG via Quiver's Arrow 1.1 model. Black-box generation, paid per call.

## When to use this vs scientific-drawing

| Task | Use |
|------|-----|
| Logo, icon, decorative illustration, stylized graphic | **illustration-gen** |
| Architecture/ERD/flowchart, math diagram, plot, technical figure | **scientific-drawing** |
| Anything where you'll edit control points, replay deterministically, or version-control the source | **scientific-drawing** |

Arrow generates non-deterministically and costs credits per call. The output is editable SVG, but you can't re-derive it from source — re-prompting gives a different result.

## Setup (one-time)

```bash
# Get a key at app.quiver.ai \u2192 API keys, then:
export QUIVERAI_API_KEY=qvr_...
```

Add the export to `~/.zshrc` (or `~/.config/zsh/.env`) for persistence.

## Usage

```bash
uv run python3 ~/Projects/skills/illustration-gen/scripts/generate.py "a minimalist fox logo" -o fox.svg
```

Flags:

| Flag | Default | Notes |
|------|---------|-------|
| `-o, --output` | `illustration-<ts>.svg` | With `--n>1`, becomes `<stem>_<i>.svg` |
| `-m, --model` | `arrow-1.1` | Use `arrow-1.1-max` for detailed assets (higher cost) |
| `-i, --instructions` | none | Refinements: palette, line weight, style constraints |
| `-n, --n` | 1 | Number of variants |

Examples:

```bash
# Single output
uv run python3 ~/Projects/skills/illustration-gen/scripts/generate.py \
  "isometric server rack with cables" -o rack.svg

# Higher-quality model with style instructions
uv run python3 ~/Projects/skills/illustration-gen/scripts/generate.py \
  "abstract geometric crest" \
  -m arrow-1.1-max \
  -i "two-color flat fill, no gradients, thick strokes" \
  -o crest.svg

# Multiple variants for selection
uv run python3 ~/Projects/skills/illustration-gen/scripts/generate.py \
  "lab notebook icon" -n 4 -o notebook.svg
# \u2192 notebook_0.svg, notebook_1.svg, notebook_2.svg, notebook_3.svg
```

## API contract

- Endpoint: `POST https://api.quiver.ai/v1/svgs/generations`
- Auth: `Authorization: Bearer $QUIVERAI_API_KEY`
- Models: `arrow-1.1`, `arrow-1.1-max`
- Response: `{id, created, data: [{svg, mime_type}], credits}`

Pricing: prepaid credits (see quiver.ai/pricing). Script prints credits charged on each call.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `QUIVERAI_API_KEY not set` | Export the key (see Setup) |
| `HTTP 401` | Key invalid or revoked — regenerate at app.quiver.ai |
| `HTTP 402` | Out of credits — top up at quiver.ai/pricing |
| `HTTP 429` | Rate-limited — back off and retry |
| Non-SVG response | Check the printed payload; report upstream if persistent |

$ARGUMENTS
