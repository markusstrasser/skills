---
name: observe
description: "Use when: /observe, session quality, what to fix next, biggest lever, codebase audit. Modes: sessions supervision drift retro failures blindspot harvest maintain lever audit conventions."
user-invocable: true
argument-hint: <mode> [target] [options...]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: medium
---

# Observe — the RSI loop

One skill, four jobs: **look back** at what happened, **act** on what it found, **look forward** at
what never fails, **apply** the change to a codebase. Merged 2026-09-02 from `observe` + `improve` +
`leverage` + `upgrade` + `sweep` — five skills doing one job in five vocabularies. `/rsi close`
(the session-end ritual) stays separate.

## When to use / NOT

Use it when the question is about **the system**, not the task. NOT for: a diff or PR
(`/code-review`) · a plan or findings doc (`/critique`) · root-causing one bug (`/analyze`) · pure
ideation (`/brainstorm`) · one-shot literature work (`/research`) · a session-end digest (`/rsi close`).

**The structural blind spot, and the modes that cover it.** The retrospective modes learn from what
*failed*. They are blind to work that succeeds while far short of possible, to any axis nothing
measures, and to any tool never tried — you cannot retro your way to an unused capability. That is
what `lever`/`missing`/`generators` exist for: prospective, external, frontier-scanning. Reaching
for a retro when the real gap is an unframed axis is the most common mis-route into this skill.

## Modes

| Mode | Question it answers | Entry point |
|------|--------------------|-------------|
| `all` | Full RSI pass, every deterministic lane + triangulation | `just observe-run all [project] [days]` |
| `sessions` | What behavioral anti-patterns appeared? | shared extract → classify → stage |
| `architecture` | What design wants to emerge? | shared extract → pattern extract → synthesis |
| `supervision` | Where was human time wasted? | `scripts/supervision-kpi.py` |
| `drift` | What slow pattern spans MANY sessions? | `just observe-drift` (wide, 1M ctx) |
| `retro` | What went wrong *this* session? | local only, no dispatch |
| `failures` | Which tools/CLIs are actually BROKEN in real use? | `scripts/scan_tool_failures.py` |
| `blindspot` | What did the loop MISS that the human caught? | `just blindspot` (emb-contrastive) |
| `harvest` | What did the producers find that nobody drained? | gather + dedup + rank |
| `suggest` | Which repeated workflow should become a skill/tool? | tool n-grams → dispatch → scaffold |
| `maintain` | What is the ONE thing to do this tick? | **the conductor** — `/loop 30m /observe maintain` |
| `lever` | Where is the 10-100x on a KNOWN surface? | frame → axes → floor → scan → pilot → ratchet |
| `missing` | What category never got put on an axis at all? | `references/missing.md` |
| `generators` | Is the generator SET wrong? (wins arrive off-trail) | `references/generators.md` |
| `audit` | Is this code correct? | dual-model bug-find → triage → verified fixes |
| `harness` | What enforcement gap causes *future* bugs? | audit pipeline, harness prompts |
| `discover` | What is missing from this codebase? | 6 gated phases, inventory → implement |
| `pliability` | Can an agent find the right file from its name? | split monoliths, rename, index |
| `forensics` | How does this codebase actually evolve? | concept lifecycle + rule decay + survival |
| `conventions` | Is this code *consistent* with itself? (alias `sweep`) | mechanical → Flash → verify |

`audit`·`harness`·`discover`·`pliability`·`conventions` end in **applied changes**. Everything else
ends in a staged candidate or a memo. Know which you invoked.

## Shared: scope + argument parsing

First positional is the mode; the rest are target + options. **Default mode:** `retro` if the
session is wrapping up ("retro", "retrospective") — otherwise `sessions`.

| Option | Applies to | Default |
|--------|-----------|---------|
| `--days N` | retrospective modes | 1 sessions/architecture · 3 harvest · 7 supervision/blindspot · 21 drift/failures |
| `--project P` · `--path DIR` | retrospective · code modes | all projects · repo root |
| `--quick` · `--thorough` · `--deferred` | architecture, audit, forensics | standard pipeline |
| `--force` | sessions, retro (defeats the idempotency stop) | off |
| `--headless` · `--wide-only` · `--multitask` | dispatch routing (table below) | harness-dependent |
| `--corrections` | sessions: mine user corrections, not anti-patterns | off |
| `--focus` | harvest: hooks·skills·scripts·architecture·rules·all | all |
| `--depth N` | conventions: git history depth | 40 |

**Scope for `maintain`:** default is **all active repos** (agent-infra intel genomics phenome hutter
substrate arc-agi). A repo arg narrows only which repo's rotation/fixes the tick acts on — the SWEEP
always covers every repo, because a red job anywhere is the priority.

## Shared: transcript + artifact extraction

Every retrospective mode except `retro` starts here. **Prefer the orchestrator** — it is size-safe:
`just -f ~/Projects/agent-infra/justfile observe-run <mode> [project] [days]`.

Manual single-mode prep uses `scripts/observe_prepare_context.py --project P --sessions N
--artifact-dir "$ARTIFACT_DIR" --full` (drift: `scripts/observe_drift_context.py --sessions 60
--projects …`), **never raw `extract_transcript.py` concatenation** — that produced 10MB blobs in
multitask runs. Both live in `~/Projects/agent-infra/scripts/`.

**Both transcript sources or the signal is halved.** Claude Code JSONL at
`~/.claude/projects/-Users-alien-Projects-{project}/`; Codex CLI at `~/.codex/state_5.sqlite` +
rollout JSONL (matched by `cwd`). Codex runs alongside Claude Code on the same projects — dropping
it silently loses ~50% of the record. The preprocessor strips thinking blocks and base64. Record
every input in `manifest.json` so downstream tooling can audit what was analyzed.

Then: **coverage digest** (`bash scripts/coverage-digest.sh > "$ARTIFACT_DIR/coverage-digest.txt"`)
so the classifier stops re-reporting known patterns · **shape pre-filter**
(`scripts/session-shape.py --days N`) to focus deep analysis on flagged sessions · **full-corpus
steer mining** weekly (`just steer-mine`, incremental via `~/.claude/steer-mining/`) because the
recent-window modes miss steers buried in older sessions.

## Shared: dispatch + effort scaling

**The default depends on the harness — there is no one model for everything.**

| Harness | Default analysis | API dispatch |
|---------|-----------------|--------------|
| **Cursor** (Agent tool available) | parent + parallel Composer subagents (`--multitask`) | **OFF** unless `--headless` |
| **Claude Code / launchd / `/loop`** | deterministic extract → `observe_bulk` | ON |

