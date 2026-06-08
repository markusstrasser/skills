---
name: leverage
description: "Hunt order-of-magnitude (10-100x) workflow wins your reactive loops can't see — audit ambient COST not bugs, scan the external tool frontier not your history, pilot+measure. 'why is this slow even though it works', '10x this', 'biggest lever here', 'frontier audit', 'what are we doing the dumb slow way'. The generative twin of /observe."
user-invocable: true
argument-hint: <workflow or surface to 10x> [--repo path]
context: fork
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: high
---

# Leverage — find the order-of-magnitude wins your reactive loops can't see

## Why this exists (the category failure it fixes)

Self-improvement machinery — `/observe`, session-analyst, the error-correction git
log, "recurring pattern → architecture" — is **reactive and history-bound**. It
learns from errors and corrections. That makes it structurally blind to an entire
class of improvement:

- **Friction that never fails.** A test loop that takes 70s and *passes* produces
  no error, no correction, nothing to learn from. Ambient latency / cost / manual
  repetition is invisible to a system tuned for failures.
- **Tools you've never used.** You cannot observe your way to a capability that
  isn't in your history. Finding it needs an *external frontier scan*, not a
  session retro.
- **The wrong objective.** Optimizing autonomy or correctness silently ignores
  throughput, wall-clock, and token/dollar cost.
- **Measurement without consumption.** Telemetry you collect but never act on
  (e.g. a `tool_latency` query nothing reads) — the system's own #1 disease,
  generation-without-consumption, turned inward.

Net effect: order-of-magnitude wins (real example — impacted-test selection,
121s → ~2s, **30-77x**) sit undiscovered until a human happens to notice. This
skill is the **prospective, generative, frontier-scanning** counterpart to
`/observe`'s retrospective error-hunt.

**This is general.** Test-speed was one *instance*. The surface can be anything
high-traffic: data ingestion, research, deploy, debugging, a daily ritual, a
report you regenerate by hand. Point it at anything you suspect is silently
10-100x heavier than it needs to be.

## The process

### 1. Pick the surface + name the consumer
State the workflow precisely, and **who consumes its output: an agent or a human?**
This is not cosmetic — it changes what "better" means. (In the founding case, the
reframe "the consumer is an agent, not a human" deleted half the candidate tools:
reactive notebooks, TUI debuggers, and watch-mode runners are human ergonomics an
agent can't use.) Score every later option against the consumer's *actual*
constraint — agent feedback latency / parseable output / fewer turns, or human
wall-clock / clicks — not generic niceness.

### 2. Measure ambient COST, not errors
What does this surface cost in wall-clock, turns, repeated manual steps, or tokens
**even when it succeeds**? The blind spot is friction that passes. Pull existing
telemetry instead of guessing: `agentlogs query tool_latency`, session logs,
`/usr/bin/time -p`, git history of how often the ritual recurs. If you can't put a
number on the current cost, you can't recognize a 10x — quantify first.

### 3. State the floor (first principles)
What would this look like if it were 100x better? What's the theoretical minimum —
run the 5 tests touching the edit, not all 4,779? Naming the floor turns a vague
"could be faster" into a measurable gap.

### 4. Divergent frontier scan (external, NOT historical)
Fan out (multiple subagents, one per axis) over what *exists in the world* — the
newest tools, packages, and approaches — because your own history by construction
cannot contain a tool you've never tried. Rules:
- **Verify currency.** Training data is stale on fast-moving tooling; confirm
  latest version + release date via web search / context7. Don't assert from memory.
- **Gate on maintenance, not effort.** Dev cost ≈ 0 with agents; the real cost is
  ongoing drag. Score Value | Maintenance | Prerequisites.
- **Reframe each candidate for the step-1 consumer** before crediting it.
- Default to *thoroughness* here — this is the divergent phase; converge later.
See `/brainstorm`, `/research`, `/deep-research` for the fan-out machinery.

### 5. Adversarial cross-model review
Run `/critique model` on the *proposal* (not an open question). Cross-model pressure
catches tool-choice naivety ("X is a drop-in" when it floods 1600 warnings),
over-engineering, and benefits asserted-but-unproven. Bucket convergent /
single-source / divergent; you have context the reviewers don't — reconcile, don't
adopt wholesale.

### 6. Pilot + MEASURE — eat the dogfood
Build the smallest real version and **measure it against the floor**. This step is
non-negotiable: measurement routinely *corrects the plan*. In the founding case it
overturned three claims — parallel linting was 1.4x not 8x (import-bound, not
parallelizable); the named "fix" for the slow outlier did nothing (cost was imports,
not `uv run`); a "drop-in" type checker flooded 1600 warnings. **Report honest
factors** — a measured 1.4x and a measured 30x are both more valuable than an
asserted 100x.

### 7. Consumption-gate + ratchet
Build only what has a *named consumer* (skip the rest **with reasons**, so they
aren't re-proposed). Then **ratchet or architect** the win so it sticks and the
system can't silently regress to the old way (a recipe, a default, a gate, a
baseline that can only shrink). A win nobody runs is generation-without-consumption
again.

## Anti-patterns this counters
- **Error-driven blindness** — only learning from corrections ⇒ friction-that-passes
  stays invisible.
- **History-bound blindness** — you can't retro your way to an unused tool.
- **Measurement without consumption** — collecting `tool_latency` etc. and never
  acting on it.
- **Plan-without-pilot** — quoting a speedup you never measured.
- **Cargo-culting the case** — this is a *general* process; the original surface
  (tests) was incidental.

## Composes with
`/observe` (its retrospective, error-oriented twin), `/brainstorm` + `/research` +
`/deep-research` (step 4 fan-out), `/critique model` (step 5), `/verify-before`
(step 2 probe / step 6 preregister), `/sweep` + `/upgrade` (drift and bug audits —
different axes).

## Output
A memo (`research/…` or the project's convention) recording the floor, the scan
(adopt/trial/skip gated on maintenance), the measured pilot results, and the
ratchet/architecture that locks the win. A worked end-to-end example:
`agent-infra/research/agent-dev-loop-tooling-2026-06.md` and
`agent-infra/decisions/2026-06-08-failure-envelope-convention.md`. Not a doc-only
deliverable — the artifact is the shipped+measured change.

## The automated complement (note, not part of the manual run)
This skill is the human/agent-invoked version. Its step-2 blind spot ("friction that
passes") wants an *automated feeder*: a loop that reads the cost telemetry the system
already collects (`agentlogs tool_latency`, aggregate wall-clock by command across
sessions) and surfaces the top time-sinks as leverage candidates in `/observe`. That
gives the orphaned telemetry a consumer and auto-nominates surfaces for this skill —
the structural fix for "why did a human have to notice."
