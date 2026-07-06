---
name: improve
description: "Use when: /improve, 'what to fix next', maintenance loop, harvest findings, workflow→skill. Modes: maintain (/loop 30m), harvest, suggest. NOT one-shot research (/research)."
user-invocable: true
argument-hint: <mode> [options...]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: medium
---

# Improve

The action arm of the diagnostic loop. Three modes: harvest cross-artifact findings, suggest new skills from usage patterns, or maintain infrastructure quality.

## Modes

| Mode | Purpose | Loop | Default args |
|------|---------|------|-------------|
| `harvest` | Cross-artifact gathering, dedup, ranked output | no | `--days 3 --focus all` |
| `suggest` | Detect repeated workflows, propose skill/MCP candidates | no | `--sessions 10` |
| `maintain` | THE loop conductor — sweep + pick-one + route | `/loop 30m` | `[repo]` (default: all active) |

**Default (no mode):** Run harvest with defaults, show top 5, implement top confirmed finding.

> History: the `tick` mode and the headless orchestrator (`scripts/orchestrator.py` + launchd)
> were eradicated 2026-06-07/08; the standalone `orchestrator` skill and `research-ops cycle`
> were merged INTO `maintain` 2026-06-12 (it is now the single loop conductor — three
> conductors for one job was over-proliferation). The old orchestrator-queue P0/P1 steps are gone.

Parse mode from first positional argument in `$ARGUMENTS`. Remaining args pass through to the mode.

---

## Mode: harvest

Cross-artifact improvement harvester. Reads recent analysis artifacts, user feedback, and git corrections. Deduplicates against improvement-log and vetoed-decisions. Outputs a ranked list of infrastructure/tooling improvements.

**You consume artifacts. You don't produce analysis.** Session-analyst, design-review, retro, and suggest-skill produce the raw findings. You aggregate, deduplicate, rank, and surface what fell through the cracks.

**Harvest does two jobs: gather NEW, and drain the actionable OPEN queue.** A prior framing
("~140 open vs ~190 done, consumption is the bottleneck, drain harder") was built on a
**miscounted denominator** (F1, 2026-06-08): ~92 of the 131 "open" items were behavioral
calibration-ledger entries mistagged `[ ]` — they can never be `[x]` (their consumer is
recurrence→rule promotion, not a build), plus ~13 referenced eradicated infra. The real
actionable-open queue was ~23, not 140. **So the first move every run is to classify the
stream (below), THEN drain only the genuinely-actionable residue.** Draining is real but small;
the bigger lever is keeping the streams separate at entry (gov-id.md `[obs]` vs `[ ]`) so the
count stays honest. Rank the drain by leverage × staleness, not recurrence. Run on a cadence
(weekly). Two actionable classes to weight when they DO appear: **agent self-process
anti-patterns** (re-guessing before measuring, fix-spirals, `--no-verify` escape-hatching —
these recur silently because no error fires; log them `[obs]` unless there's a concrete guard to
build) and **dead-infra / generation-without-consumption** (a generator with no consumer —
genuinely `[ ]` actionable: delete it or wire it).

### Phase 0: Parse & Setup

Parse from `$ARGUMENTS`:
- `--days N` (default: 3)
- `--focus` filter: `hooks`, `skills`, `scripts`, `architecture`, `rules`, `all` (default: `all`)

```bash
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
ARTIFACT_DIR="$HOME/Projects/agent-infra/artifacts/harvest"
mkdir -p "$ARTIFACT_DIR"
DATE=$(date +%Y-%m-%d)
OUTFILE="${ARTIFACT_DIR}/${DATE}-${SID}-harvest.md"
CUTOFF=$(date -v-${DAYS}d +%Y-%m-%d)
```

### Phase 1: Load Dedup Baselines

Read in full -- they define what's already known:

1. **`improvement-log.md`** -- Extract all finding summaries and statuses (proposed/implemented/in-progress). Build `TRACKED` list.
2. **`.claude/rules/vetoed-decisions.md`** -- Extract all vetoed proposals. Build `VETOED` list. Do NOT re-propose anything on this list.

### Phase 2: Harvest Structured Artifacts