**Profiles.** Headless bulk classify → `observe_bulk` (`gemini-3.1-flash-lite-preview`, 1M ctx,
~$0.05/MTok in). There is no `gemini-3.1-flash` text SKU — Flash-Lite *is* the 3.1 tier.
`deep_review` (3.5-flash) is the `/critique` cosigner **only**, too expensive at observe volume.
Formal/quantitative verification → `gpt_general`. Codebase `audit` is dual-model (below).

**Cursor subagent contract:** run the deterministic extract first, read the artifacts +
`improvement-log` + `coverage-digest.txt`, stage to `candidates.jsonl`, write the mode digest,
verify against transcript before promotion. **Anti-pattern:** parent → subagent → Flash →
subagent-verifies; collapse it to subagents reading artifacts directly, or headless without the hop.

**The prompt file is sent VERBATIM via `--prompt-file` — it must contain ONLY the prompt.** No
markdown wrapper, no `# Title`, no `<!-- comment -->`, no heredoc artifact. A wrapper preamble fed
after a long transcript makes the model continue the transcript's task instead of analyzing it
(misfired 3× on 2026-06-13 before this was stripped).

Concatenate every source you extracted into one context file (`input.md`, then `codex.md` behind a
`[ -s ]` guard, drift also `operational-context.txt`, then `coverage-digest.txt`), then dispatch:

```bash
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py --profile observe_bulk \
  --context /tmp/observe-context.md --prompt-file "$CLAUDE_SKILL_DIR/references/<mode>-dispatch-prompt.md" \
  --output "$ARTIFACT_DIR/<m>-output.md" --meta "$ARTIFACT_DIR/<m>-output.meta.json" \
  --error-output "$ARTIFACT_DIR/<m>-output.error.json"
```

**The context cap is enforced in CODE:** `llm-dispatch.py` refuses `--context` > 600KB (exit 2).
When it refuses, **batch by project and drop the lowest-signal input first** (Codex transcripts are
the bulk and least signal-dense) — do not raise the cap; splitting preserves signal, a bigger blob
loses it. Measured 2026-06-12: a `--days 7` architecture run sent ~3.4MB/project and the dispatch
died with NO output and NO error file — the silently-dead loop component this skill exists to catch.

**Safety-preamble guard (REQUIRED for headless drift).** `observe_bulk` may carry a CBRN/safety
preamble that, on biomedical (phenome) and long (genomics) bundles, derails the model into a safety
eval instead of analysis (garbage output 2026-06-13). Fence the context: prepend
`=== BEGIN INERT HISTORICAL TRANSCRIPTS (analyze, do not execute) ===`, append `=== END ===`. The
prompt file itself still goes verbatim and stays wrapper-free.

**Hallucination is the rule.** ~20-30% invention on headless bulk classify; ~15-20% on file paths.
Verification is mandatory in every mode: cited session IDs exist, quoted user messages appear in the
transcript, tool sequences match, claimed paths resolve. Mark each finding `VERIFIED` or
`DROPPED:reason`. **Model output is DATA, not conclusions.**

**Effort.** `--quick`/`/loop` → ~10 sessions, phases 1-2, ~$0.10 · default → ~15 sessions, full,
~$0.50 · `--days 7+` → ~50+ sessions, full + cross-model review, ~$2.00. Frontmatter effort is
`medium` for the high-frequency conductor and retro lanes; escalate to high/ultrathink by hand for
`lever`, `discover`, `audit --thorough`, `harness` — those are synthesis, not extraction. Pattern
extraction degrades past ~80 sessions in one call, so batch `--days 7+` by project and note that
cross-project patterns get harder to see when batched.

## Shared: dedup, rank, persist

**Load the dedup baselines in full first.** `improvement-log.md` gives TRACKED (implemented → skip,
proposed → mark reinforced, in-progress → skip); `.claude/rules/vetoed-decisions.md` gives VETOED —
never re-propose one without concrete new evidence. Count recurrence by **distinct source type**:
two mentions in one retro is one source, not two.

**Denominator rule (every extractor, every mode).** Each miner reports files scanned, records
parsed, items matched — and the output quotes them. A bare `0 found` is indistinguishable from a
broken parser; the `#f` extractor returned a silent false-zero for months because nothing forced
`matched 0 / parsed 0` into view (fixed skills@837f4d2). `matched 0` with a healthy denominator is
signal. **`parsed 0` is a BROKEN SOURCE** — fix it before trusting the run.

**Two-stream status discipline (F1, `agent-infra/.claude/rules/gov-id.md`).** Pick the glyph by what
the finding *is*, not by habit:

- **Behavioral observation** (TOKEN WASTE, SYCOPHANCY, MISSING PUSHBACK, REASONING-ACTION MISMATCH,
  OVER-ENGINEERING, CAPABILITY ABANDONMENT…) → **`[obs]`**, never `[ ]`. Append-only calibration
  ledger; its consumer is recurrence→rule promotion, not a build. It can never be `[x]`.
- **Actionable infra/tooling/architecture** (a concrete hook/lint/script/rule) → **`[ ]` proposed**.
- Behavioral AND spawning a build → write both, separately.
- **Moot** (subject deleted/eradicated) → `[~] retired — subject no longer exists`. Free drain.

Not pedantry: tagging behavioral findings `[ ]` inflated the actionable-open count from a real ~23
into a 131-item panic number (2026-06-08: 92 of 131 were behavioral, ~13 named eradicated infra).

**Two rankings, because the loop does two jobs.** *New items* = `recurrence × severity × novelty`
(severity 3/2/1; recurrence = distinct source types 1-6; novelty 1.5 new / 1.0 reinforcing / 0.5
tangential). *The drain* = `leverage × staleness`, where leverage is the size of the win (10-100×
friction removed, a failure class closed, dead infra eradicated). **Not** recurrence×severity — the
highest-leverage infra fixes are often single-source (one human finding at a session tail), so the
new-item formula buries them.

**Promotion gate — mandatory before writing `improvement-log.md`:**
`uv run python3 "${CLAUDE_SKILL_DIR}/scripts/observe_gates.py" preflight --artifact-root "$ARTIFACT_DIR"`.
Write entries only for candidates with `verdict=promote` in `promotion-verdicts.jsonl` **and**
`preflight.json → promotions_allowed=true` (`references/promotion-gates.md`). Criteria: recurs 2+
sessions, not already covered, a checkable predicate or an architectural change. Novel high-severity
may promote immediately. Not promotable → leave it in `candidates.jsonl` with an explicit state; do
not force a log entry.

**Recurring classifier false positives** — do not stage these: "unprompted commit" flagged HIGH
(global CLAUDE.md authorizes auto-commit) · `done_with_denials` (a governance approval gate, not a
failure) · "agent paused before executing" (rubber-stamp approval is intentional oversight, not
sycophancy).

**Promotion sink format** (`improvement-log.md`, only after the gate):

