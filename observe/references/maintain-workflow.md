# Observe: maintain

This is the unattended conductor, not a new grant of authority. Follow existing user authorization and the [candidate lifecycle](candidate-lifecycle.md) before creating proposals/questions; the mode bounds self-directed ticks.

Apply the [maintain fleet scope](scope-and-arguments.md) before the tick: a repo argument narrows
rotation/fixes, while the SWEEP always covers all active repos.

Run as `/loop 30m /observe maintain` in one open window you watch. The **single RSI-loop conductor**
— it absorbed the standalone `orchestrator` skill and `research-ops cycle` (both retired 2026-06-12;
three conductors for one job was over-proliferation). It is a **thin conductor**: sweep for health,
pick ONE thing, dispatch existing workers. It does not reimplement them. **Never ask for input.**

Each tick, in order: **SWEEP** → **noop check** → **pick ONE and route** when work is needed →
**finish artifact updates and action logging** → **report** → **stop**. A red mechanical job takes
priority. An unchanged green tick skips the work step, records a noop, and reports one concise line.
The `/loop` interval drives the next tick; don't self-schedule. There is no earlier exit before the
required logging and artifact updates are complete.

**Route by verifier boundary.** For self-directed work, reversible changes confined to agent-infra
with one clear approach may proceed and be auto-committed. Other-repo changes, shared infrastructure,
structural changes or multiple viable approaches are propose-only. Continue broader work already
authorized by the user within that scope; an unattended tick grants no additional permission.
Work still requiring approval (taste / money / irreversible / shared deployment / discovery-tier)
becomes a sign-off-ready item in `agent-infra/decisions-pending/`; **never greenlight it yourself**.
The Generate lane produces reversible drafts for a yes/no.