**Live streams first** (launchd-produced, refreshed daily — they carry the current signal),
then the legacy artifact dirs behind an mtime guard (read-path reordered 2026-07-05: the
original 2a-2d producers went quiet April-June 2026 and the signal plane moved to the
deterministic miners). One line per source below; the per-source protocol, history, and
judgment calls live in [references/harvest-sources.md](references/harvest-sources.md) —
read a source's entry (§2d-§2i) before working it.

- **2a. Blindspot misses** (`agent-infra/.claude/blindspot-digest.md`; detail §2i) — highest-signal
  live source: the loop misses the human had to catch. Top recurring cluster → a CANDIDATE DETECTOR
  (dedup vs existing hooks first); route local → `improvement-log` `[ ]`, shared → `decisions-pending/`.
- **2b. Reflect-loop quarantine** (`~/.claude/reflect-quarantine/*.jsonl`; detail §2e) — FM-routed
  enforcer/mint proposals, pre-deduped and pre-generalized; `just reflect-review` for the ranked
  view; promote for human disposition only, never auto-apply.
- **2c. Orphaned research findings** (`just orphan-findings`; detail §2f — the CANONICAL
  finding-routing protocol other generators cite, never restate) — finding-level ratchet; promote
  only genuinely-live, discrete, undone items with the finding title verbatim; one
  `RECONCILIATION:` entry clears a fully-dispositioned memo.
- **2d. Legacy artifact dirs** (session-retro / design-review / session-analyst / suggest-skill) —
  mtime guard FIRST: skip any dir with nothing in-window; parse normally if a producer wakes.
- **2g. Observe shell-env gate** (`artifacts/observe/*/failures/shell-env-candidate.jsonl`) —
  auto-staged; treat as high-priority infra, never `[obs]`.
- **2h. Cross-project memory generalization** (`just memory-harvest`) — dedup against the suggested
  target FIRST; promote only generalizable ≥2-project lessons; cross-skill factoring is propose-only.

**Denominator rule (all sources, this phase and Phase 3):** every extractor/miner invoked
must report its denominators — files scanned, messages/records parsed, items matched — and
the harvest output quotes them. A bare `0 found` is indistinguishable from a broken parser;
the #f extractor returned a silent false-zero for months because nothing forced
`matched 0 / parsed 0` into view (fixed skills@837f4d2). Treat `matched 0` with a healthy
denominator as signal, and `parsed 0` as a BROKEN SOURCE to fix before trusting the run.

### Phase 3: Harvest Unstructured Signals

**3a. User `#f` Feedback** -- highest signal, ground-truth corrections:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/extract_user_tags.py --days ${DAYS} --tag f
```

**3b. Git Corrections:**
```bash
git -C ~/Projects/agent-infra log --since="${CUTOFF}" --format='%h %s' --grep='Evidence:' --
git -C ~/Projects/agent-infra log --since="${CUTOFF}" --oneline -- .claude/rules/ improvement-log.md
git -C ~/Projects/skills log --since="${CUTOFF}" --oneline -- '*/SKILL.md' hooks/
```
Look for patterns -- if 3 commits fix hook edge cases, that signals weak hook testing.

**3c. Daily Memory Logs** (optional):
Check `~/.claude/projects/-Users-alien-Projects-meta/memory/` for `YYYY-MM-DD.md` files within window.

### Phase 4: Deduplicate & Classify

For each harvested item:

1. **Check TRACKED list.** Match against improvement-log: `implemented` -> skip, `proposed` -> mark "reinforced", `in-progress` -> skip.
2. **Check VETOED list.** Match against vetoed-decisions -> skip (unless concrete new evidence changes the calculus).
3. **Classify:** `hook`, `skill`, `script`, `architecture`, `rule`, `config`.
4. **Apply `--focus` filter** if specified.
5. **Count cross-source recurrence.** Two mentions in the same retro = 1 source, not 2. Count distinct source types.

### Phase 5: Rank

Two rankings, because harvest does two jobs (gather NEW + drain OLD):

**New items** — `priority = recurrence_count x severity_weight x novelty_bonus`
- `severity_weight`: high=3, medium=2, low=1
- `recurrence_count`: distinct sources mentioning this theme (1-6)
- `novelty_bonus`: 1.5 if completely new, 1.0 if reinforcing unimplemented, 0.5 if tangential

**Old open items (the drain)** — `priority = leverage x staleness`, where leverage is the
size of the win if fixed (10-100x friction removed, a whole failure class closed, dead-infra
eradicated) and staleness is age-of-open. This is NOT recurrence×severity — the highest-leverage
infra fixes are often single-source (one human finding at session end), so the new-item formula
buries them. Rank the drain by what's worth fixing × how long it's been rotting, not by how many
artifacts re-mentioned it.

**Before ranking the drain, classify the open backlog by stream (do this every run):**
- **Behavioral findings** (TOKEN WASTE, SYCOPHANCY, MISSING PUSHBACK, REASONING-ACTION MISMATCH,
  OVER-ENGINEERING, CAPABILITY ABANDONMENT…) are an append-only calibration ledger. Their consumer
  is recurrence→rule promotion, NOT per-item implementation. They can never be `[x]`. Do NOT count
  them as "open actionable work" — that inflates the backlog into a false panic number (measured
  2026-06-08: 92 of 129 "open" were behavioral; only ~8 were actionable-and-valid). When a rule has
  shipped covering a behavioral class, bulk-mark its contributors `[>]` superseded-by rule:X.
- **Moot items** — subject was deleted/eradicated (e.g. orchestrator items after 2026-06-07). Mark
  `[~] retired — subject no longer exists`. These are free drain.
- **Actionable infra/tooling/architecture** — the only stream that should carry `[ ]`/`[x]` and the
  only one "drain the backlog" applies to. Usually a small number once decluttered.

Sort each ranking descending.

### Phase 6: Output

Write to `$OUTFILE`:

```markdown
# Harvest -- {DATE}