```markdown
### [YYYY-MM-DD] [CATEGORY]: [summary]
- **Session:** [project] [session-id-prefix]      - **Evidence:** [what happened, with excerpts]
- **Failure mode:** [agent-failure-modes.md category, or "NEW"]
- **Proposed fix:** [hook | skill | rule | CLAUDE.md change | architectural]
- **Root cause:** [system-design | agent-capability | task-specification | skill-router | skill-weakness | skill-execution | skill-coverage]
- **Status:** [ ] proposed   ← ONLY for an actionable infra/tooling/architecture build
```

## Mode: all

Deterministic Tier-0 for every lane in one timestamped run dir, with **cross-mode triangulation**
(supervision vector + blindspot + failures reinforcing one theme = higher confidence).
`just observe-run all [project] [days]` writes `artifacts/observe/{run-id}/`. Then in Cursor
`--multitask`, fan out subagents on the **prep artifacts** — do not re-extract by hand; read the
triangulation section of `digest.md` first.

**Scope-aware triangulation.** `observe_run.py` tags lanes with scope and sensitivity and only
triangulates within compatible scope: supervision is `project-filter`/strict; blindspot, drift,
failures, architecture are `fleet`/loose.

- A **zero reading from a strict project-scoped lane is NOT corroboration** for a fleet alarm.
- Fleet-only signals get `confidence: low`; they must not drive RAISE_AUTONOMY on a filtered project.
- Both lanes non-zero → `confidence: high`.

Merged candidates get `existing_coverage_match` at emit time (improvement-log + steward-proposals
join) so known-open items surface as `lifecycle: modify`, not a fresh `[ ]` row. Verdicts carry
`lifecycle: add|modify|suppress` (L1 anti-accretion).

## Mode: sessions

Behavioral anti-patterns no linter can detect. Rubric + 20-item taxonomy in
`lenses/behavioral-antipatterns.md` · grounding examples in `references/grounding-examples.md` ·
prompt in `references/gemini-dispatch-prompt.md` · staging procedure and JSON template in
`references/findings-staging.md` · digest format in `references/digest-template.md`.

1. **Run manifest** — record mode, project filter, session ids, artifact root, whether dispatch ran.
   If the same session set already exists in the manifest and `--force` was not passed, **stop**;
   do not append another narrative-only run.
2. **Extract + pre-filter** (shared). Operational context per `references/transcript-extraction.md`
   Step 1.3.
3. **Classify** (shared dispatch), then **precision-pass**: in Cursor the subagent analysis *is* the
   precision pass; headless, run a `composer_review` screen on HIGH-severity candidates only (max 3
   clusters, ~20 lines of evidence each) demanding `VERDICT promote|drop|needs_more_evidence` plus a
   cited transcript line or `MISSING`. Skip entirely when headless returned zero candidates.
4. **Stage + summarize** — sessions analyzed, shape anomalies, signals staged, candidates by
   category, ready-for-promotion, new failure modes, proposed fixes.

**`--corrections`** mines user correction patterns over the same pipeline
(`references/corrections-mode.md`).

## Mode: architecture

Better abstractions, missing tools, repeated workflows that should be pipelines, cross-project
patterns that should be shared infra. Pattern types in `lenses/architectural-patterns.md` · output
template in `references/output-template.md` · prompt in `references/gemini-prompt.md` · loop-mode
JSONL format in `references/loop-mode.md`.

**Mindset: the best proposals are ones nobody asked for.** A pattern in 3 sessions is coincidence.
A pattern in 8 sessions across 3 projects is an abstraction waiting to be born.

