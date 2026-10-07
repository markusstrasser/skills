# Bare / Lean Dispatch — cheapest correct way to call codex / claude / cursor / gemini

Project-agnostic. Applies to ANY one-off LLM call or subagent config: extraction,
classification, judging, a quick agentic task. Measured 2026-06-16; contract-tested by
`../tests/test_cli_contracts.py` (run after a CLI update).

## The cost trap: reasoning tokens BILL AS OUTPUT
Thinking models (gemini-3-flash, GPT, Opus, Grok) emit reasoning tokens that
**count as output tokens on the bill** — and gemini-flash "thinks" even at
`reasoning_effort=null` (~4–5K reasoning/call ≈ 45% of output). **Any cost estimate that
sums only `completion_tokens` is ~40× low** (a real probe reported $1.16 for a run that
tracked ~$40–78). Always count `completion + reasoning`. And: **`-e low` is usually
cheaper AND better for structured work** — measured gemini-flash `-e low` beat default
thinking on quality (1.17×), cost (4×), and speed (4×); default over-reasoning *hurt*.
Set `-e low` for extraction/classification; reserve high effort for open synthesis.

## Don't rebuild usage capture — llmx already logs it (incl. reasoning tokens + caller)
Before writing any per-call cost/usage dispatcher, know this exists: `llmx/usage_log.py`
records every **API-transport** call to `~/.claude/llmx-usage.jsonl` — prompt / completion /
**reasoning** / cached tokens **+ the caller** (which script/skill invoked it = cost attribution
per memo/job, for free). `python ~/Projects/llmx/scripts/usage_summary.py --by caller` rolls it
up to estimated **$** (a PRICING table; `out = completion + reasoning`, so reasoning is billed
correctly). So "cost per X" needs **no new dispatcher** — read the log. Two real caveats, both
fix-in-place not fork: (1) **CLI / subscription transports (codex-cli, claude-cli, cursor) log
NULL tokens** — those CLIs don't return a usage object, so only API transports (gemini paid API,
openai-api direct) are metered; a subscription run shows calls with empty token fields. (2) the
PRICING table is a **hardcoded constant that goes stale** (shows `+?` for unpriced models) — update
it in `usage_summary.py`, don't build a parallel pricer. A bespoke OpenAI-only dispatcher would
miss gemini/claude AND duplicate the capture llmx already does AND lose the caller attribution.

## One-offs want a RAW MESSAGES call, NOT an agent
An *agent* CLI (codex exec, claude/cursor default mode) carries a large harness system
prompt + tool defs, **re-sent every turn** — pure overhead for a one-shot "text → JSON".
Measured floor for one doc:

| path | tokens/doc | $ | when |
|---|---|---|---|
| gemini `-e low` (raw API) | **~2.6K** | paid-cheap | the floor; default for cheap one-offs |
| claude sub, `--system-prompt` lean | ~4–5K | **$0 (OAuth sub)** | free lean one-off |
| codex agent (bare) | 56K | $0 (sub) | only when you need agency |
| cursor agent / Cloud-Agents API | 38–56K | metered | only for the opt-in Grok lane |

Rule: **one-off = raw messages** (gemini paid-lean, or claude-sub `--system-prompt`).
Reach for an agent only when the task genuinely needs tools/multi-step.

## BARE invocations (strip MCPs + harness) — per CLI
- **codex** (ChatGPT subscription): for an explicitly isolated bare invocation, use `codex exec -s read-only --ignore-user-config -m <requested-model> -c model_reasoning_effort=low -C <clean-dir> "<task>"`. Select workspace-write only for authorized writes. This omits user configuration; supply required tools/settings explicitly. The Codex agent harness still exists, so measure the actual overhead for the task. See [current Codex mechanics](codex-dispatch.md).
- **claude** (OAuth sub, free): `env -u ANTHROPIC_API_KEY -u CLAUDE_API_KEY claude -p --system-prompt "<minimal>" --tools "" --strict-mcp-config --output-format json`. `--system-prompt` **REPLACES** the Claude-Code harness (there's also `--system-prompt-file`); `--strict-mcp-config` drops project MCPs; `--tools ""` drops tools. Key-stripped env = subscription, not API billing. This is the lean FREE one-off.
- **cursor**: `cursor-agent -p --mode ask --model grok-4.7-low --output-format text "<task>"` (Composer 2.5, the old default, was retired 2026-10-07; a model-less prompt run falls to it and is hook-blocked). **`--mode ask`** is the lightweight read-only Q&A path (the bundle's "ephemeral question" system prompt, NOT the agent harness) — ~16× faster than agent mode (14s vs 224s for a small doc). The CLI reports no token count (latency is the lean proxy); meter via the Cloud Agents `/v1/agents/{id}/usage` endpoint.

## Subscription routing gotchas (llmx)
- Verify the billing route with `llmx chat --dry-run --subscription -m <requested-model> "<task>"`; expect the intended subscription CLI transport before a live call. The earlier silent-fallback report is retained in [dispatch history](codex-dispatch-history.md), not treated as the current contract.
- `composer-2.5` / `composer-2.5-fast` were **retired 2026-10-07**; llmx refuses them with exit 2 and names the successor, `gpt-6-astra` at low effort (`llmx chat --subscription -m gpt-6-astra -e low`).
- **gemini has NO sub route** (free CLI retired 2026-05-31) — always paid API (cheap with `-e low`/`--flex`).
- **Subsidy map:** ChatGPT (codex) + Claude (OAuth) subs are *subsidized* (~$0 marginal). **Cursor's pool is METERED** at each model's rate — "sub" but not free.

## Cursor: agent-only (no lean raw endpoint)
- Cursor-served models have **no third-party messages/completions API** — IDE / SDK / agent only (measured on Composer 2.5, retired 2026-10-07).
- Programmatic = the **Cloud Agents API** (`POST api.cursor.com/v1/agents`): durable agent + per-prompt *runs*, repo/PR-oriented (no-repo agents allowed), async, **reports tokens** (`/usage`). But agent-heavy (~38K/run, ~21K of it cache-read harness). Benchmark-only; never lean.
- The lean cursor path is the **local `cursor-agent --mode ask`** above.

## These flags change — the tripwire
Providers rename flags + reroute silently. `../tests/test_cli_contracts.py` asserts the
load-bearing flags (`-c`, `--system-prompt`, `--strict-mcp-config`, `--mode ask`,
`--api-key`) and (gated `LIVE_CLI=1`) that bare/ask/sub modes still work + stay on the
sub. Run it after any codex/claude/cursor update.
