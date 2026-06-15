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

For profile-based dispatch with a context manifest, `~/Projects/skills/scripts/llm-dispatch.py` exists — the dispatch layer behind research-ops/observe/sweep cycles, not a general recommendation; direct CLI dominates ad-hoc usage.

> Detail files: [transport-routing.md](references/transport-routing.md) | [models.md](references/models.md) | [error-codes.md](references/error-codes.md) | [codex-dispatch.md](references/codex-dispatch.md) | [subcommands.md](references/subcommands.md) | [batch-apis.md](references/batch-apis.md)

## Canonical patterns

### Probe (before subscription dispatch or critique batches)

```bash
llmx chat --dry-run --subscription -m MODEL -e max
```

Critique harness (hard gate before parallel axes):

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py --preflight
# writes .model-review/preflight-latest.json; exit 6 = billing dead — abort
```

### Subscription dispatch (`--subscription` replaces `--lite bare`)

**Claude: NEVER `anthropic-direct`/API by default.** Subscription only unless the user explicitly requests metered API billing.

```bash
llmx chat --subscription -m claude-opus-4-8 -f ctx.md -o out.md "query"
llmx chat -p codex-cli --subscription -m gpt-5.5 -f ctx.md -o out.md "query"
```

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
5. **`--timeout` explicit** for high/xhigh (1800–3600); use `run_in_background` from agent context
6. **One combined context file** for critical reviews — multi-`-f` silently drops earlier files
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

Legacy: `--lite bare` still works but `--subscription` is canonical. `--lite research` for Codex research MCP profile only.

$ARGUMENTS
