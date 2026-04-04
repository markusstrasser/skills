<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Subcommands & Convenience Flags

## Convenience Flags

| Flag | What it does |
|------|-------------|
| `--fast` | Gemini Flash + low reasoning (quick queries) |
| `--use-old` | Previous model version (e.g., Kimi K2 instead of K2.5) |
| `--no-thinking` | Disable reasoning (Kimi switches to instruct model) |

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
llmx vision file.png -p "describe"          # single image
llmx vision "frames/*.png" -p "summarize"   # multiple
llmx vision video.mp4 -p "list UI elements" # video
```
