---
name: llmx-guide
description: Critical gotchas when calling llmx from Python or Bash. Non-obvious bugs and incompatibilities. Use when writing code that calls llmx, debugging llmx failures, or choosing llmx model/provider options.
user-invocable: true
argument-hint: '[model name or issue description]'
effort: medium
---

# llmx Quick Reference

Most agents should not call `llmx` directly for normal repo automation. Use the shared wrapper first:

```bash
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile fast_extract \
  --context context.md \
  --prompt "Analyze this" \
  --output result.md
```

If the context was built by the shared packet layer, pass its manifest too:

```bash
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile fast_extract \
  --context context.md \
  --context-manifest context.manifest.json \
  --prompt "Analyze this" \
  --output result.md
```

Use this skill when:
- debugging shared dispatch failures
- writing or reviewing low-level code that calls `llmx.api.chat()`
- doing manual terminal work where raw CLI transport matters

Agent note: the repo hook blocks raw `llmx` chat-style Bash automation. The CLI examples below are for manual terminal debugging or maintainer reference, not for normal agent execution through the Bash tool.

> Detail files in `references/`: [models.md](references/models.md) | [error-codes.md](references/error-codes.md) | [transport-routing.md](references/transport-routing.md) | [codex-dispatch.md](references/codex-dispatch.md) | [subcommands.md](references/subcommands.md)

## Before You Call llmx — Checklist

1. **Model name correct?** Hyphens not dots (`claude-sonnet-4-6` not `claude-sonnet-4.6`)
2. **Timeout set?** Reasoning models need `--timeout 600` or `--stream`. Max allowed: **900s**. If dispatching from an agent shell, set the outer shell timeout above this (for Claude Code, use at least `1200000` ms).
3. **Using `shell=True`?** Don't — parentheses in prompts break it. Use list args + `input=`
4. **Using `-o FILE`?** Never use `> file` shell redirects — they buffer until exit
5. **No provider prefixes needed.** `gemini-3.1-pro-preview` not `gemini/gemini-3.1-pro-preview`.
6. **Know the transport triggers:** `google` prefers `gemini` CLI (free). Gemini falls back to API for: `--schema`, `--search`, `--stream`, `--max-tokens`. Codex CLI also falls back for `--search` and `--stream`, but can keep `--schema` via `codex exec --output-schema`. GPT goes direct to API unless you explicitly force `-p codex-cli`.
7. **Hangs in agent context?** Claude Code's Bash tool pipes stdin without EOF. Fixed in current llmx (skips stdin when prompt provided).
8. **Prompt is POSITIONAL, `-p` is PROVIDER.** `llmx chat -m gpt-5.4 -f context.md "Analyze this"` — prompt goes LAST as a bare string. `-p` means `--provider` (openai, google, codex-cli), NOT prompt. Using `-p "long text..."` sends the text as a provider name → "Unknown provider" error. Context goes in `-f`, system message in `-s`. Two `-f` flags with no positional prompt = model invents a task from context. (Evidence: 2026-04-05 — Gemini hallucinated; 2026-04-12 — 4 consecutive failures from `-p` misuse.)
9. **For critical reviews, use one combined context file.** Multi-file `-f` has recurring failure modes with Gemini/CLI transport, including silently dropping earlier files. Pre-concatenate first, but preserve file boundaries in the combined file.

## When llmx Fails — Diagnose, Don't Downgrade

**Never swap to a weaker model as a "fix."** The problem is the dispatch, not the model.

