<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Subcommands & Convenience Flags

## Convenience Flags

| Flag | What it does |
|------|-------------|
| `--fast` | Gemini Flash + low reasoning (quick queries) |
| `--use-old` | Previous model version |
| `--no-thinking` | Disable reasoning |

## Deep Research

```bash
llmx research "topic"           # o3, background mode, 2-10 min
llmx research --mini "topic"    # o4-mini, faster/cheaper
llmx research "topic" -o out.md # save output
```

## Image Generation

```bash
llmx image "prompt" -o out.png       # codex image_gen on the plan ($0; plan's current model)
llmx image -i ref.jpg "prompt"       # same route, edit/reference workflow
llmx image --auth api -m flare --quality low --complexity low "prompt" -o out.png  # metered 2.6
llmx image --auth api -m flare --format gif --frame-count 6 "prompt" -o loop.gif
llmx image --auth api --format svg "prompt" -o logo.svg  # --svg-model, --svg-effort
llmx image --auth api -i room.png --markup circled.png "replace the circled vase" -o out.png
llmx image "prompt" --provider google -m pro -r 2K -a 16:9
llmx svg "prompt" -o out.svg         # SVG written by Gemini as text, no image model
```

Metered default: `gpt-image-2.6-sunburst`; `sunburst` and `flare` alias the 2.6 models.
`--complexity`, `--format svg|gif`, the frame flags, `--markup` and the SVG flags need
`--auth api`, and llmx fails rather than dropping them on another route.

Measured 2026-11-05, where the live API differs from the guide or the guide is silent:

- `--frame-count` stops at 16 (HTTP 400 above it; the guide says 64).
- GIF frames are laid out on one sprite sheet: 1024x1024 frames failed at 2, 3 and 4 frames
  ("No supported sheet fits"), `auto` and 512x512 returned 512px frames.
- SVG needs `svg.model` on this account; llmx sends `gpt-6.1-sol` unless `--svg-model` is set.
- 2.6 rejects `--input-fidelity`; 2.5 rejects `--complexity` and SVG.
- 4 frames at low quality cost 555 output tokens, a 1024x1024 low image 824, xhigh 3122.

For personal style previews, preserve identity explicitly and constrain the edit:

```bash
llmx image \
  --input-image photobooth.jpg \
  --quality high \
  --size 1024x1536 \
  -o textured-crop-beard.png \
  "Realistic grooming preview of the same person. Preserve identity, face shape, skin texture, camera angle, lighting, clothing, and background. Change only the hairstyle to a textured crop and facial hair to a short boxed beard."
```

## Vision Analysis

```bash
llmx vision file.png -p "describe"              # single image
llmx vision "frames/*.png" -p "summarize"       # multiple
llmx vision video.mp4 -p "list UI elements"     # video
llmx vision page.png -p "extract" -o result.md  # -o writes to file (added 2026-04)
```

**PDFs** — vision doesn't accept PDFs directly. Convert first:
```bash
pdftoppm -png -r 200 report.pdf out
llmx vision out-*.png -p "transcribe everything"
```

**Binary file in `-f`** — `llmx chat -f foo.pdf` now detects binary and emits
a clear error with conversion hints (2026-04). Before that fix, it threw an
opaque `UnicodeDecodeError`.
