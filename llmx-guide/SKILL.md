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
4. **Using `-o FILE`?** Never use `> file` shell redirects — they buffer until exit
5. **Know the transport and fallback triggers:** `openai` prefers `codex exec`, `google` prefers `gemini`, then falls back to API

## When llmx Fails — Diagnose, Don't Downgrade

**Never swap to a weaker model as a "fix."** If GPT-5.4 or Gemini Pro fails, the problem is the dispatch — not the model. Switching to Flash or GPT-5.2 loses the capability you needed.

**Diagnostic steps (in order):**
1. Check exit code: `echo $?` — tells you rate limit (3), timeout (4), or model error (5)
2. Check stderr: llmx prints `[llmx:ERROR] type=... provider=... status=...`
3. Re-run with `--debug` on a small prompt to isolate
4. Common fixes: increase `--timeout`, add `--stream`, reduce context size, check API key

## Model Names & Defaults

| Model | llmx name | Notes |
|-------|-----------|-------|
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | **Default Google model.** `google` prefers Gemini CLI when installed |
| Gemini 3 Flash | `gemini-3-flash-preview` | Cheap. `-preview` required |
| Gemini 3 Flash | `gemini-3-flash-preview` | Budget: $0.50/$3/M, 1M ctx |
| Gemini 3.1 Flash Image | `gemini-3.1-flash-image-preview` | No text-only 3.1 Flash yet |
| GPT-5.3 Instant | `gpt-5.3-chat-latest` | Reasoning max: **medium only**. Auto-defaults |
| GPT-5.4 | `gpt-5.4` | **Default OpenAI model.** `openai` prefers Codex CLI when installed. API fallback defaults reasoning to `high`; `xhigh` is also supported. |
| GPT-5.2 (legacy) | `gpt-5.2` | Legacy OpenAI default. 400K context. |
| GPT-5-Codex | `gpt-5-codex` | No `minimal` reasoning-effort |
| Kimi K2.5 | `kimi-k2.5` | No `--reasoning-effort`. Use `--no-thinking` |
| Kimi K2 (legacy) | `kimi-k2-thinking` | Use `--use-old` flag |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Hyphens, not dots |

**404 traps:** `gemini-3-flash` (missing `-preview`), `gemini-flash-3` (wrong order), `gpt-5.3` (needs `-chat-latest` suffix), `gpt-5.3-instant` (NOT in litellm model map as of v1.82 — use `gpt-5.3-chat-latest` or prefix as `openai/gpt-5.3-instant`).

## Token Limits (litellm 1.82)

| Model | Max Input | Max Output | Notes |
|-------|----------|-----------|-------|
| GPT-5.4 | 1,050,000 | 128,000 | |
| GPT-5.2 | 272,000 | 128,000 | |
| GPT-5.3 Chat | 128,000 | 16,384 | Smallest output cap — watch for truncation |
| o4-mini | 200,000 | 100,000 | |
| Gemini 3.1 Pro | 1,048,576 | 65,536 | Server default is 8K — always pass `--max-tokens 65536` |
| Gemini 3 Flash | 1,048,576 | 65,535 | |

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

## The Four llmx Footguns

### 1. GPT-5.4 Timeouts

GPT-5.4 (and 5.2) with reasoning burns time BEFORE producing output. Non-streaming holds the connection idle during reasoning — proxies and HTTP clients kill idle connections. Default is 300s (since llmx 0.5.2).

**Max timeout: 900s** (validated at CLI level, 1-900 range). For review dispatches use `--timeout 600`.

**Wall-clock enforcement (v0.5.3+):** `--timeout` is enforced via SIGALRM, not httpx socket timeout. This means the process will actually exit after N seconds of real time — even with streaming keepalives or chunked transfer. Before v0.5.3, streaming calls could hang indefinitely past the timeout value.

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

### 2. Output Capture

**Use `--output FILE` (or `-o FILE`).** Writes via Python (unbuffered), not shell redirect.

```bash
# CORRECT — output goes to both stdout and file:
llmx -m gpt-5.4 -f context.md --timeout 600 -o output.md "query"

# BROKEN — never use shell redirects with llmx:
llmx -m gpt-5.4 "query" > output.md    # 0 bytes until process exits
llmx -m gpt-5.4 "query" > output.md &  # 0 bytes if killed

# BROKEN — these don't help either:
stdbuf -oL llmx "query" > output.md    # buffering is in shell >, not Python
PYTHONUNBUFFERED=1 llmx "query" > out  # same — shell > is the problem
```

**When dispatching from Claude Code:**
1. Use `-o FILE` for file output — never `> file`
2. Set Bash tool `timeout: 360000` (6 min) — default 120s kills llmx early
3. Compact context before dispatch — 2K context → 52s, 50K → may hang

### 3. shell=True + Parentheses

```python
# BREAKS if prompt has ():
subprocess.run(f'echo {repr(prompt)} | llmx ...', shell=True)

# CORRECT — always use list args:
subprocess.run(['llmx', '--provider', 'google'], input=prompt, capture_output=True, text=True)
```

### 4. Reasoning Effort Values

| Model | Valid values | Default |
|-------|------------|---------|
| GPT-5.3 Instant | **medium only** | medium (auto) |
| GPT-5.4 | none, minimal, low, medium, high, xhigh | high |
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
llmx -p google "question"       # prefers Gemini CLI, falls back to API
llmx -p openai "question"       # prefers Codex CLI, falls back to API
llmx -p gemini-cli "question"   # force Gemini CLI transport
llmx -p codex-cli "question"    # force Codex CLI transport
```

Falls back to API for:

- Gemini CLI: `--schema`, `-s`, `--search`, `--stream`, `--max-tokens`
- Codex CLI: `-s`, `--search`, `--stream`
- Both CLIs ignore explicit `--reasoning-effort`; they use their own default thinking behavior
- Codex CLI now handles `--schema` via `codex exec --output-schema`
- `--max-tokens` forces API because Gemini CLI defaults to 8K with no override
- `--output` works with both CLI and API transport (Python-level, not shell)

### CLI-First System Prompt Pattern

If you want CLI transport by default, **do not use `-s`**. `-s` becomes an API-fallback trigger for both Google and OpenAI providers.

Instead, inline the system instructions at the top of the prompt or context file:

```bash
cat <<'EOF' | llmx chat -p openai -m gpt-5.4 --timeout 600
<system>
You are reviewing code. Be concrete. Reference specific files and tradeoffs.
</system>

Review this design:
- ...
EOF
```

Important caveat:

- `<system>...</system>` is just prompt text, not a transport-level system role
- It preserves `gemini-cli` / `codex-cli` usage, but the model may treat it as advisory text rather than a hard system channel
- If you need a true system role, use `-s` and accept API fallback

### Codex CLI Reasoning Default

`llmx -p openai` inherits Codex CLI's own reasoning default. llmx does **not** pass a reasoning-effort flag to `codex exec`.

Set the Codex CLI default in `~/.codex/config.toml`:

```toml
model = "gpt-5.4"
model_reasoning_effort = "xhigh"
```

One-off override:

```bash
codex exec -c 'model_reasoning_effort="xhigh"' "question"
```

Practical implication:

- `llmx -p openai ...` on a machine with `model_reasoning_effort = "xhigh"` uses Codex CLI at `xhigh`
- If llmx falls back to the OpenAI API, llmx's own default is `high` unless you pass `--reasoning-effort`

## Judge Names ≠ Model Names

| Context | Name |
|---------|------|
| llmx CLI | `gemini-3.1-pro-preview` |
| tournament MCP judges | `gemini25-pro` |

$ARGUMENTS
