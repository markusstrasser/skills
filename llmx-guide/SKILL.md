---
name: llmx-guide
description: "Use when: /llmx-guide, writing llmx calls, debugging llmx failures, or choosing model/provider. Python/Bash gotchas — flags, transports, subscription vs API."
user-invocable: true
argument-hint: '[model name or issue description]'
effort: medium
---

# llmx Quick Reference

**Transport facts → mirror. Model judgment → `/model-guide`.** This skill is mechanics + footgun history only.

```bash
llmx info --write-mirror   # → ~/.claude/cache/llmx-routing.json — Read before dispatch
```

For profile-based dispatch with a context manifest, `~/Projects/skills/scripts/llm-dispatch.py` exists — the dispatch layer behind research-ops/observe/sweep cycles, not a general recommendation; direct CLI dominates ad-hoc usage. Library callers wanting structured status (not exceptions alone): `from llmx import dispatch, DispatchResult`.

> Detail files: [transport-routing.md](references/transport-routing.md) | [bare-lean-dispatch.md](references/bare-lean-dispatch.md) | [models.md](references/models.md) | [error-codes.md](references/error-codes.md) | [codex-dispatch.md](references/codex-dispatch.md) | [subcommands.md](references/subcommands.md) | [batch-apis.md](references/batch-apis.md)

**Cheap/lean one-off?** Read [bare-lean-dispatch.md](references/bare-lean-dispatch.md): reasoning tokens bill as output (`-e low` is cheaper AND better); one-offs want a RAW messages call not an agent harness; bare invocations to strip MCPs (codex `-c mcp_servers={}`, claude `--system-prompt --tools "" --strict-mcp-config` on the free sub, cursor `--mode ask`); subscription-routing footguns. Contract-tested: `tests/test_cli_contracts.py` (run `LIVE_CLI=1 pytest` after any codex/claude/cursor update).

**Measuring spend / "cost per X"?** Don't build a usage dispatcher — llmx already logs every
**API-transport** call (prompt/completion/**reasoning**/cached tokens + **caller**) to
`~/.claude/llmx-usage.jsonl`; `python ~/Projects/llmx/scripts/usage_summary.py --by caller` rolls it
to estimated `$` (reasoning counted as output). Caveats: CLI/subscription transports log NULL tokens
(only API transports metered); the PRICING table goes stale — fix it in place, don't fork.

## Canonical patterns

### Probe (before subscription dispatch or critique batches)

```bash
llmx chat --dry-run --subscription -m MODEL -e max
```

Critique harness (hard gate before parallel axes):

```bash
uv run python3 ~/Projects/skills/critique/scripts/model-review.py --preflight
# writes .model-review/preflight-latest.json; nonzero = transport/readiness failure — abort
```

### Subscription dispatch (`--subscription` replaces `--lite bare`)

**Claude: NEVER `anthropic-direct`/API by default.** Subscription only unless the user explicitly requests metered API billing.

```bash
llmx chat --subscription -m claude-opus-4-8 -f ctx.md -o out.md "query"
llmx chat -p codex-cli --subscription -m gpt-5.6-sol -f ctx.md -o out.md "query"
llmx chat --subscription -m cursor-grok-4.5-high -f ctx.md -o out.md "query"
```

Repository-coupled agent review (caller cwd, project rules, native CLI tools):

```bash
llmx chat --subscription --mode agent -m claude-opus-4-8 -e max \
  --timeout 3600 -o out.md "Inspect this repository read-only; cite file:line evidence."
```

`--mode agent` is a workspace agent. Legacy `--lite research` is an isolated
research-MCP-only profile; they are intentionally not aliases.

Strips API-key env on Claude/Codex subscription paths. If you see "Credit balance is too low", you hit API-key billing, not local subscription auth.

### Smoke (live, tiny)

```bash
llmx chat --subscription -m claude-opus-4-8 -e low \
  -o /tmp/llmx-claude-smoke.md "Reply exactly OK."
```

## Before You Call — checklist

