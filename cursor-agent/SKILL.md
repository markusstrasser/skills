---
name: cursor-agent
description: "Use when: headless `agent` CLI from shell/CI/scripts, Composer install/auth/dispatch. NOT in-editor Cursor agent or llmx/claude-cli."
user-invocable: true
argument-hint: '[install|probe|dispatch|models] [prompt or model id]'
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: low
---

# Cursor Agent CLI — Composer 2.5 lane

Headless Cursor Agent from any terminal. Announced [2025-08-07](https://cursor.com/blog/cli); docs: [cursor.com/docs/cli](https://cursor.com/docs/cli).

**Default model here: `composer-2.5`** (also `composer-2.5-fast`). Cursor subscription auth — not llmx, not `claude -p`.

## Install & auth

```bash
curl https://cursor.com/install -fsSL | bash   # installs ~/.local/bin/agent
agent login                                     # once; NO_OPEN_BROWSER=1 for headless
agent status                                    # must show logged-in email
agent update                                    # bump CLI (pin version in eval manifests)
agent models                                    # list account models
```

Binary aliases: `agent` → `cursor-agent` (same binary).

## The three invocation shapes

| Shape | When | Command skeleton |
|---|---|---|
| **Interactive** | Human in the loop | `agent` or `agent "fix the auth bug"` |
| **Headless ask** | Read-only probes, reviews, Q&A | `agent -p --mode ask --trust --model composer-2.5 "…"` |
| **Headless agent** | Writes + shell (trusted env only) | `agent -p --trust --force --model composer-2.5 --workspace "$WT" "…"` |

### Flags that matter

- **`-p` / `--print`** — headless; stdout is the deliverable (scripts/CI).
- **`--trust`** — skip workspace-trust prompt (required with `-p`).
- **`--mode ask|plan`** — read-only; default agent mode edits + runs shell.
- **`--model composer-2.5`** — pin model; omit → account default (often `composer-2.5-fast`).
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

## Composer 2.5 dispatch patterns

### Screening probe (cheap, deterministic)

```bash
agent -p --mode ask --trust --model composer-2.5 \
  --workspace /tmp/cursor-probe-empty \
  --output-format text \
  "Reply with exactly: COMPOSER_OK"
```

### Uniform eval arm (evals repo)

```bash
~/Projects/evals/bin/dispatch-cursor-arm.sh \
  <workspace> composer-2.5 ask "<prompt>" out.txt [manifest.json]
```

Reads `out.txt`; optional manifest records CLI version + prompt hash.

### Parallel terminals

Each shell is an independent session — no shared context unless `--resume`:

```bash
agent -p --trust --model composer-2.5 --workspace ~/Projects/foo "task A" &
agent -p --trust --model composer-2.5-fast --workspace ~/Projects/bar "task B" &
wait
```

Cloud handoff (interactive only): prefix message with `&` → continues on cursor.com/agents.

## When to use vs other lanes

| Need | Route |
|---|---|
| Cursor subscription, terminal/Neovim/JetBrains | **this skill** (`agent`) |
| Claude subscription, headless CC | `claude -p` (strip `ANTHROPIC_API_KEY`) or `llmx chat --subscription -m claude-opus-4-8` |
| GPT/Codex subscription | `codex exec` or `llmx chat --subscription` |
| API billing, batch, schema | `llmx chat` without `--subscription` (`/llmx-guide`; probe with `--dry-run`) |
| In-editor agent with hooks/skills | native Cursor / Claude Code Agent tool |

**Measured screening eval:** `~/Projects/evals/composer_cli_probe/` — ask-mode deterministic tasks, composer-2.5 vs composer-2.5-fast.

## Footguns

1. **Forgot `--trust` with `-p`** — hangs on workspace prompt in scripts.
2. **Ask mode for writes** — agent can read/grep but won't edit; use default agent mode + `--force` for implementation arms.
3. **Default model drift** — always pass `--model composer-2.5` when comparing; `composer-2.5-fast` is the speed tier, not interchangeable in evals.
4. **Empty stdout** — check exit code + stderr; wrap with timeout in orchestrators (`timeout 120 agent …`).
5. **Sandbox vs network** — ask-mode file reads are local; web fetch depends on sandbox config. Don't assume search works headlessly without probing.
6. **Beta security** — CLI can read/write/delete and run shell ([blog disclaimer](https://cursor.com/blog/cli)). Trusted environments only; isolate with `--workspace` throwaways.
7. **Don't confuse with Cursor IDE Tab** — this is the **Agent** product line, model family Composer.
8. **Cost is usage-METERED, not $0 — do NOT analogize from codex-cli/claude-cli.** Those subscription CLIs are genuinely $0-marginal within rate limits; Cursor is different: calls draw from the "Auto + Composer" included-usage pool, then bill usage-based (Composer ~$0.50/M in, $2.50/M out; `-fast` $3/$15; proxied frontier models at their own rates). Near-free *within* the monthly pool, then metered. (We shipped a "$0 marginal" claim across 5 docs by analogizing without checking — corrected 2026-06-14. Verify vendor pricing at cursor.com/pricing before asserting cost.) Full: `agent-infra research/2026-06-14-cursor-cli-composer-integration.md`.
9. **`--approve-mcps` auto-trusts ALL MCP servers; auto-update drift.** Never pass `--approve-mcps` in automation (a global MCP config could be auto-trusted). `cursor-agent` auto-updates itself + flags evolve (beta) — pin or smoke-test scripted transports on a schedule, and prefer `--output-format json` + check `is_error` over trusting non-empty text.

## Quick diagnose

```bash
agent status && agent about
agent -p --mode ask --trust --model composer-2.5 "Reply with exactly: PING"
```

Exit non-zero → read stderr; re-run with `--output-format json` for structured error.

$ARGUMENTS
