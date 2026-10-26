# llmx footgun history and spend-measurement notes

<!-- moved-from llmx-guide/SKILL.md L17-29 2026-10-26 -->
## Dispatch layer and spend measurement (moved verbatim from SKILL.md)

> Moved verbatim from llmx-guide/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

For profile-based dispatch with a context manifest, `~/Projects/skills/scripts/llm-dispatch.py` exists — the dispatch layer behind research-ops/observe/sweep cycles, not a general recommendation; direct CLI dominates ad-hoc usage. Library callers wanting structured status (not exceptions alone): `from llmx import dispatch, DispatchResult`.

> Detail files: [transport-routing.md](references/transport-routing.md) | [bare-lean-dispatch.md](references/bare-lean-dispatch.md) | [models.md](references/models.md) | [error-codes.md](references/error-codes.md) | [codex-dispatch.md](references/codex-dispatch.md) | [subcommands.md](references/subcommands.md) | [batch-apis.md](references/batch-apis.md)

**Cheap/lean one-off?** Read [bare-lean-dispatch.md](references/bare-lean-dispatch.md): reasoning tokens bill as output (`-e low` is cheaper AND better); one-offs want a RAW messages call not an agent harness; bare invocations to strip MCPs (codex `-c mcp_servers={}`, claude `--system-prompt --tools "" --strict-mcp-config` on the free sub, cursor `--mode ask`); subscription-routing footguns. Contract-tested: `tests/test_cli_contracts.py` (run `LIVE_CLI=1 pytest` after any codex/claude/cursor update).

**Measuring spend / "cost per X"?** Don't build a usage dispatcher — llmx already logs every
**API-transport** call (prompt/completion/**reasoning**/cached tokens + **caller**) to
`~/.claude/llmx-usage.jsonl`; `python ~/Projects/llmx/scripts/usage_summary.py --by caller` rolls it
to estimated `$` (reasoning counted as output). Caveats: ~~CLI/subscription transports log NULL tokens
(only API transports metered)~~ [stale: claude-cli, grok-cli and codex-cli log real tokens; `prompt_tokens`
is TOTAL input, partitioned by `cached_tokens`/`cache_write_tokens` — footgun 12]; the PRICING table goes
stale — fix it in place, don't fork.

<!-- moved-from llmx-guide/SKILL.md L97-117 2026-10-26 -->
## Footgun history (full table) (moved verbatim from SKILL.md)

> Moved verbatim from llmx-guide/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

## Footgun history (brief)

| # | Trap | Fix |
|---|------|-----|
| 1 | Gemini "free CLI" | Retired 2026-05-31; paid API + `--flex` |
| 2 | GPT xhigh timeout | `--timeout 1800–3600`; `--max-tokens` = visible-output budget (reasoning headroom added) |
| 3 | Shell `> file` / pipelines | `-o` + `set -o pipefail`; don't `2>/dev/null` diagnostics |
| 4 | `shell=True` + parens in prompt | List args + `input=` |
| 5 | Model name 404s | Hyphens not dots; see [models.md](references/models.md) |
| 6 | Historical Fable downshifts / billing confusion | Current 5.1 route: `--subscription -m claude-fable-5-1`. Max includes a limited Fable allowance; do not fall back to paid API or usage credits without authorization. Agent-tool Fable pins need separate verification — see `/model-guide`. |
| 7 | Grok 4.20 `--reasoning-effort` | Errors on reasoning variant; >200K input = 20× price tier |
| 7b | Grok Cursor slugs rotate with the model | Verified live 2026-09-23: current pin is `grok-4.7-{low,medium,high,xhigh}[-fast]` — **no `cursor-` prefix** (a 2026-09-22 guess assumed `cursor-grok-4.7-*`, which does not exist); 4.6 slugs (`cursor-grok-4.6-*`) retired from routing 2026-09-25. Rederive from `cursor-agent models`, never from memory. `-e` is ignored on cursor-cli. Bare `grok-4.7` is xAI / Grok Build (`llmx chat -p grok`). `grok` CLI updated to 1.0.41, lists 4.7 as default. |
| 7c | Grok 4.5 xAI API 403 | `API key is currently blocked` — **key status**, not EU geo (Chicago Mullvad egress still 403'd 2026-07-09). Rotate/unblock key in console; Cursor pool is the live path meanwhile. |
| 7d | Critique `grok` vs llmx cursor | `grok` axis uses `cursor-agent --workspace` (repo). `llmx -p cursor` uses neutral empty cwd (packet-only). Don't substitute. |
| 8 | Shelling llmx from Python: `subprocess.run(capture_output=True, timeout=)` hangs forever at 0% CPU | run()'s TimeoutExpired kills the child then blocks draining a pipe the llmx→claude-CLI grandchild holds. Use `Popen(start_new_session=True)` + `communicate(timeout)` + `os.killpg` on expiry (exemplar: arc-agi `agent/foundry_ewm.py llm()`; 27-min wedge 2026-07-04) |
| 9 | `--mode agent -e max` inherited the 300s chat default | Fixed in llmx `99de7a5`: agent floor 1800s, max floor 3600s; zero-byte `-o` after timeout is transport failure, never reviewer evidence |
| 9 | `--mode agent` launches in `~/.cache/llmx/lite/research` with no repo tools | Fixed 2026-07-10: mode and lite profile are separate. Workspace agent preserves caller cwd; `--lite research` stays isolated. Live-smoke with `pwd` + `git log` after changes. |
| 10 | Claude subscription call fails before dispatch when `--max-tokens` is set | Claude CLI does not expose that control. Omit `--max-tokens`; use explicit `--timeout` and let the model's native output ceiling apply. Subscription routes fail loud rather than silently billing API fallback. |
| 11 | Claude chat call returns rc=0 with the model's reply to a user Stop hook in place of the answer (the empty cwd skipped project settings, not user hooks) | Fixed in llmx `72866bc`: chat and `--lite research` calls pass `disableAllHooks`, and a turn injected after the answer fails loud. Workspace `--mode agent` keeps hooks. Still validate outputs by content, never by rc alone. |
| 12 | claude-cli/grok-cli usage rows logged `prompt_tokens` = Anthropic `input_tokens` (excludes cache; e.g. 2 of ~25k) and dropped `cache_creation_input_tokens`; reasoning was double-counted in output | Fixed 2026-10-12 (`_anthropic_shaped_usage` in `cli_backends.py`): prompt = input + cache read + cache write, `cache_write_tokens` logged, `completion_includes_reasoning=True`, claude `reported_cost_usd` kept. Unknown usage token fields or missing cache fields write a `[DEGRADED]` note + stderr warning. Rows before 2026-10-12 under-report input. Regression: `tests/test_usage_accounting.py` live fixture. |
| 13 | `--mode agent` with no `--auth` on an OpenAI/Gemini model silently ran a metered API chat: default auth=api downgraded agent to chat (3 reviews died on "Invalid API key", 2026-10-14) | Fixed in llmx `41b8462`: explicit `--mode agent` implies `--auth subscription` (one `[llmx]` stderr line); explicit api (`--auth api`, `-p anthropic-direct`) + agent exits 2; a model with no subscription CLI (Gemini) exits 2. CLI, dispatch API and Python `chat()`/`LLM()` share `mode.resolve_auth_mode`. |
