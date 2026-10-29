---
name: llmx-guide
description: "Use when: /llmx-guide, writing llmx calls, debugging llmx failures, choosing model/provider, or reading/messaging a running Codex Desktop thread. Python/Bash gotchas — flags, transports, subscription vs API."
user-invocable: true
argument-hint: '[model name or issue description]'
effort: medium
---

# llmx Quick Reference

**Transport facts → mirror. Model judgment → `/model-guide`.** This skill is mechanics + footgun history only.

```bash
llmx info --write-mirror   # → ~/.claude/cache/llmx-routing.json — Read before dispatch
```

Profile-based dispatch with a context manifest: `~/Projects/skills/scripts/llm-dispatch.py` (the layer behind research-ops/observe/sweep; ad-hoc calls use the CLI). Library callers wanting structured status: `from llmx import dispatch, DispatchResult`.

> Detail files: [transport-routing.md](references/transport-routing.md) | [bare-lean-dispatch.md](references/bare-lean-dispatch.md) | [models.md](references/models.md) | [error-codes.md](references/error-codes.md) | [codex-dispatch.md](references/codex-dispatch.md) | [subcommands.md](references/subcommands.md) | [batch-apis.md](references/batch-apis.md)

**Cheap/lean one-off?** Read [bare-lean-dispatch.md](references/bare-lean-dispatch.md): reasoning tokens bill as output (`-e low` is cheaper AND better); one-offs want a RAW messages call not an agent harness; bare invocations to strip MCPs (codex `-c mcp_servers={}`, claude `--system-prompt --tools "" --strict-mcp-config` on the free sub, cursor `--mode ask`); subscription-routing footguns. Contract-tested: `tests/test_cli_contracts.py` (run `LIVE_CLI=1 pytest` after any codex/claude/cursor update).

**Messaging a Codex agent running in ChatGPT.app?** To deliver now, into the running turn, use `~/Projects/skills/bin/codex-thread steer <uuid> <file>`. To deliver at the end of the turn, use the app's bundled `codex queue --thread <uuid> --message <text>`. To find the thread and read its rollouts, see [codex-dispatch.md](references/codex-dispatch.md#live-codex-desktop-threads).

**Measuring spend / "cost per X"?** Don't build a usage dispatcher: llmx logs every call (claude-cli, grok-cli and codex-cli included) to `~/.claude/llmx-usage.jsonl`; roll up with `python ~/Projects/llmx/scripts/usage_summary.py --by caller` (reasoning counted as output). `prompt_tokens` is TOTAL input, partitioned by `cached_tokens`/`cache_write_tokens`. A stale PRICING table gets fixed in place, not forked. History: [footgun-history.md](references/footgun-history.md).

## Canonical patterns

**Newest picks (operator 2026-10-26):** `gpt-6.1-sol`, `gpt-6-astra`, `claude-opus-5-5`, `gemini-4-argon`. DeepSeek V4.1 Flash runs on LithosAI only (`-p lithosai`, tiers `deepseek-flash`/`-fast`/`-ultra`); DeepInfra is retired. Ids, prices, effort: [models.md](references/models.md).

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
llmx chat --subscription -m claude-opus-5-5 -f ctx.md -o out.md "query"
llmx chat --subscription -m claude-fable-5-1 -f ctx.md -o out.md "query"
llmx chat -p codex-cli --subscription -m gpt-6-astra -f ctx.md -o out.md "query"
llmx chat -p codex-cli --subscription -m gpt-6.1-sol -f ctx.md -o out.md "query"   # codex-cli >= 0.162
llmx chat --subscription -m grok-4.7-high -f ctx.md -o out.md "query"       # no cursor- prefix; re-list with cursor-agent models
llmx chat -p grok -m grok-4.7 -e high -f ctx.md -o out.md "query"           # Grok Build CLI lane (subscription-only; grok CLI 1.0.41 lists 4.7 as default)
```

Repository-coupled agent review (caller cwd, project rules, native CLI tools):

```bash
llmx chat --subscription --mode agent -m claude-opus-5-5 -e max \
  --timeout 3600 -o out.md "Inspect this repository read-only; cite file:line evidence."