**Before minting proposals/questions, enforce [queue backpressure](candidate-lifecycle.md#queue-backpressure).** Route a frozen queue into the drain.

**Priorities output.** An unchanged green noop does not regenerate or repeat the Top-N. Run
`uv run python3 ~/Projects/agent-infra/scripts/top_priorities.py --top 10` when priorities have
changed, a new actionable result should be surfaced, or the user explicitly requests them. It
prints the ranked digest and writes gitignored `PRIORITIES.md`; verify the artifact when updating
it. Report the meaningful change or actionable items, not an unchanged list. Route resulting work
through the same verifier and authorization boundary above.

**Live state.** After a green SWEEP, run
`bash ~/.claude/skills/observe/scripts/maintain_live_state.sh` from the tick's project cwd. It writes
`~/.claude/maintain-state-hash.txt` and, on unchanged state, appends the existing
`action:noop`, `target:state-unchanged`, `result:ok` row to cwd-relative `maintenance-actions.jsonl`.
Its exit 0 returns control to the tick; it is not proof that the SWEEP passed or that the tick is
finished. Reuse its noop row rather than append a duplicate, finish any other required logging,
then report. On a red SWEEP, skip this helper's success/noop branch and log the actual failure.

**The SWEEP.** The cheap health pass before the noop check. A silently-dead hook or stuck mechanical
job surfaces here on the first tick after it breaks — this is why the loop is watched, not headless.

Run each command as a **separate tool call**, retaining its return status and full stdout/stderr.
Do not pipe the producer through a display filter or replace its failure with `|| true`.

```bash
just -f ~/Projects/agent-infra/justfile hooks-smoke --timeout 8
```

```bash
uv run python3 ~/Projects/agent-infra/scripts/pulse.py canary
```

```bash
launchctl list
```

```bash
just -f ~/Projects/agent-infra/justfile freshness
```

Nonzero status from any command prevents a green/noop verdict. Also inspect the producer's findings:
hook failures/leaks, canary alarms, nonzero last-exit statuses for agent-infra jobs in the launchctl
table, and freshness `DUE` rows need triage even if the listing command itself succeeded. A successful
listing is not a health verdict. Treat a `DUE` row as an actionable pick before considering a noop.

Optionally add a parallel per-repo Composer drift screen (`git diff HEAD~1 --stat` →
`llm-dispatch.py --profile composer_screen` asking for `RISK high|medium` + one line + a suggested
check, else `OK`). Surface `RISK` lines — **triage only**; deterministic `doctor`/`drift-sentinel`
own ground truth. A **red sweep is the tick's priority**: if the fix is agent-infra-local and
obvious, do it this tick instead of the rotation. Full `doctor.py` stays in the daily rotation.

A **`just freshness` DUE row is a valid pick** — run the named worker: `trending-scout` →
`/trending-scout` (writes `research/trending-scout-YYYY-MM-DD.md`); `agent-infra-sweep` → a memo
named `research/*sweep*.md` with a `YYYY-MM-DD` stamp anywhere in the name, which is what
`freshness` reads to mark the source fresh. Any broad sweep memo counts; check the newest
`*sweep*.md` before starting a fresh deep sweep. The deterministic sources (vendor-docs,
binary-extract) are **not** the agent's job — launchd's `vendor-sweep` owns them; they appear in
`freshness` only so a red row exposes a dead job.

**Rate limit.** `CLAUDE_PROCS=$(pgrep -x claude | wc -l)`; ≥5 → skip the claude subagent lane. Use
`pgrep -x` (exact process name) — the old `-lf` substring-matched every `~/.claude/…` path (105 vs 5
true), so the gate was stuck closed and the loop never dispatched. **The cursor lane is NOT gated by
this count** (separate quota, separate process).

**The priority ladder.** (P0/P1 were the orchestrator queue — eradicated 2026-06-07, deleted here.)

- **P2 — implement promoted findings.** For `[ ]` items: read context, verify 2+ recurrence,
  classify autonomous vs propose, execute or write the proposal.
- **P2.5 — route design-review proposals** to `~/.claude/steward-proposals/`.
- **P3 — routine rotation.** Due-ness is **derived, not remembered**:
  `uv run python3 ~/.claude/skills/observe/scripts/rotation_due.py` reads
  `maintenance-actions.jsonl` and prints DUE/never per task. **Logging contract:** a tick that picks
  a rotation task appends `{"ts":…,"action":"rotation","target":"<task-key>","result":…}` — the
  script only sees what is logged with its keys, and an unlogged run stays "due" forever. Cadence
  values live in the SCRIPT (single source); the [rotation table](maintain-rotation.md) documents *how*.
- **P4 — implement proposals.** Read `~/.claude/steward-proposals/`. Autonomous → implement, verify,
  commit, append `**Status:** IMPLEMENTED`. Propose-only → skip.
- **P5 — triage + escalation.** >20 `[ ] proposed` → batch-triage. A hook at >100 warns/day for 3+
  days with <20% FP → write a promote proposal. Boundary-crossing → a sign-off-ready
  `decisions-pending/` item (run `/critique model` first if consequential).
- **P6 — all clear.** Nothing actionable? One line. **Don't invent work.**

**Rotation table** — the 24 rotation tasks, their cadence and how each is run, live in
[maintain-rotation.md](maintain-rotation.md). The session-learning rows (session anti-patterns, steer
mining, supervision, blindspot→detector, governance downstream-watch, the maintain motor, ACT
drain) come first — they are why this runs on a loop.

**Tier 2 dispatch — max 1 per tick.** Pick the lane by task shape:

- **Repo-coupled critique/analysis → the cursor lane (default).**
  `~/Projects/skills/scripts/cursor_dispatch.sh --prompt "<task>" --out <artifact> [--workspace <dir>]`
  uses **Composer** (a non-Composer `--model` is off-policy AND hook-blocked). Read-only, repo-aware
  (it flags "already handled at file:line" a cold API model cannot), not gated by `CLAUDE_PROCS`.
  **Mandatory fallback:** any non-zero exit (10 no-binary · 11 no-auth · 12 timeout · 13 error · 14
  empty) → re-dispatch the SAME task to the claude Agent lane. **Never skip a task because cursor failed.**
- **Code-mutating / multi-file fixes → claude Agent + worktree isolation** (the cursor lane is
  read-only by design). **Non-repo synthesis / search fan-out → claude `Explore`/`Agent` or `llmx`**
  (gated by `CLAUDE_PROCS`).

**Logging.** Append JSONL to `maintenance-actions.jsonl` for EVERY action:
`{"ts":"…","action":"freshness","target":"ClinVar","result":"ok","detail":"12d old"}`.
Keep the existing `rotation`/`target:<task-key>` contract above; log failures and noops as well as
completed work. Finish the required action rows and affected `MAINTAIN.md`/`PRIORITIES.md` updates
before the tick's single final report and stop. A noop does not need a priorities rewrite.

**MAINTAIN.md** — unified quality state; create from [MAINTAIN.md](MAINTAIN.md) if absent. Sections:
Findings, Queue, Fixed, Deferred, Strategic Notes, Drift Alerts. Monotonic IDs M001… WIP caps
enforce flow: max 5 findings (full → stop taking new), max 3 queued (full → halt discovery, focus
dispatch), items >90 days → move to end with `[STALE]`.

**Self-directed limits.** *Autonomous when reversible and one clear approach:* agent-infra-local
files, advisory hooks, measurement scripts, retrying transient failures, finding triage, rule
additions at 2+ recurrence. *Propose only:* changes to other repos, shared hooks/skills, new
pipelines, structural changes, multiple viable approaches. *Never self-authorize:* GOALS.md or
Constitution edits, capital, external contacts, or shared-infrastructure deployment. Existing user
authorization and the canonical Constitution/GOALS approval rule still apply; these limits do not
cancel approved broader work.

**Operating rules.** One task per tick, highest priority · log everything · report in 1-3 lines ·
auto-fix deterministic, dispatch the rest · respect revisit dates · idempotent (check the action log
and git log before acting) · classify before acting · a failed task is logged and skipped, never
retried consecutively.