**Window:** {CUTOFF} to {DATE} ({DAYS} days)
**Focus:** {FOCUS}
**Sources scanned:** N retros, N design-reviews, N session-analyst, N suggest-skill, N #f tags, N git corrections
**Items found:** N total -> N after dedup -> N after focus filter

## Summary

| # | Improvement | Type | Sources | Recurrence | Severity | Status |
|---|------------|------|---------|------------|----------|--------|
| 1 | ... | hook | retro, design-review | 3 | high | NEW |

## Details

### 1. [Improvement title]
**Type:** hook | skill | script | architecture | rule | config
**Priority:** {score} (recurrence={N} x severity={S} x novelty={B})
**Status:** NEW | REINFORCED | VETOED-BUT-REVISIT
**Sources:** (list with file paths and quoted findings)
**Proposed action:** {concrete next step}
**Dedup notes:** {what was checked}
```

### Anti-Patterns
- Don't re-analyze sessions -- read existing artifact output.
- Don't propose vetoed items without concrete new evidence.
- Don't inflate recurrence -- count distinct source types.
- Don't skip dedup. If everything is already tracked, say so.
- Don't propose maintenance as "improvement." This finds infrastructure/tooling/architecture changes.

---

## Mode: suggest

Detect repeated multi-tool workflows in recent sessions and propose skill or MCP tool candidates.

### What This Detects

1. **Repeated tool sequences** -- same 3+ step tool chain across 2+ sessions.
2. **Manual orchestration** -- user giving same multi-step instructions repeatedly.
3. **MCP tool gaps** -- agent shells out to bash for what a single MCP tool could do.
4. **Workflow templates** -- recurring session shapes that could be parameterized.

### Step 1: Extract Transcripts

Parse project from `$ARGUMENTS`. Default: current project, last 10 sessions.

```bash
ARTIFACT_DIR="$HOME/Projects/agent-infra/artifacts/suggest-skill"
mkdir -p "$ARTIFACT_DIR"
python3 ~/Projects/skills/observe/scripts/extract_transcript.py <project> --sessions 10 --output "$ARTIFACT_DIR/input.md"
```

Fall back to reading the 10 most recent JSONL files from `~/.claude/projects/-Users-alien-Projects-<project>/` if extractor unavailable.

### Step 2: Extract Tool Sequences

Local analysis to identify candidate patterns -- extract 3/4/5-grams of tool sequences, count frequencies, filter to those appearing 2+ times.

### Step 3: Dispatch to Gemini

Send transcripts + tool sequence analysis via the shared dispatch helper (`deep_review` profile, currently gemini-3.5-flash):

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path.home() / "Projects" / "skills"))
from shared.llm_dispatch import dispatch

transcripts = Path("$ARTIFACT_DIR/input.md").read_text()
response = dispatch(
    profile="deep_review",
    prompt=(
        "Analyze Claude Code session transcripts for repeated workflows. "
        "Classify as SKILL candidate (multi-step, judgment needed) or MCP TOOL candidate (deterministic, reusable). "
        "For each: pattern, frequency, current cost, trigger, parameters, skeleton. "
        "Only patterns appearing 2+ times across different sessions. Max 7 candidates. "
        "Rank by frequency x complexity saved."
    ),
    context_text=transcripts,
    output_path=Path("$ARTIFACT_DIR/candidates.md"),
)
```