1. **Read mirror** — `~/.claude/cache/llmx-routing.json` (regenerate with `llmx info --write-mirror`)
2. **Probe** — `--dry-run --subscription` or `model-review.py --preflight` before critique batches
3. **Prompt is POSITIONAL; `-p` is PROVIDER** in `llmx chat` (`llmx vision` inverts this)
4. **`-o FILE`** — never `> file`; background mode requires `-o`
5. **`--timeout` explicit** when the caller owns a tighter budget; `llmx` now defaults agent mode to
   at least 1800s and max effort to 3600s, but an explicit 1800–3600s bound remains clearer in scripts
6. **Context files** — repeatable `-f a.md -f b.md` concatenates with `=== File: path ===` boundaries (fixed; do not pre-merge unless you want a custom layout). Library: `llmx.api.dispatch(..., context_paths=[...])`.
7. **Gemini = paid API** since 2026-05-31; add `--flex` for 50% off non-interactive dispatch
8. **Exit 6 = billing exhausted (permanent)**; exit 3 = rate limit (retry/backoff)

## When llmx Fails

Never swap to a weaker model as a fix. Check exit code → stderr JSON → `--debug` probe on a tiny prompt. See [error-codes.md](references/error-codes.md).

## Audit-plan critique (mechanics only)

Routing table: `critique/lenses/repo-audit-plan-review.md`. Preflight via `model-review.py --preflight`. Critics: `--subscription` (Claude) + `-p codex-cli` (GPT), background, `-o`, no skill-prescribed `--timeout`.

## Footgun history (brief)

| # | Trap | Fix |
|---|------|-----|
| 1 | Gemini "free CLI" | Retired 2026-05-31; paid API + `--flex` |
| 2 | GPT xhigh timeout | `--timeout 1800–3600`; `--max-tokens` = visible-output budget (reasoning headroom added) |
| 3 | Shell `> file` / pipelines | `-o` + `set -o pipefail`; don't `2>/dev/null` diagnostics |
| 4 | `shell=True` + parens in prompt | List args + `input=` |
| 5 | Model name 404s | Hyphens not dots; see [models.md](references/models.md) |
| 6 | Fable over llmx | Downshifts / API billing; use Agent subagent or `--subscription` Opus — see `/model-guide` |
| 7 | Grok 4.20 `--reasoning-effort` | Errors on reasoning variant; >200K input = 20× price tier |
| 7b | Grok 4.5 retired Cursor aliases | Use exact `cursor-grok-4.5-{low,medium,high}` or matching `{effort}-fast` slugs from `cursor-agent models`. There is no xhigh slug. Bare `grok-4.5` is xAI API-only and subscription auth must fail before any xAI plan. |
| 7c | Grok 4.5 xAI API 403 | `API key is currently blocked` — **key status**, not EU geo (Chicago Mullvad egress still 403'd 2026-07-09). Rotate/unblock key in console; Cursor pool is the live path meanwhile. |
| 7d | Critique `grok` vs llmx cursor | `grok` axis uses `cursor-agent --workspace` (repo). `llmx -p cursor` uses neutral empty cwd (packet-only). Don't substitute. |
| 8 | Shelling llmx from Python: `subprocess.run(capture_output=True, timeout=)` hangs forever at 0% CPU | run()'s TimeoutExpired kills the child then blocks draining a pipe the llmx→claude-CLI grandchild holds. Use `Popen(start_new_session=True)` + `communicate(timeout)` + `os.killpg` on expiry (exemplar: arc-agi `agent/foundry_ewm.py llm()`; 27-min wedge 2026-07-04) |
| 9 | `--mode agent -e max` inherited the 300s chat default | Fixed in llmx `99de7a5`: agent floor 1800s, max floor 3600s; zero-byte `-o` after timeout is transport failure, never reviewer evidence |
| 9 | `--mode agent` launches in `~/.cache/llmx/lite/research` with no repo tools | Fixed 2026-07-10: mode and lite profile are separate. Workspace agent preserves caller cwd; `--lite research` stays isolated. Live-smoke with `pwd` + `git log` after changes. |
| 10 | Claude subscription call fails before dispatch when `--max-tokens` is set | Claude CLI does not expose that control. Omit `--max-tokens`; use explicit `--timeout` and let the model's native output ceiling apply. Subscription routes fail loud rather than silently billing API fallback. |

Legacy: `--lite bare` still works but `--subscription --mode chat` is canonical.
`--lite research` remains the isolated research-MCP profile for Claude/Codex.

$ARGUMENTS