```

`--mode agent` is a workspace agent. Legacy `--lite research` is an isolated
research-MCP-only profile; they are intentionally not aliases.

Metered lanes (no subscription CLI):

```bash
llmx chat -m gemini-4-argon -e high --flex -f ctx.md -o out.md "query"      # effort low|medium|high only
llmx chat -p lithosai -m deepseek-flash -e high -f ctx.md -o out.md "query"  # -e none turns thinking off
```

Strips API-key env on Claude/Codex subscription paths. If you see "Credit balance is too low", you hit API-key billing, not local subscription auth.

### Smoke (live, tiny)

```bash
llmx chat --subscription -m claude-opus-5-5 -e low \
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
7. **Gemini = paid API** since 2026-05-31; add `--flex` for 50% off non-interactive dispatch; name `-m gemini-4-argon` (the `-p google` default is the older 3.8 Flash)
8. **Exit 6 = billing or plan usage limit exhausted** (not retryable; a plan limit's message carries its reset time); exit 3 = rate limit (retry/backoff)

## When llmx Fails

Never swap to a weaker model as a fix. Check exit code → stderr JSON → `--debug` probe on a tiny prompt. See [error-codes.md](references/error-codes.md).

## Audit-plan critique (mechanics only)

Routing table: `critique/lenses/repo-audit-plan-review.md`. Preflight via `model-review.py --preflight`. Critics: `--subscription` (Claude) + `-p codex-cli` (GPT), background, `-o`, no skill-prescribed `--timeout`.

## Footgun rules (one line each; when a call misbehaves in a way listed here, read [footgun-history.md](references/footgun-history.md) for the incident and fix commit)

1. Gemini has no free CLI: paid API + `--flex`.
2. GPT xhigh: `--timeout 1800–3600`; `--max-tokens` is the visible-output budget (reasoning headroom added).
3. Never `> file` or a bare pipeline: `-o` + `set -o pipefail`; don't `2>/dev/null` diagnostics.
4. Python: list args + `input=`, never `shell=True` with a prompt (parens break it).
5. Model 404: hyphens not dots; check [models.md](references/models.md).
6. Fable: `--subscription -m claude-fable-5-1`; never fall back to paid API or usage credits without authorization; verify Agent-tool Fable pins via `/model-guide`.
7. Grok: rederive slugs from `cursor-agent models`, never memory. Current `grok-4.7-{low,medium,high,xhigh}[-fast]`, no `cursor-` prefix; `-e` is ignored on cursor-cli; bare `grok-4.7` is xAI / Grok Build (`llmx chat -p grok`). xAI API 403 `API key is currently blocked` = key status, not geo: rotate/unblock, use the Cursor pool meanwhile. Critique `grok` axis (repo workspace) and `llmx -p cursor` (empty cwd, packet-only) are not substitutes.
8. Shelling llmx from Python: `Popen(start_new_session=True)` + `communicate(timeout)` + `os.killpg` on expiry; `subprocess.run(capture_output=True, timeout=)` can hang forever at 0% CPU.
9. Zero-byte `-o` after a timeout is transport failure, never reviewer evidence. After changing `--mode agent`, live-smoke with `pwd` + `git log` (workspace agent keeps caller cwd; `--lite research` stays isolated).
10. Claude subscription: omit `--max-tokens` (the CLI rejects it); set an explicit `--timeout`.
11. Validate outputs by content, never by rc alone (a Stop-hook reply once came back as rc=0).
12. Usage rows before 2026-10-12 under-report claude-cli/grok-cli input; a `[DEGRADED]` usage note means unknown or missing token fields.
13. `--mode agent` implies `--auth subscription`; explicit api auth + agent, or a model with no subscription CLI (Gemini), exits 2.
14. DeepSeek: short tier aliases (`deepseek-flash-fast`) need `-p lithosai` (bare `deepseek-flash` goes to the DeepSeek platform); `-ultra` 429s "at capacity" under concurrent calls, so fan out on base or `-fast`; never send `promptCacheKey` (400). `-p deepinfra` and `deepinfra/…` ids exit 2 (retired 2026-10-26).

`--lite bare` still works; `--subscription --mode chat` is canonical.

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-07-16, historical: then-gpt-5.6, applies to the gpt-6 codex-cli lane] codex-cli --subscription lane runs with NO tools/web/file access (transport banner confirmed 2026-07-16) — "verify via search" instructions in dispatch prompts are silently no-ops on this lane; route search-dependent verification to researcher-type curators or claude lanes with MCP**