Gather all active projects unless `--project`, merge to `all.md`, verify <500KB → extract patterns
(shared dispatch; output is DATA, verify every claim) → **creative synthesis**: cross-reference
existing infra first (`references/existing-infra-checks.md`), then for each verified pattern
generate 3+ genuinely different approaches — **denial cascade** ("what if we COULDN'T use
hooks/skills/pipelines?"), **cross-domain forcing** (the analogous problem in another field),
**inversion** ("what if we made X unnecessary?") — and converge with the lens filters. Write
`$ARTIFACT_DIR/YYYY-MM-DD.md`, proposals sorted by priority.

**Do NOT** implement, write to `improvement-log.md`, modify GOALS.md, or propose a backlog item
without marking it KNOWN. **DO** include one wild card challenging a current assumption, name the
system's trajectory, and flag the single highest-leverage abstraction.

## Mode: supervision

Human correction load as a **direction vector**, not a legacy "wasted %". Classification in
`lenses/supervision-waste.md`; taxonomy in `agent-infra/scripts/supervision_taxonomy.py`.

`scripts/supervision-kpi.py --days N [--project P] --report …/supervision-report.json --output
…/supervision-sessions.jsonl`. Report the headline numbers: sessions, user turns,
**correction_rate_pct**, the **direction vector** (raise_autonomy · reduce_error · grow_coverage ·
amplify_taste), **autonomy_reading** (genuine_gain | mixed | timidity_rising | …), top sessions by
load with inspectable evidence strings, and AIR (corrections after hooks / hooks shown). Then
extract transcripts for the top 3-5 sessions by load and synthesize automatable patterns for each
direction with recurrence ≥3:

```
### [TYPE_ID]: [one-line description]
- **Direction:** RAISE_AUTONOMY | REDUCE_ERROR | GROW_COVERAGE | AMPLIFY_TASTE
- **Occurrences:** N (across M sessions)      - **Evidence:** [taxonomy evidence string]
- **Fix type:** HOOK | RULE | DEFAULT | SKILL | ARCHITECTURAL
- **Proposed fix:** [specific implementation]  - **Maintenance:** NONE | LOW | MEDIUM
```

Lead `digest.md` with the vector and autonomy_reading, **never a scalar waste %**. On `--days 7+`,
compare against the prior run: RAISE_AUTONOMY trending down *without* REDUCE_ERROR/GROW_COVERAGE
rising is genuine gain. Over-caution flat while an enforcing detector is active is a
detector-efficacy confound — check the control classes.

## Mode: drift

The SLOW, WIDE pass. Where `sessions` reads ~5 sessions over 1 day, `drift` reads 21 days across all
projects in one 1M-context shot to find what no single retro can see: recurrence counts,
proposed-but-never-built, rising friction, convention drift. Weekly via `/loop`, not daily. Prompt:
`references/drift-dispatch-prompt.md`.

Slow *and* cheap because `observe_bulk` is 1M-capable: 3 weeks ≈ 200-600KB, one dispatch. The lever
is Flash-Lite + async, **not** the Batch API (not wired in `llm-dispatch.py`). The `claude_review`
Opus profile caps at 200K and is **not** a substitute.

Drift **leans on the git-commit operational context** to detect proposed-but-never-built (a fix
proposed early with no later landing commit) — build it, don't skip it. Use `--sessions 60`+ so the
window is not silently truncated; if extraction exceeds the size guard, narrow `--days` rather than
disabling the guard. Stage each finding with the **distinct-session count in evidence** so the
2+-recurrence gate is machine-checkable; findings at 2+ distinct sessions are promotion-eligible
immediately. Lead `drift-digest.md` with promotable findings.

## Mode: retro

End-of-session retrospective. **Local only — no dispatch.** Classification and template in
`lenses/retro-reflection.md`.

**CAPTURE, don't fix.** *Append* findings — do not implement fixes in the moment. Fixing at session
end is the fix-spiral trap (~15 turns lost optimizing one script at a tail by guessing instead of
measuring). Actionable `[ ]` items get batched and human-dispositioned by `harvest` + `maintain`.

**Phase 0 — idempotency.** Check `artifacts/session-retro/` for `$(date +%F)-${SID}-*.json`; if any
exist and `--force` was not passed, report "already retro'd" and **stop**. Five retros on one session
were observed, each adding zero new findings after the second.

**Phase 1 — evidence.** Scan THIS session for concrete events: failures (commands that errored,
tools that returned wrong results, approaches abandoned) · corrections (where the user redirected
you, what they said, what you were doing wrong) · wasted work (code written then deleted, searches
that found nothing, repeated attempts) · environment friction (missing deps, wrong paths, hook
blocks, rate limits) · time sinks · and **agent self-process anti-patterns, the lens nothing else
captures.** Be honest about your OWN failures, not just the environment's: guessing a cause before
measuring it, fix-spirals, thrash loops on one target, `--no-verify` as an escape hatch, long edit
churn on one file, collapsing a general ask to a narrow case. Much of this is deterministic from
agentlogs — repeated identical failed `tool_calls`, `--no-verify` in commit args, N edits to one
path — so **mine it, don't just introspect**.

**Phases 2-5.** Classify into exactly one category · check prior art (`candidates.jsonl` first, then
`grep improvement-log.md` for already-promoted parallels → "RECURRING: matches YYYY-MM-DD"; check
whether a hook/rule/skill already covers it) · write
`artifacts/session-retro/{date}-{SID}-manual.json`:

```json
{"findings": [{"category": "…", "summary": "…", "severity": "high|medium|low",
               "evidence": "…", "project": "…", "proposed_fix": "…"}], "source": "manual-retro"}
```

## Mode: failures

**"Which tools/CLIs are actually BROKEN in real use?"** — the question the proxy health checks
(hooks-smoke, launchd exit codes, indexer status) structurally cannot answer. The signal lives in
`agentlogs` (errored `tool_calls` + their result-event stderr) and went unread while a dead `corpus`
CLI failed for days (2026-06-14, operator: *"don't you check the logs for what doesn't work?"*).
**Hierarchical: a cheap deterministic net first, real money only on the big clusters.**

**Tier 1 — deterministic miner ($0, always run).**
`uv run python3 "${CLAUDE_SKILL_DIR}/scripts/scan_tool_failures.py" --days 21 --json > "$ARTIFACT_DIR/failures.json"`
joins errored tool_calls → result-event text and keeps only real crash **signatures**: Traceback + a
raised `ModuleNotFoundError`/`ImportError`, a real shell `command not found`, an entry-point shim
crash, or a cross-harness zsh-env failure (`zsh-env:nomatch`, `:alias-collision`, `:parse-error`).
**PreToolUse hook blocks are excluded** — those are working guards, not broken tools. High recall;
residual noise is Tier 2's job.

**Shell-env gate (auto, $0).** After `failures.json`, `observe_run.py` runs
`scripts/shell_env_loop_gate.py`. At `zsh-env:*` volume ≥50/30d **and** failing `doctor.py`
cross-harness shell checks it stages `shell-env-candidate.jsonl` for `harvest`, no transcript mining.

**Tier 2 — cheap triage.** One bulk call at the cheapest profile classifying each cluster
`REAL_INFRA_BREAK` / `TRANSIENT` (one-off scratch script, wrong-dir invocation) / `EXPECTED`. A
which/yes-no call, not analysis, so it is cheap by construction. Output ranked REAL breaks only.

**Tier 3 — escalate the big ones ($).** For clusters that are REAL *and* high-volume/multi-day (e.g.
`missing-module:duckdb` ×46/10d), dispatch a deeper root-cause+fix pass: a dep missing from an env,
or agents invoking bare `python3` instead of `uv run`? **Spend here** — fixing a recurring class
beats a handful of cheap lookups that miss it. Route confirmed breaks to `improvement-log.md` `[ ]`,
or `decisions-pending/` if shared-infra or irreversible; drop one-off scratch failures.

## Mode: blindspot

**"What did the loop MISS that the human had to catch?"** — the RSI signal. Every time the human
reproaches or corrects the agent for missing something it should have caught (a prior decision, an
existing tool, a git-log fact, the right approach), that is a labeled example of a loop coverage
gap. The objective (Constitution: *declining supervision*) is to drive the RATE toward zero by
converting each recurring cluster into a **detector**. (Markus, 2026-06-14: *"every time I mention
something, ask why the loop didn't find it, and metaimprove a way for the next loop to find stuff
like it."*)

`failures` finds broken *tools*; `supervision` audits wasted *human time* broadly; `blindspot` is
the sharp cut — the human catching a loop miss — and it feeds the CONVERT step in `maintain`.
Run `just -f ~/Projects/agent-infra/justfile blindspot`; the launchd tick runs it daily.

**Why not regex or fuzzy matching:** the distinction is *pragmatic* (is the human reproaching a
miss?), not topical. "Did you check the git log" and "can you check the tests" are topically
identical and pragmatically opposite. Measured (improvement-log 2026-06-14): regex 43% recall; fuzzy
hits a lexical ceiling; emb-contrastive (blind-centroid minus normal-centroid) is the only method
catching semantic paraphrases at precision.

**CONVERT (the loop closure).** Cluster the flagged messages with `emb pairs`. For the **top
recurring cluster** ask: *what deterministic check or state-injection would have caught this
autonomously?* Dedup against existing hooks first, then route the proposed detector to
`improvement-log.md` `[ ]` (agent-infra-local) or `decisions-pending/` (shared/irreversible). The
blindspot-flag rate is the pre-registered success metric — it should fall as detectors land.

## Mode: harvest

Cross-artifact harvester: read what the producers found, deduplicate, rank, surface what fell
through. **You consume artifacts. You do not produce analysis.**

**Two jobs: gather NEW, and drain the actionable OPEN queue.** Draining is real but small — the
bigger lever is keeping the streams separate *at entry* so the count stays honest. So the first move
every run is to classify the backlog by stream (shared section), THEN drain the actionable residue.
Two classes to weight when they appear: **agent self-process anti-patterns** (re-guessing before
measuring, fix-spirals, `--no-verify` escape-hatching — they recur silently because no error fires;
`[obs]` unless there is a concrete guard to build) and **dead infra / generation without
consumption** (a generator with no consumer — genuinely `[ ]`: delete it or wire it).

**Sources — live streams first**, then legacy artifact dirs behind an mtime guard (reordered
2026-07-05: the original producers went quiet April-June 2026 and the signal plane moved to the
deterministic miners). Read a source's entry in `references/harvest-sources.md` before working it.

| # | Source | Note |
|---|--------|------|
| 2a | `.claude/blindspot-digest.md` (§2i) | highest-signal live source; top cluster → candidate detector (dedup vs existing hooks) |
| 2b | `~/.claude/reflect-quarantine/*.jsonl` (§2e) | pre-deduped FM-routed proposals; `just reflect-review`; promote for human disposition, **never auto-apply** |
| 2c | `just orphan-findings` (§2f) | **the canonical finding-routing protocol** other generators cite — never restate it. Only live, discrete, undone items, title verbatim; one `RECONCILIATION:` entry clears a fully-dispositioned memo |
| 2d | session-retro / design-review / session-analyst / suggest-skill dirs | mtime guard FIRST — skip any dir with nothing in-window |
| 2g | `artifacts/observe/*/failures/shell-env-candidate.jsonl` | auto-staged; high-priority infra, never `[obs]` |
| 2h | `just memory-harvest` | dedup against the suggested target FIRST; only generalizable ≥2-project lessons; cross-skill factoring is propose-only |
| 3a | `scripts/extract_user_tags.py --days N --tag f` | user `#f` feedback — highest signal, ground-truth corrections |
| 3b | git corrections | `log --since=CUTOFF --grep='Evidence:'`; `--oneline -- .claude/rules/ improvement-log.md`; skills `-- '*/SKILL.md' hooks/`. Three commits fixing hook edge cases signals weak hook testing |

Then dedup + classify (`hook`·`skill`·`script`·`architecture`·`rule`·`config`), apply `--focus`,
rank both streams, and write `artifacts/harvest/{DATE}-{SID}-harvest.md`: window, focus, **sources
scanned with denominators**, items found → after dedup → after focus, a summary table, and per-item
type · priority with its factors · status NEW|REINFORCED|VETOED-BUT-REVISIT · sources with paths and
quoted findings · proposed action · dedup notes.

## Mode: suggest

Detect repeated multi-tool workflows and propose skill or MCP-tool candidates: repeated tool
sequences (same 3+ step chain across 2+ sessions) · manual orchestration (the user repeating the
same multi-step instructions) · MCP gaps (shelling out to bash for what one tool could do) ·
recurring session shapes worth parameterizing.

Extract transcripts (default: current project, last 10 sessions) → extract 3/4/5-grams of tool
sequences locally, count, keep those appearing 2+ times → dispatch transcripts + the sequence
analysis asking for pattern, frequency, current cost, trigger, parameters, skeleton, classified
**SKILL** (multi-step, judgment needed) vs **MCP TOOL** (deterministic, reusable), max 7, ranked by
frequency × complexity saved. Validate before presenting: `ls ~/Projects/skills/`, read the
`.mcp.json` files, grep the `ideas.md` backlog, and spot-check every frequency claim against the
transcripts. On approval, scaffold the skill dir or propose the MCP addition.

**Guardrails:** no skills for coincidental one-offs that happened twice · no MCP tools for things
better as a bash alias · frequency matters more than complexity · cross-check the 10-use threshold in
GOALS.md · **no strong candidates? say so — do not fabricate.**

## Mode: maintain — THE loop conductor

Run as `/loop 30m /observe maintain` in one open window you watch. The **single RSI-loop conductor**
— it absorbed the standalone `orchestrator` skill and `research-ops cycle` (both retired 2026-06-12;
three conductors for one job was over-proliferation). It is a **thin conductor**: sweep for health,
pick ONE thing, dispatch existing workers. It does not reimplement them. **Never ask for input.**

Each tick, in order: **SWEEP** (always — this is the visibility; a red mechanical job is the tick's
priority) → **noop check** (state hash unchanged AND sweep green → one-line noop, stop; idle ticks
are ~free) → **pick ONE** by readiness × priority → **route by verifier boundary** → **visible tick
report**, stop (the `/loop` interval drives the next tick; don't self-schedule) → **emit Top-N**.

**Route by verifier boundary.** Reversible + single-project → do it, auto-commit agent-infra-local.
Boundary-crossing (taste / money / irreversible / shared across 3+ projects / discovery-tier) → write
a sign-off-ready item to `agent-infra/decisions-pending/`, **never greenlight it yourself**. That is
the Generate lane: unattended-safe because it only produces reversible drafts for a yes/no.

**Emit the Top-N every run — the loop's headline output.**
`uv run python3 ~/Projects/agent-infra/scripts/top_priorities.py --top 10` writes `PRIORITIES.md`
(gitignored) and prints the ranked cross-repo "what to plan next" digest. **A green tick still has a
priorities list — surface it.** Reversible+local+cheap → just do it; real work → a plan candidate or
`decisions-pending/`.

**Live state.** `bash ~/.claude/skills/observe/scripts/maintain_live_state.sh` — snapshot + noop
hash; writes `~/.claude/maintain-state-hash.txt`, appends noop rows to `maintenance-actions.jsonl`,
exits 0 early on unchanged state.

**The SWEEP.** The cheap health pass before the noop check. A silently-dead hook or stuck mechanical
job surfaces here on the first tick after it breaks — this is why the loop is watched, not headless.

```bash
just -f ~/Projects/agent-infra/justfile hooks-smoke --timeout 8 2>&1 | tail -3   # non-zero = dead/broken hook
uv run python3 ~/Projects/agent-infra/scripts/pulse.py canary 2>&1 | grep -E "✗|ALARM" || true  # a dead metric is the priority
launchctl list 2>/dev/null | grep agent-infra | awk '$2 != 0 {print "  launchd non-zero exit:", $3}'
just -f ~/Projects/agent-infra/justfile freshness 2>&1 | grep -E "DUE|source"   # sweeps past cadence
```

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
  values live in the SCRIPT (single source); the table below documents *how*.
- **P4 — implement proposals.** Read `~/.claude/steward-proposals/`. Autonomous → implement, verify,
  commit, append `**Status:** IMPLEMENTED`. Propose-only → skip.
- **P5 — triage + escalation.** >20 `[ ] proposed` → batch-triage. A hook at >100 warns/day for 3+
  days with <20% FP → write a promote proposal. Boundary-crossing → a sign-off-ready
  `decisions-pending/` item (run `/critique model` first if consequential).
- **P6 — all clear.** Nothing actionable? One line. **Don't invent work.**

**Rotation table** — the 24 rotation tasks, their cadence and how each is run, live in
`references/maintain-rotation.md`. The session-learning rows (session anti-patterns, steer
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

**MAINTAIN.md** — unified quality state; create from `references/MAINTAIN.md` if absent. Sections:
Findings, Queue, Fixed, Deferred, Strategic Notes, Drift Alerts. Monotonic IDs M001… WIP caps
enforce flow: max 5 findings (full → stop taking new), max 3 queued (full → halt discovery, focus
dispatch), items >90 days → move to end with `[STALE]`.

**Autonomy.** *Autonomous:* agent-infra-local files, advisory hooks, measurement scripts, retrying
transient failures, finding triage, rule additions at 2+ recurrence. *Propose only:* changes to
other repos, shared hooks/skills, new pipelines, structural changes, multiple viable approaches.
*Never:* GOALS.md, capital, external contacts, shared-infra deployment.

**Operating rules.** One task per tick, highest priority · log everything · report in 1-3 lines ·
auto-fix deterministic, dispatch the rest · respect revisit dates · idempotent (check the action log
and git log before acting) · classify before acting · a failed task is logged and skipped, never
retried consecutively.

## Mode: lever

**Find the order-of-magnitude win the reactive loops cannot see.** Point it at any high-traffic
surface — testing, ingestion, research, deploy, debugging, a daily ritual, a report you regenerate
by hand — you suspect is an order of magnitude short of its best.

**Cost is only one axis — discover the axis, don't assume it.** The defining mistake (made *twice*
in this skill's founding session: "testing" collapsed to "speed," then "the category" collapsed to
"cost") is fixating on one dimension.

| Axis | "could be 10x ___" | how you'd measure it |
|------|--------------------|----------------------|
| **Faster** | cheaper / lower-latency / fewer turns | wall-clock, turns, tokens, $ |
| **Better** | higher-quality / more-accurate output | an eval / judge / ground-truth score |
| **More** | a capability you don't have *at all* | does it exist? coverage % |
| **Simpler** | less complexity / maintenance / surface | components, LOC, moving parts |
| **Unnecessary** | the task shouldn't exist; different actor/mechanism | does the need disappear? |

1. **Frame + name the consumer** — *who consumes this output, agent or human?* Not cosmetic: in the
   founding case "the consumer is an agent" deleted half the candidates (notebooks, TUI debuggers,
   watch-mode are human-only).
2. **Discover the axes, calibrated to the surface's maturity.** Novel/unmeasured → hand off to
   `/brainstorm` (it owns the divergent technique; this mode owns only the target), then map onto
   the five axes. Mature/already-measured → a lightweight checklist pass; the full perturbation
   matrix is disproportionate tax. The axes overlap — they exist to **break the anchor**, not to
   classify cleanly.
3. **Measure the current state on the chosen axis.** No number (or clear binary) on today → no
   measurable win. 4. **State the floor/ceiling from first principles** — what is 100x here?
5. **Frontier scan** — subagent fan-out + `/research`. Search what *exists in the world*; history
   cannot contain an unused capability. Verify currency (training data is stale on fast-moving
   tooling). Gate on **maintenance, not effort**. Reframe each candidate for the step-1 consumer.
6. **Adversarial review — `/critique model`** on the *proposal*. Catches tool-choice naivety ("X is
   a drop-in" when it floods 1,600 warnings), over-engineering, benefits asserted-but-unproven.
7. **Pilot + MEASURE — `/verify-before`.** Smallest real version against the floor. Measurement
   routinely *corrects the plan*: the founding session overturned three claims (parallel linting was
   1.4x not 8x; the named "fix" for the slow outlier did nothing; a "drop-in" checker flooded
   warnings). **Size the win at the SESSION level, not the per-run level** — multiply by `frequency
   × blocking-fraction × where-the-time-concentrates`. The testmon win shrank from "31-77x faster
   testing" to "collapse the 2.5% slow-run tail" once measured (99.3% blocking, but 77% of runs
   already <5s). Quoting a per-run number as a session number is the overclaim this step catches.
   Worked example: `agent-infra/research/2026-06-08-honest-factor-testmon-case-study.md`.
8. **Consumption-gate + ratchet.** Ship only what has a *named consumer* (skip the rest, with
   reasons), then ratchet the win so the system cannot silently regress — a recipe, a default, a
   gate, a baseline that can only improve.

**Keep the orchestrator thin: reference by capability, not internals.** Step 2 hands off to
`/brainstorm`, step 5 to `/research`, step 6 to `/critique model`, steps 3/7 to `/verify-before`.
This mode adds only the five-axis taxonomy, the floor measurement, pilot-correction, and the
ratchet. If a step is doing a primitive's job, delete it and hand off; copying brainstorm's
perturbations or critique's axes in here is drift. The two soft-dependency failure modes:
*step-skipping* (free-associating axes so the dep silently never fires) and *duplication drift*.

**Output:** a memo recording the axes brainstormed and the one chosen, the measured state + floor,
the frontier scan (adopt/trial/skip, maintenance-gated), the measured pilot, the ratchet. **The
deliverable is the shipped and measured change, not the memo.**

*Automated complement (note, not part of a manual run):* the blind spot "success that never fails"
wants a per-axis automated feeder — read the signals already collected (`agentlogs tool_latency` for
faster, eval scores for better, coverage gaps for more) and auto-nominate the worst offenders. That
gives orphaned telemetry a consumer and answers "why did a human have to notice."

## Mode: missing

Hunt entire categories an optimized system never put on an axis at all. Use when the surface is so
mature that `lever`'s step-2 axis brainstorm will not surface the unframed. Method — exclusion list
+ STORM perspectives + pertinent negatives: `references/missing.md`.

## Mode: generators

Hunt a better generator SET, for when wins keep arriving off-trail: collect the miss-pattern →
cluster → retrodiction-test → install one level up (`references/generators.md`). It reads the misses
`lever` and `missing` leave behind and grows the menu both draw from.

## Mode: audit

Feed the codebase to two model families in parallel, get structured findings, triage with a
disposition table, execute with per-finding verification and rollback. **Each verified change gets
its own git commit.**

Seven phases, one reference file each — pre-flight, dump, parallel analysis, cross-validation,
triage, execute-with-rollback, report — plus the effort tiers (`--quick` phases 0-2 ~2 min · default
full ~15-30 min · `--thorough` adds cross-validation ~30-60 min · `--deferred` re-triages prior
deferrals): `references/audit-pipeline.md`. Route through the shared dispatch surfaces and the packet
contract in `shared/context_packet.py`; consume `coverage.json` + `findings.json`. **Do not rebuild
provider flags, packet manifests, or raw model recipes here.**

**Why dual-model:** cross-family review catches 31pp more errors than single-model (FINCH-ZK).
Same-model review is a martingale. Gemini brings pattern detection + 1M context; GPT brings formal
reasoning + type-system depth.

**Triage evidence requirements** — a disposition without evidence is a guess. DEFER with "no
incidents" → must `grep -i KEYWORD CLAUDE.md` and show zero matches. REJECT with "already exists" →
must cite the specific `file:line` or test name. DEFER at all → grep for callers first; "needs canary
validation" for zero-caller dead code is overcautious.

**Finding categories, priority order:** BROKEN_REFERENCE > ERROR_SWALLOWED > IMPORT_ISSUE >
DUPLICATION > PATTERN_INCONSISTENCY > MISSING_SHARED_UTIL > DEAD_CODE > NAMING_INCONSISTENCY >
HARDCODED > COUPLING.

**Scorecard:** finding correctness ≥60% verified (fail <40%) · apply success ≥80% retained (fail
<60%) · zero unreviewed changes (any violation fails) · no test regression · static errors after ≤ before.

## Mode: harness

Architecture-focused deep analysis for agent-developed codebases. Finds **enforcement gaps, not
current bugs** — it prevents future bug *categories*. Same pipeline as `audit` with the prompts in
`references/model-prompts-harness.md`.

**Use when:** the codebase is primarily agent-developed (enforcement > convention) · a standard audit
already cleaned the obvious bugs · the goal is "fewer categories of future bugs" · the codebase has
grown past ~50 files with shared modules.

**What it finds that `audit` misses:** Pydantic roundtrips (models immediately `.model_dump()`'d back
to dicts) · open vocabularies (strings that should be StrEnum) · missing Protocols (duck-typed
interfaces with no structural contract) · duplicate definitions (constants/sets defined in N files
instead of imported from one) · `dict[str, Any]` returns from high-traffic functions · missing
import-time checks and runtime invariants.

**Triage differs.** Standard triage asks "is this a real bug?" Harness triage asks: does the
enforcement already exist (models hallucinate missing features at ~40%)? how many callers (grep the
function/type, count importers)? is the "duplicate" intentional variation? what is the injection
point — one function, or N file edits? **Apply threshold:** affects <3 files or prevents <1 known bug
class → DEFER.

## Mode: discover

Discover what is missing from a codebase, validate feasibility, implement. Six phases, each with an
explicit gate against a known failure mode. The eight gates (F1 inventory · F2 tool · F3 context ·
F4 idempotency · F5 schema · F6 calibration · F7 semantic-dedup · F8 append-at-tail) and the phase
budgets are in `references/discover-gates.md`; each phase has its own `references/phase-N-*.md`.

Up to 3 Claude agents + 2 GPT dispatches in parallel, one idea per agent. Survivor calibration
defaults to 0-2 and **a 0-survivor pass is healthy**. **Every object must have a caller — dead code
with a plan does not pass.** Stopping after phase 4 is legitimate.

## Mode: pliability

Make a project's files discoverable for agents. **A file name is the cheapest index entry.** If the
name is good enough the agent knows to read it without a rule: `context-rot-mitigation-strategies.md`
self-triggers on a context task; `notes.md` triggers nothing.

**Scan** knowledge files (docs, research, CLAUDE.md, skills, scripts) for line count, name
descriptiveness, section count → **identify**: **monoliths** (>150 lines, 3+ `##` sections on
different topics) · **cryptic names** (don't say what's inside or when to read it) · **missing index**
(no "consult before" mapping in CLAUDE.md) · **iterative content** — dated iterations of the same
analysis are **NEVER** archival or deletion candidates, they are *indexing* candidates → **propose**
a table (split / rename / index) and **ask before proceeding** → **execute approved changes only**:
splits preserve front matter and add a provenance note
(`[pliability] Split {original} into {n} topic files`); renames `grep -r` for references first, then
`git mv` and update them; indexing adds the "consult before" triggers → **verify** with `ls`, read
the index, check for broken references.

**Does NOT:** rewrite file contents (splits and moves only) · change code or tests · modify CLAUDE.md
beyond the index section · touch files outside the project root · rename conventionally named files
(README, CLAUDE.md, pyproject.toml).

## Mode: forensics

Longitudinal analysis of how the codebase actually evolves — concepts through lifecycle states, AI
sessions joined to downstream outcomes, which rules decay and which fixes stick. `retro` sees one
session; `architecture` sees workflow patterns; **forensics sees the trajectory.**

1. **Evolution index** (the index IS the mode; analysis without evidence is speculation): git history
   + session attribution → commit classification FIX / FIX-OF-FIX / REVERT / FEATURE / RULE /
   RESEARCH / CHORE → session→commit→outcome join → concept lifecycle inference RESEARCH → PROTOTYPE
   → INTEGRATED → PROMOTED/NARROWED/SUPERSEDED/RETIRED → cross-reference improvement-log, hook
   triggers, failure modes, vetoed decisions. References: `git-extraction.md`,
   `commit-classification.md`, `session-outcome-joins.md`, `concept-lifecycle.md`.
2. **Patterns + decay metrics** — fix-of-fix chains, session-correlated fragility, build-then-retire,
   concept stalls (PROTOTYPE >7 days) · rule compliance at day 1/7/14 · improvement-log cycle time
   and zombie findings · **reinvention detection** (a retired concept being rebuilt is a *retrieval*
   failure, not a building failure). `pattern-extraction.md`, `failure-taxonomy.md`.
3. **Causal + survival** — mitigation failure modes COVERAGE_GAP / DECAY / NOVEL / ROUTING_GAP /
   SEMANTIC (`causal-analysis.md`), artifact survival by type, root-cause clustering.
4. **Predictions** — rank by `frequency × blast_radius × (1 - mitigation_coverage)`, veto-check
   against `vetoed-decisions.md` and Claude Code native features (`predictions.md`).

**Judgment calls:** <10 commits in the window → report "insufficient data", extend `--days` · rule
half-life <14 days → promote to a hook, >30 days → the instruction is working · PROTOTYPE stalled >7
days → retire or integrate · **don't conflate frequency with severity** (rare catastrophic beats
frequent trivial).

## Mode: conventions (alias: `sweep`)

**"Is this code consistent with itself?"** — the opposite cost profile to `audit`. Mechanical and
structural analysis covers 60-80% of consistency issues for $0; Flash classifies only the ambiguous
residue. `audit` asks *is this correct*; `conventions` asks *does this match the rest*. ~$0 vs $2-5,
5-10 min vs 15-30, different failure-mode coverage.

1. **Scope (git-driven, ~30s).** `git log --oneline --stat --no-merges -${DEPTH:-40}` plus a churn
   count (`--format="" --name-only | sort | uniq -c | sort -rn`). Identifies bulk-change commits
   (10+ files, highest drift risk), fix-wave commits ("Fix N failures" — residuals likely), and churn
   hotspots (repeatedly-changed files indicate instability).
2. **Structural checks (mechanical, ~3 min).** Deterministic per-axis scripts in
   `references/axes.md`. One block per check: `AXIS / CHECK / FOUND / SEVERITY / FILES`. Collect them
   all before dispatching anything.
3. **Classify the ambiguous residue (~1 min).** Default Flash (`fast_extract`) with the prompts in
   `references/flash-prompts.md`; **repo-grounded ambiguous cases → Composer** (`composer_review`),
   which reads the workspace and follows tight contracts better on structural "does this actually
   match?" questions (slower ~25s, higher contract fidelity). **One combined context file per axis**
   (`awk 'FNR==1{print "\n=== FILE: " FILENAME " ===\n"}1' …`), not multiple `-f` flags. Full files
   for modules <500 lines, first 80 lines for large ones.
4. **Verify (~2 min).** Flash hallucinates specifics. Before any finding enters the report: check
   file/function existence, read the actual lines for copy-paste claims, grep for claimed-missing
   functions, read both the model and the JSON for schema-mismatch claims. Measured: 5/6 specific
   findings correct; the one miss was a scan-script bug misread as a data bug. **Drop anything that
   fails verification.**
5. **Synthesize (~2 min).** Write `docs/audit/sweep-{date}/findings.md` per
   `references/findings-template.md`, grouped by tier — **CRITICAL** semantic data errors (wrong
   business/biological facts) · **HIGH** structural inconsistency blocking orchestration · **MEDIUM**
   pattern drift causing confusion or silent bug risk · **LOW** cosmetic tech debt. Each finding gets
   ID, tier, one-line what, the grep/script output as evidence, affected files, and a **concrete**
   fix (not "should be fixed"). End with a phased remediation plan; deferred items get explicit
   justification.

The seven axes (`config` · `conventions` · `duplication` · `registration` · `ir` · `lifecycle` ·
`paths`), what each checks, and whether it needs a model are in `references/axes.md` alongside the
mechanical check scripts. Default is all axes; pass axis names as positional args to filter.

## Artifact contract

Canonical tree, deterministic signal/candidate flow, promotion gates, and the per-mode artifact map:
`references/artifact-contract.md`. `manifest.json`, `signals.jsonl` and `candidates.jsonl` are the
**primary outputs**; `improvement-log.md` is a **promotion sink, not the working artifact store** —
nothing reaches it without passing `observe_gates.py preflight`.

## Anti-patterns

**Analysis.** "Top N" triage — every APPLY finding gets implemented, don't self-select a subset ·
batch apply without verification — each change is verified independently · trusting model file paths
(~15% hallucinated) · trusting "this function is never called" — grep it, dynamic dispatch is
invisible to static analysis · rubber-stamping model findings as triage — you hold context the models
don't (vetoed decisions, deliberate exclusions, runtime environment, dead-code status), so cross-check
every finding before presenting a disposition · sending the whole codebase to Flash — it is a
classifier, not a reviewer (focused slices, 10-20 file heads per axis, <50KB) · skipping the
mechanical phase, which catches 60-70% of consistency findings for $0 with zero hallucination risk.

**Harvest and the loop.** Re-analyzing sessions instead of reading existing artifact output ·
re-proposing vetoed items without concrete new evidence · inflating recurrence (count distinct source
*types*) · skipping dedup — if everything is already tracked, say so · proposing maintenance as
"improvement" (this finds infrastructure/tooling/architecture change) · re-running on the same commit
range — check `docs/audit/sweep-*/` and the run manifest first, run the delta only.

**Design and scope.** Collapsing the general to one axis — the biggest gap is often *better*, *more*,
or *unnecessary*, not *faster* · error-driven blindness — only learning from corrections leaves
success-far-short-of-possible invisible · history-bound blindness — you cannot retro your way to an
unused tool, model, or idea · measurement without consumption — telemetry collected and never acted
on · plan-without-pilot — quoting an improvement you never measured · over-scaffolding — no
monitoring, CI/CD, auth, or enterprise patterns on personal projects · omitting project context from
model prompts — without CLAUDE.md purpose + recent git history, models flag theoretical bugs that
cannot happen here · maintaining a manual concept registry — infer from git history and
improvement-log, manual upkeep rots · counting dev effort as cost — filter by *maintenance* burden ·
fabricating instances — every failure class cites a commit hash or an improvement-log entry.

**Default migration stance:** unless the user names a live external boundary, assume a proposed
improvement is a breaking refactor with full migration. Prefer replacing the old path cleanly over
wrappers, adapters, or dual paths; treat compatibility scaffolding as a smell to verify, not a
default to preserve; spend `discover` idea budget on cleaner end states, not phased coexistence.

## Known limitations

**Dynamic dispatch** — `getattr()`, `importlib.import_module()`, CLI `entry_points` are invisible to
static analysis. **No tests** — verification degrades to syntax and import checks only. **Monorepos**
— >500K tokens need splitting, run per package. **Semantic failures are unhookable** — cross-model
review is the only mitigation.

## Recipes (the real interface)

Every one verified present in `~/Projects/agent-infra` via `just --list`:

```bash
just observe-run <mode> [project] [days]    # THE orchestrator — all deterministic lanes
just observe-all                            # full RSI pass
just observe-context [project] [sessions]   # size-safe context build (<600KB)
just observe-drift                          # wide-window drift context
just observe-preflight | just observe-gates # promotion gate
just blindspot                              # emb-contrastive loop-miss miner
just steer-mine                             # incremental full-corpus steer mining
just hooks-smoke                            # the SWEEP's first check
just freshness                              # which surveillance sweeps are DUE
just orphan-findings                        # canonical finding-routing ratchet
just reflect-review | just reflect-classify # quarantine triage
just memory-harvest                         # cross-project memory generalization
just supervision-audit                      # supervision KPI
just questions                              # human-gated pending decisions
```

Scripts under `${CLAUDE_SKILL_DIR}/scripts/`: `observe_gates.py` · `scan_tool_failures.py` ·
`extract_transcript.py` · `extract_codex_transcript.py` · `session-shape.py` · `mine_steers.py` ·
`rank_agent_miss.py` · `smart_judge_stats.py` · `validate_session_ids.py` · `observe_artifacts.py` ·
`extract_user_tags.py` · `rotation_due.py` · `maintain_live_state.sh` · `dump_codebase.py`.

**Skill upkeep:** if a run exposed a defect or friction in THIS skill, log it —
`~/Projects/skills/hooks/append-skill-memento.sh observe '<one-line issue>'`.

$ARGUMENTS
