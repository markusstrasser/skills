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
5. **Model name format?** No provider prefixes needed (`gemini-3.1-pro-preview` not `gemini/gemini-3.1-pro-preview`). Old prefixed names still accepted with deprecation warning.
6. **Know the transport and fallback triggers:** `openai` prefers `codex exec`, `google` prefers `gemini`. Falls back to API for: `--schema`, `--search`, `--stream`, `--max-tokens`

## When llmx Fails — Diagnose, Don't Downgrade

**Never swap to a weaker model as a "fix."** If GPT-5.4 or Gemini Pro fails, the problem is the dispatch — not the model. Switching to Flash or GPT-5.2 loses the capability you needed.

**Diagnostic steps (in order):**
1. Check exit code: `echo $?` — tells you rate limit (3), timeout (4), or model error (5)
2. Check stderr: llmx prints JSON diagnostics to stderr (v0.6.0+): `{"error": "rate_limit", "provider": "google", "model": "...", "exit_code": 3, "action": "wait and retry"}`
3. Check for transport switch warnings: `[llmx:TRANSPORT] gemini-cli → google-api (max_tokens not supported by CLI)`
4. Check for truncation warnings: `[llmx:WARN] output may be truncated`
5. Re-run with `--debug` on a small prompt to isolate
6. Common fixes: increase `--timeout`, add `--stream`, reduce context size, check API key

## Model Names & Defaults

| Model | llmx name | Notes |
|-------|-----------|-------|
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | **Default Google model.** `google` prefers Gemini CLI when installed |
| Gemini 3 Flash | `gemini-3-flash-preview` | Cheap. `-preview` required |
| Gemini 3.1 Flash Image | `gemini-3.1-flash-image-preview` | No text-only 3.1 Flash yet |
| GPT-5.3 Instant | `gpt-5.3-chat-latest` | Reasoning max: **medium only**. Auto-defaults |
| GPT-5.4 | `gpt-5.4` | **Default OpenAI model.** `openai` prefers Codex CLI when installed. API fallback defaults reasoning to `high`; `xhigh` is also supported. |
| GPT-5.2 (legacy) | `gpt-5.2` | Legacy OpenAI default. |
| GPT-5-Codex | `gpt-5-codex` | No `minimal` reasoning-effort |
| Kimi K2.5 | `kimi-k2.5` | No `--reasoning-effort`. Use `--no-thinking` |
| Kimi K2 (legacy) | `kimi-k2-thinking` | Use `--use-old` flag |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Hyphens, not dots |

**Model name format (v0.6.0+):** No provider prefixes needed. Use `gemini-3.1-pro-preview` not `gemini/gemini-3.1-pro-preview`. Old LiteLLM-style prefixed names (`gemini/`, `openai/`, `xai/`, `moonshot/`) still accepted with deprecation warning. Will be removed in a future version.

**Model name suggestions:** If you typo a model name, llmx suggests the closest match: `"gemini-3.1-pro not found; did you mean gemini-3.1-pro-preview?"`

**404 traps:** `gemini-3-flash` (missing `-preview`), `gemini-flash-3` (wrong order), `gpt-5.3` (needs `-chat-latest` suffix).

## Token Limits

| Model | Max Input | Max Output | Notes |
|-------|----------|-----------|-------|
| GPT-5.4 | 1,050,000 | 128,000 | |
| GPT-5.2 | 272,000 | 128,000 | |
| GPT-5.3 Chat | 128,000 | 16,384 | Smallest output cap — watch for truncation |
| o4-mini | 200,000 | 100,000 | |
| Gemini 3.1 Pro | 1,048,576 | 65,536 | Server default is 8K — always pass `--max-tokens 65536` |
| Gemini 3 Flash | 1,048,576 | 65,535 | |

## Error Handling (v0.6.0+)

**Exit codes** — branch on these, don't parse stderr:
| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | — |
| 1 | General error | Read stderr for details |
| 2 | API key missing/invalid | Check env vars |
| 3 | Rate limit (429/503, transient) | Wait, or add `--stream` (API transport has separate capacity from CLI) |
| 4 | Timeout | Increase `--timeout`, or add `--stream` for API transport |
| 5 | Model error (context too large, bad params) | Fix request |
| 6 | **Quota/billing exhausted** (permanent) | Top up billing. NOT transient — retries won't help |

**Structured diagnostics** on stderr (JSON, v0.6.0+):
```json
{"error": "rate_limit", "provider": "google", "model": "gemini-3.1-pro-preview", "exit_code": 3, "action": "wait or use --stream (API transport)"}
```

