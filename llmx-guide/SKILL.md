---
name: llmx Guide
description: Critical gotchas when calling llmx from Python. Non-obvious bugs and incompatibilities.
---

# llmx CLI Gotchas

## GPT-5.2 Timeouts (the #1 issue)

GPT-5.2 with reasoning burns time BEFORE producing output. Default 120s timeout is too low.

**Max timeout: 600s.** Validated at CLI level (1-600 range). No auto-scaling exists — set explicitly.

**Streaming avoids most timeouts:** Non-streaming holds the connection idle during reasoning. Proxies and HTTP clients kill idle connections. `--stream` sends keepalive chunks.

```bash
# WILL timeout with default settings:
llmx -m gpt-5.2 --reasoning-effort high --no-stream "complex query"

# Set timeout explicitly for reasoning models:
llmx -m gpt-5.2 --reasoning-effort high --timeout 600 "complex query"

# BEST — streaming avoids idle-connection kills:
llmx -m gpt-5.2 --reasoning-effort high --stream "complex query"

# For very long tasks, use deep research (background mode, no timeout):
llmx research "complex multi-source analysis"
```

**When calling from Python/subprocess:**
```python
subprocess.run(
    ['llmx', '-m', 'gpt-5.2', '--reasoning-effort', 'high', '--stream'],
    input=prompt, capture_output=True, text=True,
    timeout=600  # max allowed by llmx CLI
)
```

## Bug: shell=True breaks with parentheses

**Wrong:**

```python
subprocess.run(f'echo {repr(prompt)} | llmx ...', shell=True)  # BREAKS if prompt has ()
```

**Right:**

```python
subprocess.run(['llmx', '--provider', 'google'], input=prompt, ...)
```

## --reasoning-effort: valid values are minimal/low/medium/high

```python
# GPT-5.2 — supports minimal/low/medium/high:
['llmx', '-m', 'gpt-5.2', '--reasoning-effort', 'low']

# GPT-5-codex — supports low/medium/high (no minimal):
['llmx', '-m', 'gpt-5-codex', '--reasoning-effort', 'medium']

# Gemini 3.x — supports low/medium/high (no minimal):
['llmx', '-m', 'gemini-3.1-pro-preview', '--reasoning-effort', 'low']

# Kimi — no --reasoning-effort support. Use --no-thinking instead:
['llmx', '-m', 'kimi-k2.5', '--no-thinking']  # Switches to instruct model
```

**Defaults:** GPT-5 models auto-default to `--reasoning-effort high`. Gemini defaults to `high` server-side (no client default needed). Temperature locked to 1.0 for both GPT-5 and Gemini 3.x thinking models.

## Convenience flags (v0.4.0+)

- `--fast` — Uses Gemini Flash with low reasoning effort (quick queries)
- `--use-old` — Uses previous model version (e.g., Kimi K2 instead of K2.5)
- `--no-thinking` — Disables thinking/reasoning (Kimi switches to instruct model)

## Model names: hyphens not dots

| Right               | Wrong               |
| ------------------- | ------------------- |
| `claude-sonnet-4-6` | `claude-sonnet-4.6` |

**Kimi models:**
- `kimi-k2.5` — current default (K2.5 thinking, Jan 2026)
- `kimi-k2-thinking` — legacy (K2 thinking, Nov 2025). Use `--use-old` flag.

**Default model:** `gemini-3.1-pro-preview` (Gemini 3.1 Pro, Feb 2026)

## Verified Gemini Model Names (tested Feb 28, 2026)

Gemini naming is inconsistent. These are confirmed working:

| Model Name | Status | Use for |
|------------|--------|---------|
| `gemini-3-flash-preview` | Works | Cheap pattern extraction, fact-checking (Flash 3 text) |
| `gemini-3.1-flash-image-preview` | Works | Flash 3.1 with image (no text-only 3.1 Flash yet) |
| `gemini-3.1-pro-preview` | Works | Architectural review, cross-referencing, large context |
| `gemini-3-pro-preview` | Works | Older Pro 3.0 |
| `gemini-2.5-flash` | Works (warns "Lite") | Only for file/semantic search, not chat |
| `gpt-5.2` | Works | Quantitative/formal analysis |

**404 — DO NOT USE:**

| Wrong Name | Why |
|------------|-----|
| `gemini-3-flash` | Missing `-preview` suffix |
| `gemini-flash-3` | Wrong word order + missing `-preview` |

The `-preview` suffix is required for all Gemini 3.x models. This is a Google naming convention, not an llmx issue.

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

## Deep Research (v0.4.0+)

Background-mode research using OpenAI o3/o4-mini. No timeout issues — runs asynchronously.

```bash
# Full research report with citations (2-10 min, background mode)
llmx research "economic impact of semaglutide"

# Faster/cheaper with o4-mini
llmx research --mini "compare React vs Svelte"

# Save output
llmx research "CRISPR patent landscape" -o report.md

# With code interpreter for data analysis
llmx research --code-interpreter "global EV trends with data"
```

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
