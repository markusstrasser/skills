# Bare / Lean Dispatch — cheapest correct way to call codex / claude / cursor / gemini

Project-agnostic. Applies to ANY one-off LLM call or subagent config: extraction,
classification, judging, a quick agentic task. Measured 2026-06-16; contract-tested by
`../tests/test_cli_contracts.py` (run after a CLI update).

## The cost trap: reasoning tokens BILL AS OUTPUT
Thinking models (gemini-3-flash, GPT-5.x, Opus, Composer) emit reasoning tokens that
**count as output tokens on the bill** — and gemini-flash "thinks" even at
`reasoning_effort=null` (~4–5K reasoning/call ≈ 45% of output). **Any cost estimate that
sums only `completion_tokens` is ~40× low** (a real probe reported $1.16 for a run that
tracked ~$40–78). Always count `completion + reasoning`. And: **`-e low` is usually
cheaper AND better for structured work** — measured gemini-flash `-e low` beat default
thinking on quality (1.17×), cost (4×), and speed (4×); default over-reasoning *hurt*.
Set `-e low` for extraction/classification; reserve high effort for open synthesis.

## One-offs want a RAW MESSAGES call, NOT an agent
An *agent* CLI (codex exec, claude/cursor default mode) carries a large harness system
prompt + tool defs, **re-sent every turn** — pure overhead for a one-shot "text → JSON".
Measured floor for one doc:

| path | tokens/doc | $ | when |
|---|---|---|---|
| gemini `-e low` (raw API) | **~2.6K** | paid-cheap | the floor; default for cheap one-offs |
| claude sub, `--system-prompt` lean | ~4–5K | **$0 (OAuth sub)** | free lean one-off |
| codex agent (bare) | 56K | $0 (sub) | only when you need agency |
| cursor agent / Cloud-Agents API | 38–56K | metered | only to benchmark Composer |

Rule: **one-off = raw messages** (gemini paid-lean, or claude-sub `--system-prompt`).
Reach for an agent only when the task genuinely needs tools/multi-step.

## BARE invocations (strip MCPs + harness) — per CLI
- **codex** (ChatGPT sub, free): `codex exec --full-auto -c model_reasoning_effort="low" -c 'mcp_servers={}' -C <clean-dir> "<task>"`. The `-c mcp_servers={}` strips ~37–50K of MCP tool descriptions (a 12-server config = 56K→ much less, ~6.6× cut). `-c model_reasoning_effort=...` **does** override the config default (verified in `~/.codex/sessions/*.jsonl`). It's still an AGENT — completion-style ("here's text, return JSON") returns `[]`; use it agentically (point at files, write output to a file).
- **claude** (OAuth sub, free): `env -u ANTHROPIC_API_KEY -u CLAUDE_API_KEY claude -p --system-prompt "<minimal>" --tools "" --strict-mcp-config --output-format json`. `--system-prompt` **REPLACES** the Claude-Code harness (there's also `--system-prompt-file`); `--strict-mcp-config` drops project MCPs; `--tools ""` drops tools. Key-stripped env = subscription, not API billing. This is the lean FREE one-off.
- **cursor**: `cursor-agent -p --mode ask --model composer-2.5 --output-format text "<task>"`. **`--mode ask`** is the lightweight read-only Q&A path (the bundle's "ephemeral question" system prompt, NOT the agent harness) — ~16× faster than agent mode (14s vs 224s for a small doc). The CLI reports no token count (latency is the lean proxy); meter via the Cloud Agents `/v1/agents/{id}/usage` endpoint.

## Subscription routing gotchas (llmx)
- `llmx chat -m gpt-5.5 --subscription` **silently falls back to `openai-api` (PAID)** — saw `transport: openai-api`. Use **`-p codex-cli`** to stay on the ChatGPT sub.
- `composer-2.5` is **blocked in llmx sub-mode** ("restricted to frontier models: opus / gemini-flash / gpt-5.5; use --auth api"). Reach Composer via `cursor-agent` directly, not llmx sub.
- **gemini has NO sub route** (free CLI retired 2026-05-31) — always paid API (cheap with `-e low`/`--flex`).
- **Subsidy map:** ChatGPT (codex) + Claude (OAuth) subs are *subsidized* (~$0 marginal). **Cursor's pool is METERED** ($0.50/$2.50 Composer Standard) — "sub" but not free.

## Cursor: Composer is agent-only (no lean raw endpoint)
- Composer 2.5 has **no third-party messages/completions API** — IDE / SDK / agent only.
- Programmatic = the **Cloud Agents API** (`POST api.cursor.com/v1/agents`): durable agent + per-prompt *runs*, repo/PR-oriented (no-repo agents allowed), async, **reports tokens** (`/usage`). But agent-heavy (~38K/run, ~21K of it cache-read harness). Benchmark-only; never lean.
- The lean Composer path is the **local `cursor-agent --mode ask`** above.

## These flags change — the tripwire
Providers rename flags + reroute silently. `../tests/test_cli_contracts.py` asserts the
load-bearing flags (`-c`, `--system-prompt`, `--strict-mcp-config`, `--mode ask`,
`--api-key`) and (gated `LIVE_CLI=1`) that bare/ask/sub modes still work + stay on the
sub. Run it after any codex/claude/cursor update.