**Additional stderr signals (v0.6.0+):**
- Transport switch: `[llmx:TRANSPORT] gemini-cli → google-api (max_tokens not supported by CLI)`
- Truncation warning: `[llmx:WARN] output may be truncated`
- Model suggestion: `"gemini-3.1-pro not found; did you mean gemini-3.1-pro-preview?"`

**`--fallback MODEL`** — exists but **not recommended**. Silent model switching masks failures. If you asked for Pro, you should get Pro or an error. Prefer `--stream` (forces API transport, bypasses CLI capacity limits) over `--fallback` (switches to a weaker model).

**From Python — check exit code and diagnose:**
```python
result = subprocess.run(
    ['llmx', '-m', 'gemini-3.1-pro-preview', '--stream', '--timeout', '300'],
    input=prompt, capture_output=True, text=True, timeout=360
)
if result.returncode == 3:  # rate limit — API transport has separate capacity
    print(f"Rate limited: {result.stderr}")
elif result.returncode == 4:  # timeout
    print(f"Timeout: {result.stderr}")
```

## The Five llmx Footguns

### 1. Gemini CLI Hangs on Context Files with Thinking Models

Gemini CLI transport (`gemini-cli`) hangs indefinitely when given context files (`-f`) with thinking models (Pro, Flash thinking). The process consumes CPU but never produces output or times out. Observed with files as small as 5KB.

**Root cause:** Unknown — likely Gemini CLI's thinking mode interacts badly with piped file context. Non-thinking Flash works fine on the same files.

**Fix:** Always use `--stream` when dispatching review/analysis prompts with `-f` context files to Gemini thinking models. `--stream` forces API transport, which works reliably.

```bash
# HANGS — Gemini CLI transport with context file + thinking model:
llmx chat -m gemini-3.1-pro-preview -f context.md --timeout 300 "Review this"

# WORKS — --stream forces API transport:
llmx chat -m gemini-3.1-pro-preview -f context.md --timeout 300 --stream "Review this"

# WORKS — Flash (non-thinking) on CLI transport:
llmx chat -m gemini-3-flash-preview -f context.md --timeout 120 "Review this"
```

**Impact on model-review skill:** All Gemini Pro dispatches with `-f` must include `--stream`. This forces API transport (costs money instead of free CLI), but is the only reliable path. Budget ~$0.01-0.05 per review at 5-30KB context.

### 2. GPT-5.x Timeouts and max_completion_tokens

GPT-5.4 (and 5.2) with reasoning burns time BEFORE producing output. Non-streaming holds the connection idle during reasoning — proxies and HTTP clients kill idle connections. Default is 300s (since llmx 0.5.2).

**Max timeout: 900s** (validated at CLI level, 1-900 range). For review dispatches use `--timeout 600`.

**Wall-clock enforcement:** SDK calls run in a daemon thread with `join(remaining_time)`. If SIGALRM can't interrupt a C-level SSL read, the thread join ensures the main thread regains control.

**`max_completion_tokens` vs `max_tokens` (v0.6.0+):** GPT-5.x uses `max_completion_tokens` not `max_tokens` at the API level. llmx handles this automatically — `--max-tokens` maps to the correct parameter per provider. **Important:** for reasoning models, `max_completion_tokens` includes reasoning tokens. If you set `--max-tokens 4096` on GPT-5.4 with reasoning, the model may exhaust the budget on thinking and produce truncated output. Use 16K+ for reasoning models.

**Google server-side deadline (v0.6.0+):** Google models now use a server-side deadline timeout (via `google-genai` SDK) instead of SIGALRM. Minimum 10s. This eliminates the old SIGALRM hang problem where streaming keepalives could prevent timeout enforcement.

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
2. Set Bash tool `timeout: 660000` (11 min) — must exceed llmx's `--timeout` value
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
| Gemini 3 Flash | low, medium, high | high (server-side, via `thinking_config`) |
| Gemini 3.x (Pro/Flash) | low, medium, high | high (server-side, via `thinking_config`) |
| Kimi K2.5 | N/A — use `--no-thinking` | thinking on |

Temperature locked to 1.0 for GPT-5 and Gemini 3.x thinking models.

**Google API note:** Google uses `thinking_config` with `thinking_level` (not `reasoning_effort`) under the hood. llmx translates `--reasoning-effort` to the correct parameter per provider — you don't need to know this unless debugging raw API calls.

