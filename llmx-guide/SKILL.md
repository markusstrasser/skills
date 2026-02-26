---
name: llmx Guide
description: Critical gotchas when calling llmx from Python. Non-obvious bugs and incompatibilities.
---

# llmx CLI Gotchas

## Bug: shell=True breaks with parentheses

**Wrong:**

```python
subprocess.run(f'echo {repr(prompt)} | llmx ...', shell=True)  # BREAKS if prompt has ()
```

**Right:**

```python
subprocess.run(['llmx', '--provider', 'google'], input=prompt, ...)
```

## Bug: --reasoning-effort only works with OpenAI

```python
# Works:
['llmx', '--provider', 'openai', '--reasoning-effort', 'high']

# Silently ignored or errors:
['llmx', '--provider', 'google', '--reasoning-effort', 'high']  # WRONG
['llmx', '--model', 'kimi-k2-thinking', '--reasoning-effort', 'high']  # WRONG
```

## Model names: hyphens not dots

| Right               | Wrong               |
| ------------------- | ------------------- |
| `claude-sonnet-4-5` | `claude-sonnet-4.5` |
| `kimi-k2-thinking`  | `kimi2-thinking`    |

## Testing: test small before full pipeline

```bash
# Don't wait for full pipeline to discover API key is wrong
llmx --provider google <<< "2+2?"
```

## Judge names ≠ model names

| Context               | Name             |
| --------------------- | ---------------- |
| llmx CLI              | `gemini-2.5-pro` |
| tournament MCP judges | `gemini25-pro`   |

## Image Generation (v0.3.0+)

Generate images with Gemini 3 Pro Image:

```bash
# Generate PNG
llmx image "pixel art robot" -o robot.png

# With options
llmx image "game sprite" -r 2K -a 16:9 -o sprite.png

# Generate SVG
llmx svg "arrow icon" -o arrow.svg
```

**Options:**
- `-o` output path
- `-r` resolution: `1K`, `2K`, `4K`
- `-a` aspect ratio: `1:1`, `16:9`, `4:3`, etc.

**Note:** No Gemini 3 Flash Image model exists - both `flash` and `pro` use `gemini-3-pro-image-preview`.

## Vision Analysis (v0.4.0+)

Analyze images/videos with Gemini 3 Flash/Pro:

```bash
# Single image
llmx vision screenshot.png -p "What UI issues do you see?"

# Multiple images with sampling
llmx vision "frames/*.png" -p "Summarize gameplay" --sample 5

# Video analysis (uploads to Gemini Files API)
llmx vision gameplay.mp4 -p "List all UI elements"

# Compare images
llmx vision img1.png img2.png -p "Compare these two"
```

**Options:**
- `-p` prompt (required)
- `-m` model: `flash` (default, fast) or `pro` (better)
- `--sample N` sample N frames evenly from many images
- `--json` request structured JSON output

**Size limits:**
- Inline: < 20MB images, < 100MB videos
- Larger files auto-upload via Files API
