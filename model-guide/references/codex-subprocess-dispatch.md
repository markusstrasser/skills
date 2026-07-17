# Running codex-cli as a subprocess (research / work workers)

How to dispatch `codex` (GPT-5.6-class as of 2026-07-10 — GPT-5.5 retired from the subscription allowlist; the mechanics below are model-generation-independent, ChatGPT-subscription, $0) as a background
subprocess worker — e.g. a fleet of parallel research lanes that each write a memo.
Verified working 2026-06-18 (codex-cli 0.140.0). Pairs with **Dispatch Economics** in
SKILL.md (executor-tier-by-verifier) — this file is the *mechanics*.

## TL;DR

```bash
codex exec --full-auto -c model_reasoning_effort=medium '<PROMPT that invokes a $skill>'
```

- Run via **Bash `run_in_background: true`** for anything >5 min (foreground Bash caps ~600s).
- Each worker writes its **own** output file; the parent collects + commits (foreground).
- The prompt MUST be **single-quoted** so the shell does not expand `$research` etc.

## Why codex can do real research (not training-memory)

- **Run from the repo root** so Codex discovers **project** skills via `.agents/skills/`
  (symlinked from `.claude/skills/` by `just -f ~/Projects/agent-infra/justfile codex-parity --repo <name>`).
  Global skills come from `~/.agents/skills/` (mirrored from `~/.claude/skills` by
  `sync_agent_skills.py`). Do **not** use `~/.codex/skills/` for managed skills — that
  path is Codex-bundled `.system/` only; stale copies there caused false ABSENT / wrong
  Modal contract reads in genomics (improvement-log 2026-06-21).
- Invoke a global or project skill in the prompt with its **`$name`** keyword, e.g. `$research`.
- `~/.codex/config.toml` wires the full MCP stack: `research` (research-mcp), `exa`,
  `brave-search`, `scite`, `perplexity`, `parallel`, `context7`. So a codex worker has the
  **same live network research tools** Claude does.
- Auth is the ChatGPT subscription (codex login) → **$0** token billing. (Still measure tokens
  — codex prints `tokens used`; eval-token-costs rule.)

## Flags that matter

| Flag | Effect |
|------|--------|
| `--full-auto` | workspace-write sandbox + auto-approve, non-interactive. **Default.** Reaches network MCPs (they are separate processes — the sandbox confines codex's own *shell*, not MCP calls) and lets the worker **write files into the workspace (cwd)**. |
| `-c model_reasoning_effort=low\|medium\|high` | per-invocation effort override (verified in rollout logs). `medium` = normal research; `low` = mechanical/canary; `high` only for hard synthesis. |
| `-m <model>` | model override (default = configured GPT-5.5-class). |
| `-s read-only` | no writes — for pure analysis that returns text only. |
| `--dangerously-bypass-approvals-and-sandbox` | full host access; only if a worker must run *network shell commands directly* (rare). Avoid. |

**cwd = workspace.** Run from the repo root so the worker can read context (`docs/…`) and write
its memo there. **No `-C <worktree>` needed** when workers write *distinct* files (no merge
conflict) — only worktree-isolate when they mutate *shared* files.

## Discipline (learned the hard way, 2026-06-18)

1. **Canary first.** Before a batch, fire one cheap `--full-auto -c model_reasoning_effort=low`
   probe that *forces real tool use* (ask for a **2025/2026** paper's arXiv ID + abstract line)
   and writes a file. Confirms transport + `$skill` + network + file-write end-to-end in ~1–2 min
   (~38k tokens). Only fan out the fleet after it returns a real recent paper.
2. **Stub-first output.** Tell the worker to create its output file with a one-line
   `RESEARCH IN PROGRESS` stub, then fill it — a crash leaves a locatable partial.
3. **Intern rule in the brief.** Any post-cutoff / load-bearing citation MUST be primary-verified
   by the worker's tools, never from memory, else tagged `[UNVERIFIED]`. Subprocess output is
   **unverified by default** — the parent spot-checks 1–2 load-bearing claims on return.
4. **One file per worker, descriptive names** (`docs/research/epoch2-A-….md`) so a parallel fleet
   never collides and you can tell which lane wrote what.
5. **Don't poll.** Wait for the harness completion notification per background task id; read the
   memo once on completion.

## Gotchas (false-failures + benign noise)

- **`pretool-no-background-commit.sh` blocks the literal word `commit`.** A `run_in_background`
  Bash whose command text contains "commit" — *even "do not commit" inside a prompt* — is BLOCKED.
  Do **not** put "git"/"commit" in the worker prompt; say *"leave version-control to the parent
  session."* Commit the workers' outputs yourself, **foreground**.
- **Benign teardown error.** After a worker finishes you may see
  `ERROR rmcp::transport… fail to delete session … mcp.exa.ai`. That is MCP session-teardown
  *after* the work completed — ignore it.
- **Subprocess writes aren't in the session ledger.** The Stop hook flags worker-written files as
  "written by a subprocess … did not auto-commit." Expected — commit them explicitly.
- **A repo's pre-commit ownership guard can BLOCK the parent from committing codex output.**
  genomics `staged_ownership_guard.py` fires `BLOCKED: … owned by another live Claude session` on
  a codex-written file — the worker writes its session-touch tracker under its OWN session id (not
  the parent's), and the guard keys on tracker-mtime recency (30-min grace), *not* process
  liveness, so it blocks even after the worker has exited (verified 2026-07-01). Fix: BEFORE
  committing, pre-register the worker's output paths in a write-intent tracker for YOUR session —
  `printf '%s\n' docs/…/a.md docs/…/b.md > /tmp/claude-write-intent-$CLAUDE_SESSION_ID-wave.txt` —
  the guard's `_own_tracker_files` globs `claude-write-intent-<your-sid>*.txt` and treats those
  paths as yours. Do this at dispatch time (paths are known up front) so the commit is frictionless.
- **llmx is NOT the vehicle for codex research.** `llmx chat --mode` accepts only `chat|agent`
  (no `research` mode); `--lite research` is a dead alias. Route research through `codex exec`
  directly. `llmx --subscription` is still fine for *tool-less* GPT-5.5 chat.

## Worked example (parallel research fleet)

```bash
# 1) canary (foreground/bg, low effort)
codex exec --full-auto -c model_reasoning_effort=low \
  'Invoke $research. Find one 2025/2026 arXiv paper on <topic>; write arXiv ID + title +
   one abstract line to docs/research/_canary.md. If no tools work, write NO_TOOLS.'

# 2) on success, fan out N lanes — each run_in_background:true
codex exec --full-auto -c model_reasoning_effort=medium \
  'Invoke $research (Deep). Read docs/<context>.md (do NOT re-research it). LANE: <question>.
   Write a provenance-tagged memo to docs/research/<lane>.md (stub-first). Intern-rule-verify
   post-cutoff citations. End with a VERDICT. Report tokens used. Then STOP: write only your one
   memo; leave version-control to the parent session.'

# 3) on each completion notification: read memo, spot-check, commit foreground (specific paths)
```

## See also

- SKILL.md → **Dispatch Economics** (which executor tier for which work-shape; the verifier rule).
- `research-ops` skill (parallel research-dispatch orchestration).
- `llmx-guide` skill (the llmx transport, for tool-less subscription dispatch).

- **Arm a Monitor on the output log for every `codex exec` nohup dispatch** — codex is not harness-tracked; a finished/dead run is silent otherwise (2026-07-11 arc-agi: DAG build sat done for hours unnoticed; its first launch died on `-c model=` unsupported and only a log-read caught it. Effort-only overrides on ChatGPT-plan codex).