### Step 4: Validate and Deduplicate

1. Check existing skills: `ls ~/Projects/skills/`
2. Check existing MCP tools: read `.mcp.json` files
3. Check ideas.md backlog: `grep -i "KEYWORD" ~/Projects/agent-infra/ideas.md`
4. Spot-check Gemini's frequency claims against transcripts

### Step 5: Output

Present candidates ranked by ROI. Save to `$ARTIFACT_DIR/YYYY-MM-DD-{SID}.md`.

### Step 6: Scaffold

If user approves a candidate:
- SKILL: create directory in `~/Projects/skills/` with SKILL.md
- MCP_TOOL: propose addition to the relevant MCP server

### Guardrails
- Don't suggest skills for coincidental one-offs that happened twice.
- Don't suggest MCP tools for things better as bash aliases.
- Frequency matters more than complexity.
- No strong candidates? Say so. Don't fabricate.
- Cross-check 10-use threshold from GOALS.md.

---

## Mode: maintain — THE loop conductor

Run as `/loop 30m /improve maintain` in one open window you watch. This is the **single
RSI-loop conductor** — it absorbed two earlier skills that did the same job (the standalone
`orchestrator` skill and `research-ops cycle`, both retired 2026-06-12, 0 invocations/90d
each; three conductors for one job was the over-proliferation). It is a **thin conductor**:
it sweeps for health, picks ONE thing per tick, and dispatches existing worker skills
(`observe`, `leverage`, `harvest`, `research`, `critique`) — it does not reimplement them.

Each tick, in order:
1. **SWEEP** (always — this is the visibility): `just hooks-smoke` + a cheap activity glance.
   A red mechanical job is the tick's priority. (from the old orchestrator's sweep)
2. **Noop check**: state-hash unchanged AND sweep green → one-line noop, stop. Idle ticks
   are ~free. (the engine below)