1. Check exit code: 3=rate-limit, 4=timeout, 5=model-error, 6=billing-exhausted (permanent, don't retry)
2. Check stderr JSON diagnostics
3. Check for transport switch / truncation warnings
4. Re-run with `--debug` on a small prompt
5. Common fixes: increase `--timeout`, add `--stream`, reduce context, check API key
6. **When transport matters, probe it.** Run one tiny `--debug` smoke test before assuming CLI vs API routing from docs or memory.

See [error-codes.md](references/error-codes.md) for full exit code table and Python patterns.

## The Five Footguns

### 1. Gemini CLI Transport — Free Tier

No `--stream` needed for Gemini. Without it, llmx routes through CLI (free tier). Add `--stream` only if CLI hits rate limits (forces paid API fallback).

```bash
# FREE — routes through Gemini CLI:
llmx chat -m gemini-3.1-pro-preview -f context.md --timeout 300 "Review this"

# FORCES API (costs money) — only use if CLI rate-limited:
llmx chat -m gemini-3.1-pro-preview -f context.md --timeout 300 --stream "Review this"
```

**What still forces API:** `--max-tokens` (CLI caps at 8K), `--schema`, `--search`, `--stream`.

### 1.5. Multi-File `-f` Is Not Reliable Enough For Critical Review Flows

If the task is high-stakes or review-oriented, do this:

```bash
awk 'FNR==1{print "\n# File: " FILENAME "\n"}1' overview.md diff.md touched-files.md > combined-context.md
llmx chat -m gemini-3.1-pro-preview -f combined-context.md --timeout 300 "Review this"
```

Do **not** assume this is equivalent:

```bash
llmx chat -m gemini-3.1-pro-preview -f overview.md -f diff.md -f touched-files.md --timeout 300 "Review this"
```

Known failure mode: earlier `-f` files may be silently dropped or incompletely
forwarded. This is acceptable for casual exploration, not for plan-close or
adversarial review.

### 2. GPT-5.x Timeouts

GPT-5.4 with reasoning burns time BEFORE producing output. Non-streaming holds the connection idle during reasoning. Default timeout: 300s. Max: **900s** (hard cap). GPT-5.4 xhigh on domain-heavy prompts can exceed 900s; for those, chunk the task, stream, or switch to an async/batch path if available. Do not punt operational work to a GUI tool.

**`max_completion_tokens` includes reasoning tokens.** If you set `--max-tokens 4096` on GPT-5.4 with reasoning, the model may exhaust the budget on thinking. Use 16K+ for reasoning models.

### 3. Output Capture — Use `-o FILE`, Never `> file`

```bash
# CORRECT — llmx writes the output file itself:
llmx -m gpt-5.4 -f context.md --timeout 600 -o output.md "query"

# BROKEN — 0 bytes until exit:
llmx -m gpt-5.4 "query" > output.md
```

`-o` does not imply `--stream`. Current llmx preserves the requested transport and writes the returned result itself when needed. If the file is still 0 bytes, llmx emits `[llmx:WARN]` to stderr.

**Agent background mode:** Claude Code's `run_in_background` captures stdout in its own task file. Shell redirects (`> file`) produce 0 bytes in background mode. Always use `-o` for background llmx calls. Read the `-o` file after the task-complete notification, not before.

For GPT specifically:

- default `llmx -m gpt-5.4` routes to the OpenAI API in current llmx
- `-o` preserves that transport; it does not force a transport switch
- if you explicitly use `-p codex-cli`, diagnose any failure from stderr and output size, not shell exit alone

If you need to verify the actual route, run:

```bash
llmx chat -p codex-cli -m gpt-5.4 --debug -o /tmp/probe.txt "Reply with exactly OK."
```

Then inspect the debug line for `transport`.

### 3.5. Shell Pipelines Can Hide llmx Failures

These are bad diagnostic patterns:

```bash
llmx chat -m gpt-5.4 "query" 2>/dev/null | head -200
llmx chat -m gpt-5.4 "query" | sed -n '1,80p'
```

Why:

- `2>/dev/null` discards llmx's real diagnostics
- without `set -o pipefail`, the shell returns the last consumer's exit code (`head`, `sed`), not llmx's
- an empty llmx response can look like success if the downstream command exits 0

Safer pattern:

```bash
set -o pipefail
llmx chat -m gpt-5.4 --debug -o /tmp/review.md "query" 2> /tmp/review.err
echo $?
tail -n 200 /tmp/review.err
sed -n '1,80p' /tmp/review.md
```

From Claude Code: set Bash tool `timeout: 1200000` (20 min) — it must exceed llmx's `--timeout`.

### 4. shell=True + Parentheses

```python
# BREAKS if prompt has ():
subprocess.run(f'echo {repr(prompt)} | llmx ...', shell=True)

# CORRECT — always use list args:
subprocess.run(['llmx', '--provider', 'google'], input=prompt, capture_output=True, text=True)
```

### 5. Model Name 404 Traps

- `gemini-3-flash` -- missing `-preview`
- `gemini-flash-3` -- wrong order
- `gpt-5.3` -- needs `-chat-latest` suffix
- `claude-sonnet-4.6` -- dots, needs hyphens
- `grok-4.20-reasoning` -- needs full `-0309-` snapshot suffix: `grok-4.20-0309-reasoning`. Not in llmx's `_RECOMMENDED_MODELS` — pass full name explicitly via `-m`.

See [models.md](references/models.md) for full model table, token limits, and reasoning effort values.

### 6. Grok 4.20 Reasoning — Three Footguns

Use `-p xai` (env: `XAI_API_KEY` or `GROK_API_KEY`). xAI is OpenAI-SDK-compatible at `https://api.x.ai/v1`.

1. **`--reasoning-effort` errors out** on `grok-4.20-0309-reasoning`. The model reasons automatically. Strip the flag from any wrapper before dispatching to xAI.
2. **Multi-agent variant repurposes `reasoning.effort`** — on `grok-4.20-multi-agent-0309`, `effort=low|medium`→4 agents, `effort=high|xhigh`→16 agents. **Selects agent count, not depth.** Cost scales with agent count.
3. **>200K input → 20× price tier** ($40/$120 per M instead of $2/$6). The 2M context window is operationally usable up to 200K only. Pre-summarize or chunk before exceeding.

Also: `logprobs` is silently ignored. xAI web search not yet supported via OpenAI SDK (llmx provider config explicitly warns and ignores `--search` for `xai`) — use Exa/Perplexity/Brave for grounding instead.

```bash
# Correct invocation (as of 2026-04-16)
llmx chat -p xai -m grok-4.20-0309-reasoning -f context.md --timeout 600 -o out.md "Verify these claims"

# WRONG — errors:
llmx chat -p xai -m grok-4.20-0309-reasoning --reasoning-effort high "..."

# WRONG — uses obsolete default model:
llmx chat -p xai "..."   # llmx default is still `grok-4`, superseded by 4.20 family
```

## Transport Routing Summary

| Provider | Default transport | Forces API fallback |
|----------|------------------|---------------------|
| `google` | Gemini CLI (free) | `--schema`, `--search`, `--stream`, `--max-tokens` |
| `openai` | OpenAI API | explicit `-p codex-cli` if you want Codex CLI instead |
| `claude` | Claude CLI | v0.6.0+, non-nested contexts only |

Both CLIs ignore explicit `--reasoning-effort` — they use their own defaults. See [transport-routing.md](references/transport-routing.md) for CLI vs API decision table, context budget, piping patterns.

## Codex `-o` Gotcha (Parallel Dispatch)

`-o FILE` captures the agent's **last text message only**. If the agent spends all turns on tool calls with no final text response, `-o` writes 0 bytes. Prompt **must** include: `"End with a COMPLETE markdown report as your final message."` Without this, ~50% produce empty output.

See [codex-dispatch.md](references/codex-dispatch.md) for full parallel dispatch pattern, Brave contention, Perplexity quota.

## Subcommands

`llmx research`, `llmx image`, `llmx vision`, `llmx svg`. Flags: `--fast` (Flash+low), `--use-old`, `--no-thinking`. See [subcommands.md](references/subcommands.md).

$ARGUMENTS
