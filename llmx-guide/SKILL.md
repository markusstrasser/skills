---
name: llmx-guide
description: Critical gotchas when calling llmx from Python or Bash. Non-obvious bugs and incompatibilities. Use when writing code that calls llmx, debugging llmx failures, or choosing llmx model/provider options.
user-invocable: true
argument-hint: '[model name or issue description]'
effort: medium
---

# llmx Quick Reference

> Detail files in `references/`: [models.md](references/models.md) | [error-codes.md](references/error-codes.md) | [transport-routing.md](references/transport-routing.md) | [codex-dispatch.md](references/codex-dispatch.md) | [subcommands.md](references/subcommands.md)

## Before You Call llmx — Checklist

1. **Model name correct?** Hyphens not dots (`claude-sonnet-4-6` not `claude-sonnet-4.6`)
2. **Timeout set?** Reasoning models need `--timeout 600` or `--stream`. Max allowed: **900s**. GPT-5.4 xhigh can exceed this on domain-heavy prompts.
3. **Using `shell=True`?** Don't — parentheses in prompts break it. Use list args + `input=`
4. **Using `-o FILE`?** Never use `> file` shell redirects — they buffer until exit
5. **No provider prefixes needed.** `gemini-3.1-pro-preview` not `gemini/gemini-3.1-pro-preview`.
6. **Know the transport triggers:** `google` prefers `gemini` CLI (free). Falls back to API for: `--schema`, `--search`, `--stream`, `--max-tokens`. GPT goes direct to API.
7. **Hangs in agent context?** Claude Code's Bash tool pipes stdin without EOF. Fixed in current llmx (skips stdin when prompt provided).
8. **Prompt is positional, context is `-f`.** `llmx "analyze this" -f context.md` — prompt as first positional arg, context files as `-f`. Two `-f` flags with no positional = no prompt = model invents a task from the context. (Evidence: 2026-04-05 — Gemini received two `-f` files, hallucinated a script implementation instead of analysis.)

## When llmx Fails — Diagnose, Don't Downgrade

**Never swap to a weaker model as a "fix."** The problem is the dispatch, not the model.

1. Check exit code: 3=rate-limit, 4=timeout, 5=model-error, 6=billing-exhausted (permanent, don't retry)
2. Check stderr JSON diagnostics
3. Check for transport switch / truncation warnings
4. Re-run with `--debug` on a small prompt
5. Common fixes: increase `--timeout`, add `--stream`, reduce context, check API key

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

### 2. GPT-5.x Timeouts

GPT-5.4 with reasoning burns time BEFORE producing output. Non-streaming holds the connection idle during reasoning. Default timeout: 300s. Max: **900s** (hard cap). GPT-5.4 xhigh on domain-heavy prompts can exceed 900s — use ChatGPT Pro for those.

**`max_completion_tokens` includes reasoning tokens.** If you set `--max-tokens 4096` on GPT-5.4 with reasoning, the model may exhaust the budget on thinking. Use 16K+ for reasoning models.

### 3. Output Capture — Use `-o FILE`, Never `> file`

```bash
# CORRECT:
llmx -m gpt-5.4 -f context.md --timeout 600 -o output.md "query"

# BROKEN — 0 bytes until exit:
llmx -m gpt-5.4 "query" > output.md
```

From Claude Code: set Bash tool `timeout: 660000` (11 min) — must exceed llmx's `--timeout`.

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

See [models.md](references/models.md) for full model table, token limits, and reasoning effort values.

## Transport Routing Summary

| Provider | Default transport | Forces API fallback |
|----------|------------------|---------------------|
| `google` | Gemini CLI (free) | `--schema`, `--search`, `--stream`, `--max-tokens` |
| `openai` | Codex CLI (free) | `--search`, `--stream` |
| `claude` | Claude CLI | v0.6.0+, non-nested contexts only |

Both CLIs ignore explicit `--reasoning-effort` — they use their own defaults. See [transport-routing.md](references/transport-routing.md) for CLI vs API decision table, context budget, piping patterns.

## Codex `-o` Gotcha (Parallel Dispatch)

`-o FILE` captures the agent's **last text message only**. If the agent spends all turns on tool calls with no final text response, `-o` writes 0 bytes. Prompt **must** include: `"End with a COMPLETE markdown report as your final message."` Without this, ~50% produce empty output.

See [codex-dispatch.md](references/codex-dispatch.md) for full parallel dispatch pattern, Brave contention, Perplexity quota.

## Subcommands

`llmx research`, `llmx image`, `llmx vision`, `llmx svg`. Flags: `--fast` (Flash+low), `--use-old`, `--no-thinking`. See [subcommands.md](references/subcommands.md).

$ARGUMENTS
