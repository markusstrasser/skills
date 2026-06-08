---
name: leverage
description: "Hunt order-of-magnitude (10-100x) wins your reactive loops can't see — improvement along axes nothing measures (faster / better / more / simpler / unnecessary), found by scanning the external frontier not your history, then piloted + measured. 'how could this be 10x', 'biggest lever here', 'what are we doing the dumb way', 'frontier audit', 'why do we even do it like this'. The generative twin of /observe."
user-invocable: true
argument-hint: <workflow or surface to 10x> [--repo path]
context: fork
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: high
---

# Leverage — find the order-of-magnitude wins your reactive loops can't see

## The blind spot it fixes

Self-improvement machinery — `/observe`, session-analyst, the error-correction git
log, "recurring pattern → architecture" — is **reactive, history-bound, and frame-
fixed**. It learns from errors and corrections, against the objective it already
tracks, using its own past. That makes it blind to a whole class of improvement:

- **Anything that never fails.** Work that succeeds but is silently far short of
  what's possible produces no error, no correction, nothing to learn from.
- **Any axis nothing measures.** If there's no objective for it, optimizing
  autonomy/correctness sails right past it.
- **Anything not in your history.** You cannot retro your way to a tool, model, or
  paradigm you've never tried — that needs an *external* scan.
- **Anything requiring a frame-shift.** "This task shouldn't exist" / "a different
  actor should own it" can't come from optimizing *within* the task.

`/leverage` is the **prospective, generative, frontier-scanning** counterpart to
`/observe`'s retrospective error-hunt. Point it at any high-traffic surface —
testing, ingestion, research, deploy, debugging, a daily ritual, a report you
regenerate by hand — that you suspect is an order of magnitude short of its best.

## Cost is only one axis — discover the axis, don't assume it

The defining mistake (made *twice* in this skill's founding session: "testing" got
collapsed to "speed," then "the category" got collapsed to "cost") is to fixate on
one dimension. Improvement lives on at least five, and `/brainstorm` exists to
surface which are live here — via constraint inversion: *what if this were free?
instant? perfect? didn't exist? done by someone else?*

| Axis | "could be 10x ___" | how you'd measure it |
|------|--------------------|----------------------|
| **Faster** | cheaper / lower-latency / fewer turns | wall-clock, turns, tokens, $ (e.g. test loop 121s→2s) |
| **Better** | higher-quality / more-accurate output | an eval / judge / ground-truth score |
| **More** | a capability you don't have *at all* | does it exist? coverage % |
| **Simpler** | less complexity / maintenance / surface | components, LOC, # moving parts |
| **Unnecessary** | the task shouldn't exist; different actor/mechanism | does the need disappear? |

Don't pick the axis from intuition — generate the candidates, then choose where the
gap is largest.

## How it works (orchestration — it composes skills you already have)

`/leverage` is not a new engine. It is the end-to-end loop that wires the divergent
and verification skills together into a *measured, shipped* win:

1. **Frame + name the consumer.** State the surface precisely and *who consumes its
   output — agent or human?* This changes what "better" means and is not cosmetic
   (in the founding case "the consumer is an agent" deleted half the candidates:
   notebooks, TUI debuggers, watch-mode are human-only). Score everything later
   against the consumer's real constraint.
2. **Discover the axes — `/brainstorm`.** Constraint inversion / denial cascade over
   the five axes above. Output: which dimension(s) have the biggest gap here, not a
   premature "make it faster."
3. **Measure the current state on the chosen axis.** Quantify *before* you can
   recognize a 10x. Faster → `agentlogs query tool_latency`, `/usr/bin/time`. Better
   → run the eval. More → "we don't do this at all." Simpler → count the moving
   parts. If you can't put a number (or a clear binary) on today, you can't measure
   the win.
4. **State the floor/ceiling (first principles).** What does this look like at 100x
   on this axis? (Run 5 impacted tests, not 4,779. Or: a 95% eval, not 70%.)
5. **Frontier scan — subagent fan-out + `/research` / `/deep-research`.** Search what
   *exists in the world* on this axis (history can't contain an unused capability).
   Verify currency (training data is stale on fast-moving tooling). Gate on
   **maintenance, not effort**. Reframe each candidate for the step-1 consumer.
6. **Adversarial review — `/critique model`.** On the *proposal*. Catches tool-choice
   naivety ("X is a drop-in" when it floods 1,600 warnings), over-engineering, and
   benefits asserted-but-unproven.
7. **Pilot + MEASURE — `/verify-before`.** Smallest real version, measured against
   the floor. Non-negotiable: measurement routinely *corrects the plan* (the founding
   session overturned three claims — parallel linting was 1.4x not 8x; the named
   "fix" for the slow outlier did nothing; a "drop-in" checker flooded warnings).
   Report honest factors — a measured 1.4x and a measured 30x both beat an asserted
   100x.
8. **Consumption-gate + ratchet.** Ship only what has a *named consumer* (skip the
   rest with reasons). Then ratchet/architect the win so the system can't silently
   regress (a recipe, a default, a gate, a baseline that can only improve).

`/brainstorm` alone gives ideas; `/leverage` adds *measure → external-scan → pilot →
ratchet* — the rigor that turns an idea into a verified order-of-magnitude change.

## Anti-patterns this counters

- **Collapsing the general to one axis.** The instinct is to grab the first axis
  (usually "faster") and run. Force step 2 — the biggest gap is often *better*,
  *more*, or *unnecessary*, not *faster*.
- **Error-driven blindness.** Only learning from corrections ⇒ success-that-is-far-
  short-of-possible stays invisible.
- **History-bound blindness.** You can't retro your way to an unused tool/model/idea.
- **Measurement without consumption.** Collecting telemetry (`tool_latency`, evals)
  and never acting on it — the consumption-over-autonomy disease, turned inward.
- **Plan-without-pilot.** Quoting an improvement you never measured.

## Composes with

`/observe` (retrospective, error-oriented twin), `/brainstorm` (step 2 axis discovery
+ step 5 option generation), `/research` + `/deep-research` (step 5 frontier scan),
`/critique model` (step 6), `/verify-before` (step 3 probe / step 7 preregister),
`/sweep` + `/upgrade` (drift and bug audits — different axes again).

## Output

A memo recording: the axes brainstormed and the one chosen, the measured current
state + floor, the frontier scan (adopt/trial/skip, maintenance-gated), the measured
pilot, and the ratchet that locks the win. Worked example end-to-end:
`agent-infra/research/agent-dev-loop-tooling-2026-06.md` +
`agent-infra/decisions/2026-06-08-failure-envelope-convention.md`. The deliverable is
the shipped + measured change, not the memo.

## The automated complement (note, not part of a manual run)

The manual skill is half the fix. Its blind spot — "success that never fails" — wants
an *automated feeder* per axis: read the signals the system already collects
(`agentlogs tool_latency` for *faster*, eval scores for *better*, coverage gaps for
*more*) and auto-nominate the worst offenders into `/observe` as leverage candidates.
That gives orphaned telemetry a consumer and is the structural answer to "why did a
human have to notice."
