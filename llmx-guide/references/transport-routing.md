<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Transport Routing & CLI Details

## CLI-First Usage (Subscription Pricing)

Gemini CLI and Codex CLI use flat subscription pricing — zero marginal cost per query. Prefer them for routine tasks.

### CLI Backends

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

### When to Use CLIs vs API

| Use CLI when | Use API when |
|-------------|-------------|
| Simple Q&A, summaries, reviews | Need `--max-tokens` (Gemini CLI caps at 8K) |
| Output fits in 8K tokens | Need structured output (`--schema`) |
| Don't need streaming | Need `--stream` for progressive output |
| Cost matters (subscription = free) | Need search grounding (`--search`) |

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

Note: in both cases, `<system>...</system>` is prompt text, not a transport-level system role. The model treats it as advisory text rather than a hard system channel.

### Context Budget

Neither CLI truncates user input (verified from source code). Input goes directly to API.

| Backend | Model context | Practical limit | Input truncation? |
|---------|--------------|-----------------|-------------------|
| Gemini CLI | 1M tokens (~4MB) | ~200KB before slowdown | No — 400 error if exceeded |
| Codex CLI | 272K-848K tokens | ~200KB+ | No — auto-compacts history |
| API (Gemini) | 1M tokens | Full window | No |
| API (GPT-5.4) | 1M tokens | Full window | No |

**Tested:** 80KB code batches via both CLIs work reliably. 200KB causes timeouts on thinking models.

**What forces API transport** (costs money): `--max-tokens`, `--stream`, `--search`. For Gemini, avoid `--stream` unless CLI rate-limited — without it, calls route through CLI (free). Hang bug on thinking models fixed in gemini-cli 0.32.1+.

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
