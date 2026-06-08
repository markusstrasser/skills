---
name: orchestrator
description: "Use when: running the visible RSI loop in an open window ('/loop 30m /orchestrator'), or one manual tick. Each tick: a health SWEEP (see what's going on) + ONE rotating subagent — analyzer (observe), dream (leverage), implementor (improve). Replaces invisible launchd analysis jobs with a watched window."
user-invocable: true
argument-hint: "[once] (default: full tick)"
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write, Agent]
effort: medium
---

# Orchestrator

The RSI loop made **visible**. You run this as `/loop 30m /orchestrator` in a window you keep
open and watch — instead of headless launchd jobs you can't see. Each tick does two things:

1. **SWEEP** — a cheap health pass over the mechanical (launchd) jobs and repo state. This is the
   "I see what's going on." A silent failure (like the agentlogs indexer hanging for a month)
   surfaces here on the first tick after it happens.
2. **ONE rotating subagent** — analyzer → dream → implementor, one per tick. Each is an existing
   skill dispatched as a subagent; this skill is a *thin conductor*, it does not reimplement them.

> **Division of labor (deliberate).** launchd keeps the deterministic, zero-API, always-on jobs
> (session indexing, ledger commits, map refresh) — they must run even when no window is open, and
> burning tokens on `git commit` is wrong. The orchestrator does NOT replace them; it **watches**
> them (the sweep) and runs the **judgment** work they can't (analyze/dream/implement). The
> eradicated `orchestrator.py` was a headless queue daemon nobody invoked (0 calls/9mo) — this is
> the opposite: a watched window. Visibility is what keeps it used.

## Autonomy boundary (hard)

- **Auto-commit:** fixes that touch ONLY agent-infra's own files (meta-local) — implementor commits
  these directly (constitution: meta-local + reversible + one clear approach).
- **Propose only:** anything touching intel/phenome/genomics/skills, shared hooks/skills, or 3+
  projects → write a proposal to `~/.claude/steward-proposals/`, do NOT commit. Surface it in the tick report.
- **Never:** GOALS.md, constitution, capital, external contacts. (Invariants hold regardless of mode.)

---

## Each tick

### Phase 1 — SWEEP (always; this is the visibility)

Run the health pass and surface anything not green. Keep it to a tight block in the window.

```bash
# Mechanical-job health (the launchd jobs the orchestrator watches)
uv run python3 ~/Projects/agent-infra/scripts/doctor.py 2>&1 | tail -25
```

Read the output and call out, in 2-5 lines:
- **Any `fail`/`warn`** — especially `indexer:*` staleness or stuck-`running` (the silent-hang
  class), test-health, stale telemetry, memory overflow. A red indexer means the session substrate
  is going dark → flag it loud, it starves analyzer/dream measurement.
- **Recent activity** — `git -C ~/Projects/<repo> log --oneline --since='1 day ago'` across the
  active repos; `tail -5 ~/.claude/session-receipts.jsonl` for cost/commit anomalies.
- **Launchd liveness** (cheap): `launchctl list | grep agent-infra` — any job missing / last-exit non-zero.

If the sweep finds a **mechanical job is broken** (e.g. indexer stuck), that is the tick's priority:
report it and, if the fix is meta-local + obvious, hand it to the implementor this tick instead of
the normal rotation. Don't silently roll past a red sweep.

### Phase 2 — ONE rotating subagent

Pick the next subagent by rotation + readiness (track state in
`~/Projects/agent-infra/.claude/orchestrator-state.json`: `{last: "analyzer|dream|implementor", ts}`).
Rotation order: **analyzer → dream → implementor → analyzer …**. Skip a subagent whose precondition
isn't met (note the skip) and advance to the next.

| Subagent | Skill dispatched | Precondition | Does | Autonomy |
|----------|------------------|--------------|------|----------|
| **analyzer** | `/observe sessions` (or session-analyst) | new sessions since last analyzer run | reads recent transcripts → appends findings to improvement-log. **Capture, don't fix** — behavioral → `[obs]`, actionable → `[ ]` (see gov-id two-stream). | read-only + append-only log |
| **dream** | `/leverage` (or `/brainstorm`) | a target worth probing (high-friction project from the sweep, or a standing question) | hunts a 10-100x win on an unmeasured axis; measures friction from agentlogs first. | proposes only |
| **implementor** | `/improve harvest` | actionable `[ ]` items in the backlog | drains the OPEN actionable queue (not the `[obs]` ledger): picks highest leverage×staleness, fixes it. | **auto-commit meta-local, propose shared** |

Dispatch the chosen one as a subagent (the `Agent` tool), `isolation: "worktree"` if it touches code.
Give it the autonomy-boundary instruction explicitly. Let it run; read its result; relay the gist.

### Phase 3 — Tick report (to the window)

One concise block:
```
── orchestrator tick @ <time> ──
SWEEP: <green / N warns: …>  [loud if a mechanical job is red]
RAN: <subagent> → <one-line result>  (committed <sha> | proposed <file> | nothing actionable)
NEXT: <subagent> in <interval>
```
Then stop. The `/loop` interval drives the next tick; you don't self-schedule.

---

## Cadence & readiness notes

- **analyzer** needs new sessions to exist — skip if none since last run (don't re-analyze the same set; that was a logged waste).
- **dream** is the most expensive; once per few ticks is plenty. Don't force a 10x hunt every tick on a mature surface — one sharp survivor or skip.
- **implementor** can run whenever the actionable backlog is non-empty; it's the drain.
- If the sweep is green AND no subagent precondition is met → report "all green, nothing actionable" in one line and stop. Don't invent work (constitution: P6 all-clear).

## Anti-patterns

- **Doing all three subagents every tick** — that's the "full cycle" mode the user didn't pick; one per tick.
- **Reimplementing observe/leverage/improve** — dispatch them, don't rewrite them.
- **Auto-committing shared/cross-project changes** — propose only. The boundary is the whole point of an unattended-ish loop.
- **Rolling past a red sweep** — a silent mechanical failure is exactly what this loop exists to surface.
- **Fixing at analyzer time** — analyzer captures, implementor drains. Separating capture from consume is the gov-id two-stream discipline.

$ARGUMENTS