**OpenRouter streaming guard (v0.6.0+):** OpenRouter occasionally sends empty `choices` arrays in streaming chunks. llmx now guards against this — if you see `IndexError` on `choices[0]` in older versions, upgrade.

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
llmx -p claude "question"       # Claude CLI backend (v0.6.0+, non-nested contexts only)
llmx -p gemini-cli "question"   # force Gemini CLI transport
llmx -p codex-cli "question"    # force Codex CLI transport
```

Falls back to API for:

- Gemini CLI: `--schema`, `--search`, `--stream`, `--max-tokens`
- Codex CLI: `--search`, `--stream`
- Both CLIs ignore explicit `--reasoning-effort`; they use their own default thinking behavior
- Codex CLI now handles `--schema` via `codex exec --output-schema`
- `--max-tokens` forces API because Gemini CLI defaults to 8K with no override
- `--output` works with both CLI and API transport (Python-level, not shell)

### System Prompts with CLIs

`-s` / `--system` now works with CLI transport. System messages are folded into the prompt as `<system>...</system>` XML tags, so `-s` no longer forces API fallback.

Both approaches work:

```bash
# Using -s flag (now stays on CLI — system text folded into prompt as <system> XML)
llmx -p openai -m gpt-5.4 --timeout 600 -s "You are reviewing code. Be concrete." "Review this design"

# Inline system tags (equivalent, also stays on CLI)
cat <<'EOF' | llmx chat -p openai -m gpt-5.4 --timeout 600
<system>
You are reviewing code. Be concrete. Reference specific files and tradeoffs.
</system>

Review this design:
- ...
EOF
```

Note: in both cases, `<system>...</system>` is prompt text, not a transport-level system role. The model treats it as advisory text rather than a hard system channel. The behavior is identical whether you use `-s` or inline tags.

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

## CLI-First Usage (Subscription Pricing)

Gemini CLI and Codex CLI use flat subscription pricing — zero marginal cost per query. Prefer them for routine tasks.

### When to Use CLIs vs API

| Use CLI when | Use API when |
|-------------|-------------|
| Simple Q&A, summaries, reviews | Need `--max-tokens` (Gemini CLI caps at 8K) |
| Output fits in 8K tokens | Need structured output (`--schema`) |
| Don't need streaming | Need `--stream` for progressive output |
| Cost matters (subscription = free) | Need search grounding (`--search`) |

### Piping Context Files

CLIs accept `-f FILE` for context. Use `.claude/overviews/` (5-10KB compressed project summaries) for codebase-aware queries at zero cost:

```bash
# Code review with project context (Gemini CLI, free)
llmx -p google -f .claude/overviews/source-overview.md "Review the error handling in the orchestrator pipeline"

# Architecture question (Codex CLI, free)
llmx -p openai -f .claude/overviews/source-overview.md -f .claude/overviews/tooling-overview.md "How does the telemetry pipeline flow?"

# Specific file review (pipe file as context)
llmx -p google -f src/providers.py "Find bugs in this code"
```

### Context Budget

Neither CLI truncates user input (verified from source code). Input goes directly to API.

| Backend | Model context | Practical limit | Input truncation? |
|---------|--------------|-----------------|-------------------|
| Gemini CLI | 1M tokens (~4MB) | ~200KB before slowdown | No — 400 error if exceeded |
| Codex CLI | 272K-848K tokens | ~200KB+ | No — auto-compacts history |
| API (Gemini) | 1M tokens | Full window | No |
| API (GPT-5.4) | 1M tokens | Full window | No |

**Tested:** 80KB code batches via both CLIs work reliably. 200KB causes timeouts on thinking models.

**What forces API transport** (costs money): `--max-tokens`, `--stream`, `--search`. For Gemini, `--stream` is recommended — CLI transport hits capacity limits (429) and hangs on thinking models.

### CLI for Agents (Claude Code / Codex)

When dispatching from an agent context:

```bash
# Quick codebase question (zero cost, ~5-15s)
llmx -p google -f .claude/overviews/source-overview.md "What files handle authentication?"

# Code review with inline system prompt (stays on CLI)
cat <<'EOF' | llmx -p openai -m gpt-5.4 -o review.md
<system>You are reviewing code. Be concrete. Reference specific files.</system>

$(cat src/main.py)

Review this for bugs and security issues.
EOF

# Batch review — loop over files (each call is free)
for f in src/*.py; do
  llmx -p google -f "$f" -o "reviews/$(basename "$f").md" "Review this file for bugs"
done
```

`-s` works with CLIs — system messages are folded into the prompt as `<system>` XML tags, staying on CLI transport.

## Judge Names ≠ Model Names

| Context | Name |
|---------|------|
| llmx CLI | `gemini-3.1-pro-preview` |
| tournament MCP judges | `gemini25-pro` |

$ARGUMENTS
