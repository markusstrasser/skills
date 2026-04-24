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
llmx image "prompt" -o out.png       # Gemini 3 Pro Image
llmx image "prompt" -r 2K -a 16:9    # resolution + aspect
llmx svg "prompt" -o out.svg         # SVG output
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
