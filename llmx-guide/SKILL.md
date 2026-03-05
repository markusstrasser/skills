---
name: llmx-guide
description: Critical gotchas when calling llmx from Python or Bash. Non-obvious bugs and incompatibilities. Use when writing code that calls llmx, debugging llmx failures, or choosing llmx model/provider options.
user-invocable: true
argument-hint: '[model name or issue description]'
---

# llmx Quick Reference

## Before You Call llmx — Checklist

1. **Model name correct?** Hyphens not dots (`claude-sonnet-4-6` not `claude-sonnet-4.6`)
2. **Timeout set?** Reasoning models need `--timeout 600` or `--stream`
3. **Using `shell=True`?** Don't — parentheses in prompts break it. Use list args + `input=`
4. **Test small first:** `llmx --provider google <<< "2+2?"` before full pipeline

## Model Names & Defaults

| Model | llmx name | Notes |
|-------|-----------|-------|
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | **Default model.** `-preview` suffix required for all Gemini 3.x |
| Gemini 3 Flash | `gemini-3-flash-preview` | Cheap. `-preview` required |
| Gemini 3 Flash | `gemini-3-flash-preview` | Budget: $0.50/$3/M, 1M ctx |
| Gemini 3.1 Flash Image | `gemini-3.1-flash-image-preview` | No text-only 3.1 Flash yet |
| GPT-5.3 Instant | `gpt-5.3-chat-latest` | Reasoning max: **medium only**. Auto-defaults |
| GPT-5.4 | `gpt-5.4` | Reasoning default: high. 1M context. |
| GPT-5.2 (legacy) | `gpt-5.2` | Reasoning default: high. 400K context. |
| GPT-5-Codex | `gpt-5-codex` | No `minimal` reasoning-effort |
| Kimi K2.5 | `kimi-k2.5` | No `--reasoning-effort`. Use `--no-thinking` |
| Kimi K2 (legacy) | `kimi-k2-thinking` | Use `--use-old` flag |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Hyphens, not dots |

**404 traps:** `gemini-3-flash` (missing `-preview`), `gemini-flash-3` (wrong order), `gpt-5.3` (needs `-chat-latest` suffix), `gpt-5.3-instant` (wrong — use `gpt-5.3-chat-latest`).

## Error Handling (v0.5.0+)

**Exit codes** — branch on these, don't parse stderr:
| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | — |
| 1 | General error | Read stderr for details |
| 2 | API key missing/invalid | Check env vars |
| 3 | Rate limit (429/503) | Wait or use `--fallback` |
| 4 | Timeout | Increase `--timeout` or use `--fallback` |
| 5 | Model error (context too large, bad params) | Fix request |

**Structured diagnostics** on stderr: `[llmx:ERROR] type=rate_limit provider=google model=gemini-3.1-pro status=429 exit=3`

**`--fallback MODEL`** — auto-retry once with fallback model on rate limit or timeout:
```bash
# Pro fails with 503 → automatically retries with Flash
llmx -m gemini-3.1-pro-preview --fallback gemini-3-flash-preview --timeout 300 "query"

# stderr shows: [llmx:FALLBACK] rate_limit → retrying with gemini-3-flash-preview
```

**From Python — check exit code:**
```python
result = subprocess.run(
    ['llmx', '-m', 'gemini-3.1-pro-preview', '--fallback', 'gemini-3-flash-preview'],
    input=prompt, capture_output=True, text=True, timeout=300
)
if result.returncode == 3:  # rate limit
    # llmx already tried fallback if --fallback was set
    pass
elif result.returncode == 4:  # timeout
    pass
```

## The Three llmx Footguns

### 1. GPT-5.4 Timeouts

GPT-5.4 (and 5.2) with reasoning burns time BEFORE producing output. Non-streaming holds the connection idle during reasoning — proxies and HTTP clients kill idle connections. Default 120s is too low.

**Max timeout: 600s** (validated at CLI level, 1-600 range). No auto-scaling exists — set explicitly.

**Streaming avoids most timeouts** because `--stream` sends keepalive chunks during reasoning.

```bash
# WILL timeout:
llmx -m gpt-5.4 --reasoning-effort high --no-stream "complex query"

# Fix — stream (best) or explicit timeout:
llmx -m gpt-5.4 --reasoning-effort high --stream "complex query"
llmx -m gpt-5.4 --reasoning-effort high --timeout 600 "complex query"

# For very long tasks — deep research runs in background (no timeout):
llmx research "complex multi-source analysis"
```

From Python:
```python
subprocess.run(
    ['llmx', '-m', 'gpt-5.4', '--reasoning-effort', 'high', '--stream'],
    input=prompt, capture_output=True, text=True,
    timeout=600  # max allowed by llmx CLI
)
```

### 2. shell=True + Parentheses

```python
# BREAKS if prompt has ():
subprocess.run(f'echo {repr(prompt)} | llmx ...', shell=True)

# CORRECT — always use list args:
subprocess.run(['llmx', '--provider', 'google'], input=prompt, capture_output=True, text=True)
```

### 3. Reasoning Effort Values

| Model | Valid values | Default |
|-------|------------|---------|
| GPT-5.3 Instant | **medium only** | medium (auto) |
| GPT-5.4 | minimal, low, medium, high | high |
| GPT-5.2 | minimal, low, medium, high | high |
| GPT-5-Codex | low, medium, high | high |
| Gemini 3 Flash | low, medium, high | high (server-side) |
| Gemini 3.x (Pro/Flash) | low, medium, high | high (server-side) |
| Kimi K2.5 | N/A — use `--no-thinking` | thinking on |

Temperature locked to 1.0 for GPT-5 and Gemini 3.x thinking models.

## Convenience Flags

| Flag | What it does |
|------|-------------|
| `--fast` | Gemini Flash + low reasoning (quick queries) |
| `--use-old` | Previous model version (e.g., Kimi K2 instead of K2.5) |
| `--no-thinking` | Disable reasoning (Kimi switches to instruct model) |

## Subcommands

### Deep Research
```bash
llmx research "topic"           # o3, background mode, 2-10 min
llmx research --mini "topic"    # o4-mini, faster/cheaper
llmx research "topic" -o out.md # save output
```

### Image Generation
```bash
llmx image "prompt" -o out.png       # Gemini 3 Pro Image
llmx image "prompt" -r 2K -a 16:9    # resolution + aspect
llmx svg "prompt" -o out.svg         # SVG output
```

### Vision Analysis
```bash
llmx vision file.png -p "describe"          # single image
llmx vision "frames/*.png" -p "summarize"   # multiple
llmx vision video.mp4 -p "list UI elements" # video
```

### CLI Backends (subscription pricing)
```bash
llmx -p gemini-cli "question"   # Google account auth
llmx -p codex-cli "question"    # ChatGPT subscription auth
```

Falls back to API silently for: `--schema`, `-s`, `--search`, `--stream`, `--reasoning-effort` != high.

## Judge Names ≠ Model Names

| Context | Name |
|---------|------|
| llmx CLI | `gemini-3.1-pro-preview` |
| tournament MCP judges | `gemini25-pro` |

$ARGUMENTS
