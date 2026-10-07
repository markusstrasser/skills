---
name: cursor-agent
description: "Use when: headless `cursor-agent` CLI from shell/CI/scripts, install/auth, or exact Cursor Grok 4.7 read-only repo review. Composer is retired (2026-10-07). NOT in-editor Cursor agent or llmx/claude-cli."
user-invocable: true
argument-hint: '[install|probe|dispatch|models] [prompt or model id]'
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: low
---

# Cursor Agent CLI — admitted Grok lane

Headless Cursor Agent from any terminal. Announced [2025-08-07](https://cursor.com/blog/cli); docs: [cursor.com/docs/cli](https://cursor.com/docs/cli).

**Composer 2.5 / 2.5-fast are retired (operator, 2026-10-07: "outdated").** Their jobs moved to GPT-6 Astra at `low` effort on the codex-cli subscription ($0): `codex exec -s read-only -C <repo> -m gpt-6-astra -c model_reasoning_effort=low -o <out> -`, with `gpt-6-sol` at `high` effort when Astra's plan limit binds. The `pretool-cursor-model-guard` hook blocks any `composer*` pin and any prompt run (`-p`) without `--model`, because the account default is Composer.

**The only admitted Cursor models are exact Grok 4.7 slugs**, an opt-in read-only review lane: `grok-4.7-{low,medium,high,xhigh}` (no `cursor-` prefix, verified live 2026-09-23) and matching trailing `-fast` variants. The `cursor-grok-4.6-*` slugs were retired 2026-09-25. Cursor subscription auth — not xAI API, llmx, or `claude -p`. **Never pass generic proxied models** (opus/gpt/claude/gemini/sonnet) or bare `grok-4.7`. For Opus/GPT use `claude -p` / `codex exec` / `llmx`. Re-list with `cursor-agent models` before a model-sensitive dispatch.

## Install & auth

```bash
curl https://cursor.com/install -fsSL | bash   # installs ~/.local/bin/agent
cursor-agent login                              # once; NO_OPEN_BROWSER=1 for headless
cursor-agent status                             # must show logged-in email
cursor-agent update                             # bump CLI (pin version in eval manifests)
cursor-agent models                             # list account models
```

Binary aliases: the installer's `agent` → `cursor-agent`, but on this machine `agent` resolves to the Grok Build binary — use `cursor-agent` for the Cursor registry.

## The three invocation shapes

| Shape | When | Command skeleton |
|---|---|---|
| **Interactive** | Human in the loop | `cursor-agent` or `cursor-agent "fix the auth bug"` |
| **Headless ask** | Read-only probes, reviews, Q&A | `cursor-agent -p --mode ask --trust --model grok-4.7-low "…"` |
| **Headless agent** | Writes + shell (trusted env only) | Not licensed for Grok; use `codex exec` or the Agent tool for writes |

### Flags that matter

- **`-p` / `--print`** — headless; stdout is the deliverable (scripts/CI). Always with `--model`.
- **`--trust`** — skip workspace-trust prompt (required with `-p`).
- **`--mode ask|plan`** — read-only; default agent mode edits + runs shell.
- **`--model MODEL`** — pin an exact live `grok-4.7-*` slug; omitting it runs the account default (Composer, retired) and is hook-blocked.
- **`--workspace PATH`** — isolate cwd (use a throwaway dir for evals/dispatch).
- **`--output-format text|json`** — `json` for usage/token forensics in evals.
- **`--force` / `--yolo`** — auto-approve shell unless explicitly denied.
- **`--sandbox enabled|disabled`** — override sandbox; eval probes use default sandbox + ask mode.
- **`--resume` / `--continue`** — session continuity across calls.

### Modes (same as editor)

| Mode | Edits | Shell | Use |
|---|---|---|---|
| agent (default) | yes | yes | Implementation dispatch |
| plan | no | no | Read-only planning |
| ask | no | no | Q&A, file read, screening probes |

## Dispatch patterns

### Grok 4.7 repo-read probe (opt-in, fail closed)

```bash
cursor-agent models | rg '^grok-4\.7-high - '
cursor-agent -p --mode ask --trust --model grok-4.7-high \
  --workspace "$PWD" --output-format text \
  "Read the current git HEAD with read-only tools and report its first 12 hex characters."
```

The critique harness enforces exact registry + an unrevealed repo-HEAD canary before every `grok` axis dispatch. Current evidence covers ask-mode repo review; it does not license Grok for autonomous writes.

### Uniform eval arm (evals repo)

```bash
~/Projects/evals/bin/dispatch-cursor-arm.sh \
  <workspace> grok-4.7-low ask "<prompt>" out.txt [manifest.json]
```

Reads `out.txt`; optional manifest records CLI version + prompt hash.

### Read-only repo scout (Composer's successor, not this CLI)

```bash
codex exec -s read-only -C "$REPO" -m gpt-6-astra -c model_reasoning_effort=low \
  --json -o out.md - < prompt.md     # --json events carry turn.completed usage
```

Cloud handoff (interactive only): prefix message with `&` → continues on cursor.com/agents.

## When to use vs other lanes

| Need | Route |
|---|---|
| Cursor-native Grok read-only repo review | **this skill** (`cursor-agent --model grok-4.7-*`) |
| Cheap read-only repo scout / screen | `codex exec -s read-only -m gpt-6-astra -c model_reasoning_effort=low` |
| Claude subscription, headless CC | `claude -p` (strip `ANTHROPIC_API_KEY`) or `llmx chat --subscription -m claude-opus-5-5` |
| GPT/Codex subscription | `codex exec` or `llmx chat --subscription` |
| API billing, batch, schema | `llmx chat` without `--subscription` (`/llmx-guide`; probe with `--dry-run`) |
| In-editor agent with hooks/skills | native Cursor / Claude Code Agent tool |

**Historical screening eval:** `~/Projects/evals/composer_cli_probe/` — ask-mode deterministic tasks, composer-2.5 vs composer-2.5-fast (record only; Composer retired).

## Footguns

1. **Forgot `--trust` with `-p`** — hangs on workspace prompt in scripts.
2. **Ask mode for writes** — agent can read/grep but won't edit; Grok is not licensed for write arms anyway.
3. **Default model drift** — always pass the exact model; the account default is the retired Composer. Grok slugs put effort before an optional trailing `-fast`. Bare `grok-4.7` is xAI / Grok Build, not the Cursor CLI slug. `agent` on this machine is the Grok Build binary; use `cursor-agent` for the Cursor registry.
4. **Empty stdout** — check exit code + stderr; wrap with timeout in orchestrators (`timeout 120 cursor-agent …`).
   Observed 2026-06-18: **`--mode plan` returned empty `-p` stdout 2/3 runs** (exit 0, no stderr) on
   open-ended critique prompts; **`--mode ask --trust` was 2/2 reliable**. For headless review/critique
   TEXT, prefer `--mode ask`; treat a 1-byte output as a silent failure and re-run (or use
   `--output-format json` and check `is_error`).
5. **Sandbox vs network** — ask-mode file reads are local; web fetch depends on sandbox config. Don't assume search works headlessly without probing.
6. **Beta security** — CLI can read/write/delete and run shell ([blog disclaimer](https://cursor.com/blog/cli)). Trusted environments only; isolate with `--workspace` throwaways.
7. **Don't confuse with Cursor IDE Tab** — this is the **Agent** product line.
8. **Cost is usage-METERED, not $0 — do NOT analogize from codex-cli/claude-cli.** Those subscription CLIs are genuinely $0-marginal within rate limits; Cursor is different: calls draw from the included-usage pool, then bill usage-based at each model's rate. Near-free *within* the monthly pool, then metered. (We shipped a "$0 marginal" claim across 5 docs by analogizing without checking — corrected 2026-06-14. Verify vendor pricing at cursor.com/pricing before asserting cost.) Full: `agent-infra research/2026-06-14-cursor-cli-composer-integration.md`.
9. **`--approve-mcps` auto-trusts ALL MCP servers; auto-update drift.** Never pass `--approve-mcps` in automation (a global MCP config could be auto-trusted). `cursor-agent` auto-updates itself + flags evolve (beta) — pin or smoke-test scripted transports on a schedule, and prefer `--output-format json` + check `is_error` over trusting non-empty text.

## Quick diagnose

```bash
cursor-agent status && cursor-agent about
cursor-agent -p --mode ask --trust --model grok-4.7-low "Reply with exactly: PING"
```

Exit non-zero → read stderr; re-run with `--output-format json` for structured error.

$ARGUMENTS
