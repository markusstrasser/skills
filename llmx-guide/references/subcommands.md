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
llmx image "prompt" -o out.png       # OpenAI GPT Image 2
llmx image -i ref.jpg "prompt"       # GPT Image 2 edit/reference workflow
llmx image "prompt" --provider google -m pro -r 2K -a 16:9
llmx svg "prompt" -o out.svg         # SVG output
```

GPT Image 2 is the default because it is the current SoTA image model. For
personal style previews, preserve identity explicitly and constrain the edit:

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
