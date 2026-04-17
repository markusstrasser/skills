<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Transport Routing & CLI Details

## CLI-First Usage (Subscription Pricing)

Gemini CLI and Codex CLI use flat subscription pricing — zero marginal cost per query. Prefer them for routine tasks.

### CLI Backends

```bash
llmx -p google "question"       # prefers Gemini CLI, falls back to API
llmx -p openai "question"       # uses OpenAI API
llmx -p claude "question"       # Claude CLI backend (v0.6.0+, non-nested contexts only)
llmx -p gemini-cli "question"   # force Gemini CLI transport
llmx -p codex-cli "question"    # force Codex CLI transport
llmx -p xai "question"          # xAI API (OpenAI-compatible at https://api.x.ai/v1)
```

Falls back to API for:

- Gemini CLI: `--schema`, `--search`, `--stream`, `--max-tokens`
- Codex CLI: `--search`, `--stream`
- Both CLIs ignore explicit `--reasoning-effort`; they use their own default thinking behavior
- Codex CLI now handles `--schema` via `codex exec --output-schema`
- `--max-tokens` forces API because Gemini CLI defaults to 8K with no override
- `--output` works with both CLI and API transport (Python-level, not shell)

Current routing detail:

- logical `openai` does **not** prefer Codex CLI anymore
- Codex CLI is opt-in via `-p codex-cli`
- this avoids startup overhead and CLI-specific limit surfaces for routine GPT calls

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
# Using -s flag with the API transport
llmx -p openai -m gpt-5.4 --timeout 600 -s "You are reviewing code. Be concrete." "Review this design"

# Inline system tags (equivalent prompt text)
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

### Gemini API Service Tiers

When API transport is needed (or CLI free tier is restricted), select the tier via `service_tier`:

| Tier | Discount | Latency | Use case |
|------|----------|---------|----------|
| Standard | 0% | seconds | Interactive, default |
| Flex | 50% | 1-15 min target | Cron jobs, background reviews, session-analyst, non-interactive dispatch |
| Priority | +75-100% | sub-second | Not needed for our workloads |
| Batch | 50% (async) | up to 24h | Bulk embedding/eval jobs — requires async rewrite |

**Default for scheduled/background work: Flex.** Same discount as Batch, synchronous (no code rewrite). Flex is "sheddable" (preempted under load), acceptable for non-user-facing dispatch.

**Implicit caching** auto-enabled on Gemini 2.5+. Repeated system prompts get cache hits automatically — no explicit cache setup needed for our pattern of skill preambles + varying user content.

**Note:** llmx does not yet support `service_tier` — would need implementation when/if CLI free tier is restricted.

### Piping Context Files

CLIs accept `-f FILE` for context. Use `.claude/overviews/` (5-10KB compressed project summaries) for codebase-aware queries at zero cost:

For critical review flows, prefer **one combined context file** over multiple
`-f` inputs. Multi-file `-f` has recurring loss/truncation issues in real use.

```bash
# Code review with project context (Gemini CLI, free)
llmx -p google -f .claude/overviews/source-overview.md "Review the error handling in the orchestrator pipeline"

# Architecture question (OpenAI API by default) — combine first for reliability
cat .claude/overviews/source-overview.md .claude/overviews/tooling-overview.md > combined-context.md
llmx -p openai -f combined-context.md "How does the telemetry pipeline flow?"

# Specific file review (pipe file as context)
llmx -p google -f src/providers.py "Find bugs in this code"
```

### CLI for Agents (Claude Code / Codex)

When dispatching from an agent context:

```bash
# Quick codebase question (zero cost, ~5-15s)
llmx -p google -f .claude/overviews/source-overview.md "What files handle authentication?"

# Code review with inline system prompt (API by default)
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

`-s` also works with CLI transports because llmx folds system text into the prompt as `<system>` XML.

### Codex CLI Reasoning Default

`llmx -p codex-cli` inherits Codex CLI's own reasoning default. llmx does **not** pass a reasoning-effort flag to `codex exec`.

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

- `llmx -p codex-cli ...` on a machine with `model_reasoning_effort = "xhigh"` uses Codex CLI at `xhigh`
- If llmx falls back to the OpenAI API, llmx's own default is `high` unless you pass `--reasoning-effort`