3. **Pick ONE** by readiness × priority (ladder P2–P6).
4. **Route by verifier boundary** (constitution: verifier-conditioned autonomy):
   - **reversible + single-project** → do it, auto-commit meta-local.
   - **boundary-crossing** (taste/money/irreversible/shared 3+ projects/discovery-tier) →
     write a sign-off-ready item to `agent-infra/decisions-pending/`, never greenlight.
     This is the **Generate lane** — unattended-safe because it only produces reversible
     drafts for a yes/no. (from `research-ops cycle`'s two-lane split)
5. **Visible tick-report** → stop. The `/loop` interval drives the next tick; don't self-schedule.
6. **Emit the Top-N priorities** (every run, the loop's headline output): `uv run python3 ~/Projects/agent-infra/scripts/top_priorities.py --top 10`. Writes `agent-infra/PRIORITIES.md` (gitignored) and prints the ranked cross-repo "what to plan next" digest — broken tools, pending decisions, open findings, real health fails, stale plans, with transient proxy-noise (stale-agent/uncommitted) suppressed. This is the answer to "the loop reported noop but what should I actually plan?" A green tick still has a priorities list; surface it. If an item is reversible+local+cheap, just do it; if it's a real piece of work, it's a plan candidate (offer/route to `decisions-pending/`).

The growth/research worker is `/research` (one-shot) and `/research-ops {compile,diff,dispatch}`
(non-loop tools); their old `cycle` loop is now this skill's Generate lane. **Never ask for input.**

**Scope (optional repo arg).** Default = **all active repos** (agent-infra intel genomics phenome
hutter substrate) — run it repo-agnostic and let it find the highest-leverage work anywhere. Pass a
single repo to scope a tick: `/improve maintain genomics` targets that repo's findings/rotation.
The SWEEP always covers all repos (it's cheap and a red job anywhere is the priority); the scope arg
only narrows which repo the tick's *rotation/fixes* act on. So:
- `/loop 30m /improve maintain` — let it rip across everything (the default you want for all-day looping)
- `/loop 30m /improve maintain intel` — same loop, work scoped to intel

### Live State

Snapshot + noop-hash logic lives in `scripts/maintain_live_state.sh` (Native-First extraction
2026-07-06; behavior-preserving — writes `~/.claude/maintain-state-hash.txt`, appends noop rows
to `$(pwd)/maintenance-actions.jsonl`, exits 0 early on unchanged state):

!`bash ~/.claude/skills/improve/scripts/maintain_live_state.sh 2>&1 | head -80`

### Phase 1: SWEEP (always — the visibility)

Before the noop check, run the cheap health pass. A silently-dead hook or a stuck mechanical
job surfaces here on the first tick after it breaks (this is why the loop is watched, not headless).

```bash
just -f ~/Projects/agent-infra/justfile hooks-smoke --timeout 8 2>&1 | tail -3   # ~15s; non-zero exit = a dead/broken hook
uv run python3 ~/Projects/agent-infra/scripts/pulse.py canary 2>&1 | grep -E "✗|ALARM" || true  # closure-instrument liveness (null/constant/stale) — a dead metric is the tick's priority
launchctl list 2>/dev/null | grep agent-infra | awk '$2 != 0 {print "  launchd non-zero exit:", $3}'  # red launchd jobs
just -f ~/Projects/agent-infra/justfile freshness 2>&1 | grep -E "DUE|source"  # surveillance sweeps past cadence
```

**Composer per-repo drift screen** (parallel, cheap — runs after deterministic checks pass):

```bash
REPOS="agent-infra intel genomics phenome skills hutter"
for repo in $REPOS; do
  (
    diff=$(cd ~/Projects/$repo 2>/dev/null && git diff HEAD~1 --stat 2>/dev/null | tail -5)
    [ -z "$diff" ] && exit 0
    printf '%s\n' "$diff" > /tmp/maintain-diff-$repo.txt
    uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
      --profile composer_screen \
      --context /tmp/maintain-diff-$repo.txt \
      --prompt "Review this diff stat summary for $repo. Output ONLY if actionable: RISK high|medium + one line why + suggested check. Else output: OK" \
      --output /tmp/maintain-composer-$repo.md 2>/dev/null
    grep -q '^RISK' /tmp/maintain-composer-$repo.md 2>/dev/null && \
      echo "  composer drift: $repo — $(head -1 /tmp/maintain-composer-$repo.md)"
  ) &
done
wait
```

Surface any `RISK` lines in the tick report. This is triage only — deterministic `doctor`/`drift-sentinel`
own ground truth; Composer flags diffs worth human glance.

A **red sweep is the tick's priority** — if the fix is meta-local + obvious, do it this tick
instead of the normal rotation; don't roll past it. Full `doctor.py` health stays in the P3
rotation (daily), so the per-tick sweep stays cheap. If state is unchanged AND the sweep is
green → report "noop" in one line and stop.

A **`just freshness` DUE row is a valid pick** for this tick's rotation (it competes by
leverage like any other) — run the named worker for the due source: `trending-scout` →
`/trending-scout` (writes `research/trending-scout-YYYY-MM-DD.md`), `agent-infra-sweep` →
a frontier sweep memo named `research/*sweep*.md` with a `YYYY-MM-DD` stamp anywhere in the name
(e.g. `2026-06-12-agents-rsi-gap-sweep.md`) — that is what `freshness` reads to mark the source
fresh again. Any broad sweep memo counts; don't start a fresh deep sweep if a recent one already
covers the frontier (check the newest `*sweep*.md` first).
The deterministic sources
(vendor-docs, binary-extract) are NOT the agent's job — launchd's daily `vendor-sweep` owns
them; they appear in `freshness` only so a red (DUE+stale) row exposes a dead launchd job.

### Rate Limit Check

```bash
CLAUDE_PROCS=$(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ')
```
If >= 5: skip the **claude** subagent lane (Tier 2 claude dispatch). `pgrep -x` matches the
exact `claude` process name — the old `-lf` substring-matched every `~/.claude/...` path (105 vs
5 true on the dev box), so the gate was permanently stuck closed and the loop never dispatched.
The **cursor lane (Tier 2, below) runs on Cursor's quota and is NOT gated by this count.**
Route LLM-heavy analysis through `uv run python3 ~/Projects/skills/scripts/llm-dispatch.py --profile cheap_tick ...`.

### Each Tick: Pick ONE Task by Priority

> The orchestrator was eradicated 2026-06-07. The former P0 (Orchestrator
> Failures) and P1 (Queue Dispatch) are **deleted** — there is no queue and no
> orchestrator DB. Priority now starts at P2.

**P2: Implement Promoted Findings.**
For unimplemented findings with `[ ]`: read context, verify 2+ recurrence, classify autonomous vs propose, execute or write proposal.

**P2.5: Route Design-Review Proposals.**
New design-review artifacts -> extract proposal -> write to `~/.claude/steward-proposals/`.

**P3: Routine Rotation.**
Due-ness is DERIVED, not remembered (state-externalization, 2026-07-05):

```bash
uv run python3 /Users/alien/.claude/skills/improve/scripts/rotation_due.py   # cadence table of record
```

The script reads `maintenance-actions.jsonl` and prints DUE/never per task — pick the
top one. **Logging contract:** when a tick picks a rotation task, append
`{"ts": ..., "action": "rotation", "target": "<task-key>", "result": ...}` — the script
only sees what's logged with its task keys; an unlogged run stays "due" forever.
Cadence values live in the SCRIPT (single source); the table below documents HOW per
task and the judgment calls. The **session-learning loop rows come first** — they are
the reason this skill runs on a `/loop`: mine what happened, drain what's actionable,
scan the frontier. Cadence follows the signal rate (don't re-run a daily-grain miner
every tick):

| Task | Cadence | How |
|------|---------|-----|
| Hook health | Every tick (~15s) | `just hooks-smoke` in agent-infra — catches silently-dead hooks at the cheapest possible point. Non-zero exit → fix or escalate before other work. |
| Session anti-patterns | Daily (or per ~5 new sessions) | `/observe sessions` — behavioral findings → improvement-log `[obs]` |
| **Steering vectors (full corpus)** | Weekly (incremental) | `just steer-mine` in agent-infra — mines steers/confirmations/agent_miss from unscanned sessions (`mine_steers.py`; ledger at `~/.claude/steer-mining/`). Cluster recurring `vector` fields → GOALS tension or steward-proposal; do NOT auto-promote to hooks without observe promotion gates (2+ sessions, checkable). |
| Supervision waste | Daily | `/observe supervision` — corrections/boilerplate/rubber-stamps → automatable fixes. A reiteration of something already decided elsewhere = highest-signal defect → `decisions-pending/`. |
| Governance-change downstream watch | After constitution/GOALS/invariants edits (`git log` the governance files) | review sessions since the edit for new friction / reverts / anomalies attributable to it → flag to `decisions-pending/` or revert. The compensating control for inferred-approval governance autonomy (invariants #1): autonomy on reversible governance text is only sound if a loop actually catches a bad edit downstream. |
| Governance health read | Daily (consumes the `com.agent-infra.gov-report` launchd job's output) | read `artifacts/gov/gov-report.md`; act on the 3 REAL `gov_invariants` assertions (rule-hook balance, recurrence-architecture, verifier-coverage). Graders live in **`~/Projects/evals/graders/governance/`** (sibling repo — gov.py resolves from projects root). Shrink-eligible scaffolds with missing grader files show `⚠ grader not found`; with graders present, read the ✓/✗ verdict. Escalate failed invariants to `decisions-pending/`. SENSE half is launchd; this row is ACT. |
| **Maintain motor (build + shrink drafts)** | Daily — the symmetric ACT motor | Run the agent-infra motor (SAFE/dry-run — it NEVER edits/commits/deploys): `uv run python3 ~/Projects/agent-infra/scripts/maintain_tick.py` drafts a tier-0 BUILD proposal; add `--subtract --ablate` to draft a governance RETIREMENT (gov-shrink + advisory-noise, ablation-gated). Both land in `artifacts/maintain/`. Surface the drafts in the tick report and route by KIND: a **BUILD** draft follows P2 (reversible+agent-infra-local → implement+commit). A **RETIRE** draft is governance DELETION → route to `decisions-pending/` for human sign-off **even when local + ablation-PASS** (removing a scaffold is higher-stakes than adding one; gov-id.md earned-autonomy auto-retirement needs a track record + `AUTO_APPLY_ENABLED`, both OFF by default). **Never auto-remove governance in an unattended tick.** This closes the shrink loop: gov SENSE (row above) → motor drafts → human applies. |
| **ACT drain (disposition queue)** | Daily (consumes `com.agent-infra.act-drain` digest) | read `~/.claude/act-drain-digest.md` OR run `just act-drain`. Surfaces at SessionStart. Runs `reflect classify` + ranks quarantine / steward / RSI-close pending. **Do NOT add duplicate maintain rows for classify** — this job IS the scheduled classify drain. Human dispositions: `/rsi close`, `just reflect-review`, steward-proposals triage. |
| Finding drain | Weekly | `/improve harvest` — gather NEW + drain actionable `[ ]` queue |
| Tool failures | Weekly | `/observe failures` — mine agentlogs for tools/CLIs actually broken in real use (the proxy health-checks can't see this; a dead `corpus` CLI hid for days). Tier-1 deterministic ($0); escalate big clusters. **`zsh-env:*` clusters** → `shell_env_loop_gate.py` auto-stages when volume + doctor fail. |
| **Cross-harness shell env** | Weekly (with failures) | `doctor.py` → `global:shell-env-*` checks (agent-zsh-safe, Cursor hooks, Claude uv guard). Failures here mean home-dir shell config drift — not repo hooks. |
| **Blindspot → detector (RSI convert step)** | Daily (consumes `com.agent-infra.blindspot-miner`'s digest) | read `agent-infra/.claude/blindspot-digest.md` (loop misses the human caught). Cluster (`emb pairs`); for the top recurring cluster, **propose the DETECTOR that would have caught the class** (dedup vs existing hooks first) → `improvement-log` `[ ]` / `decisions-pending/`. This is the loop-closure: a flag becomes coverage. The blindspot-flag rate is the declining-supervision objective — it should fall as detectors land. |
| Architecture patterns | Weekly (alt. with frontier) | `/observe architecture` — cross-project abstractions |
| Leverage scan | Weekly | `/leverage` — prospective 10-100x wins observe is structurally blind to |
| Frontier sweeps | Freshness-driven (`just freshness`) | `/trending-scout` when DUE (2d) + agent-infra-sweep when DUE (3d). Ecosystem/vendor deltas. Deterministic vendor-docs+binary fetch is launchd's `vendor-sweep` (daily), not a rotation pick. |
| Database freshness | Daily | Check timestamps. Flag >30d stale. |
| Bio-verify audit | Rotate: 1/tick | `just bio-verify-queue` -> top item |
| Deferred probe | After revisit date | HTTP-probe URLs, check release pages |
| Cross-check outputs | Daily | Pick T1/T2 variant, query biomedical MCP, compare |
| Research memo staleness | Weekly | Check ACTIVE memos vs recent file changes |
| Code quality scan | Weekly | `/project-upgrade --quick` |
| Calibration canary | Weekly | `calibration-canary.py --mode sampling --difficulty hard --runs 10 --backend llmx` |
| Genomics canary | After classification changes | `just canary` in genomics |
| Doctor.py health | Daily | `uv run python3 scripts/doctor.py` |
| Session cost tracking | Daily | Flag sessions >$5 or no-commit anomalies |
| Infra coverage | Monthly | git log -> categorize fixes by detection source |
| Doc currency | Fallback | `just check-codebase-map && just check-claude-md` |

**P4: Implement Proposals.**
Read `~/.claude/steward-proposals/`. Autonomous -> implement, verify, commit. Append `**Status:** IMPLEMENTED`. Propose-only -> skip.

**P5: Triage & Escalation.**
Finding triage (>20 `[ ] proposed` -> batch-triage). Hook escalation (>100 warns/day for 3+ days with <20% FP -> write promote proposal). **Boundary-crossing items** (taste, money, irreversible, shared 3+ project blast radius, discovery-tier direction) -> write a sign-off-ready proposal to `agent-infra/decisions-pending/` (format in its README; run `/critique model` cross-lab first if consequential). Never greenlight these yourself — the loop decides everything reversible and single-project, and escalates only what genuinely needs the human.

**P6: All Clear.** Nothing actionable? Say so in one line. Don't invent work.

### Tier 2: Dispatched Work

Max 1 per tick. Rate-limit gate.

| Task | Cadence | Skill/Tool |
|------|---------|-----------|
| Audit sweep | Biweekly | `/dispatch-research quick sweep` |
| Benchmark drift | After pipeline changes | `noncoding_benchmark.py benchmark` |

**Dispatch lanes (pick by task shape):**
- **Repo-coupled critique / analysis → cursor lane (default, encouraged).** Run via the hardened
  wrapper `~/Projects/skills/scripts/cursor_dispatch.sh --prompt "<task>" --out <artifact> [--workspace <dir>]`.
  Uses **Composer** (Cursor's native lane — best price/perf; a non-Composer `--model` is
  off-policy AND hook-blocked by `pretool-cursor-model-guard.py`). Read-only
  (`--mode ask`), repo-aware (flags "already-handled at file:line" a cold API model can't), and
  **NOT gated by `CLAUDE_PROCS`** (Cursor quota, separate process). **MANDATORY fallback:** any
  non-zero exit (10 no-binary · 11 no-auth · 12 timeout · 13 error · 14 empty) means cursor is
  unavailable → re-dispatch the SAME task to the claude Agent lane. Never skip the task on a
  cursor failure (the wrapper guarantees the loop never silently dies on cursor outage).
- **Code-mutating / multi-file fixes → claude Agent + worktree isolation** (proven path; the
  cursor lane is read-only by design, so it does not handle mutations).
- **Non-repo synthesis / search fan-out → claude `Explore`/`Agent` or `llmx`** (gated by `CLAUDE_PROCS`).

### Execution Model

Auto-fix deterministic (unused imports, stale versions) inline. Dispatch multi-file fixes via Opus subagent.

### Logging

Append JSONL to `maintenance-actions.jsonl` for EVERY action:
```json
{"ts":"2026-04-06T12:00","action":"freshness","target":"ClinVar","result":"ok","detail":"12d old"}
```

### MAINTAIN.md

Unified quality state. If it doesn't exist, create from `${CLAUDE_SKILL_DIR}/references/MAINTAIN.md`.

Sections: Findings, Queue, Fixed, Deferred, Strategic Notes, Drift Alerts.
Item IDs: monotonic M001, M002... WIP caps enforce flow:
- Max 5 findings — when full, skip new findings until dispositioned
- Max 3 queued — when full, halt discovery, focus dispatch
- Items >90 days stale — auto-move to end with `[STALE]` note

### Autonomy Rules

**Autonomous:** meta-only files, advisory hooks, measurement scripts, retry transient failures, finding triage, rule additions (2+ recurrence).
**Propose only:** changes to intel/selve/genomics/skills, shared hooks/skills, new pipelines, structural changes, multiple viable approaches.
**Never:** GOALS.md, capital deployment, external contacts, shared infra deployment.

### Error Recovery

Task fails: log error, skip this tick, don't retry same task consecutively. Subagent fails: log, keep in queue, retry next tick if rate-limit allows.

### Operating Rules

1. One task per tick. Highest priority.
2. Log everything. JSONL is the audit trail.
3. Report in 1-3 lines.
4. Auto-fix deterministic, dispatch the rest.
5. Respect revisit dates.
6. Don't touch CYCLE.md.
7. Idempotent -- check action log and git log before acting.
8. Ultrathink for implementation.
9. Classify before acting.

---

## Relationship to Other Skills

```
session-analyst ---> artifacts/session-analyst/*.json --+
design-review ----> artifacts/design-review/*.md ------+
retro ------------> artifacts/session-retro/*.json ----+---> improve harvest ---> artifacts/harvest/*.md
suggest-skill ----> artifacts/suggest-skill/*.md ------+
user #f feedback -> session transcripts ---------------+
git corrections --> git log ----------------------------+
```

$ARGUMENTS
