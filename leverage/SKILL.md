---
name: leverage
description: "Hunt the wins your reactive loops can't see — three divergent-discovery modes. DEFAULT (10-100x leverage): order-of-magnitude wins along axes nothing measures (faster/better/more/simpler/unnecessary), frontier-scanned not history-bound, then piloted + measured. `missing` (negative-space sweep): what entire categories an optimized system never put on an axis — exclusion list + multi-perspective search + pertinent negatives. `generators`: mint new idea-generators from miss patterns when wins keep arriving off-trail. 'how could this be 10x', 'biggest lever here', 'what are we missing', 'blind spots', 'extract more generators', 'frontier audit', 'why do we even do it like this'. The generative twin of /observe."
user-invocable: true
argument-hint: <workflow or surface to 10x> [--repo path]
context: fork
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: high
---

# Leverage — find the order-of-magnitude wins your reactive loops can't see

## Modes

`/leverage` has one spine (find what reactive, history-bound, frame-fixed loops miss) and three
modes for three shapes of that miss. Pick by what you're hunting:

| Mode | Invoke | Hunts | Method |
|------|--------|-------|--------|
| **default** | `/leverage <surface>` | a 10-100x win on a KNOWN surface | this file: frame → axes → measure floor → frontier scan → critique → pilot → ratchet |
| **`missing`** | `/leverage missing <domain>` | entire categories an optimized system never put on an axis | [references/missing.md](references/missing.md): exclusion list + STORM perspectives + pertinent negatives |
| **`generators`** | `/leverage generators` | a better generator SET, when wins keep arriving off-trail | [references/generators.md](references/generators.md): collect miss-pattern → cluster → retrodiction-test → install one level up |

They compose: `generators` reads the misses that `default`/`missing` leave behind and grows the
generator menu both draw from; `missing` is the divergent front-end when the surface is so
mature that `default`'s step-2 axis brainstorm won't surface the unframed. The rest of this file
is the **default** mode.

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
2. **Discover the axes — calibrate divergence to the surface's maturity.** The
   load-bearing move is "don't assume the axis," not "always run the full apparatus."
   - **Novel / unmeasured surface** → hand off to `/brainstorm` (it owns the divergent
     technique; leverage owns only the target). Map its output onto the five axes.
   - **Mature / already-measured surface** → a lightweight pass over the five axes as
     a *checklist* is enough; the full perturbation matrix is disproportionate tax
     (validated dogfooding intel — the denial round "ban building a tool" earned its
     keep, the rest didn't). This is the Constitution's divergence-budget rule
     (uncertainty × irreversibility) applied to the hunt itself.
   Either way the output is the same: which dimension has the biggest gap — not a
   premature "make it faster." NB the axes overlap in practice (a win is often
   "unnecessary" + "better" + "faster" at once); they exist to *break the anchor*,
   not to classify cleanly — don't agonize over the label.
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
   100x. **Size the win at the SESSION level, not the per-run level:** a per-run
   factor (e.g. testmon 31-77x per full-suite run) is not the impact — multiply by
   `frequency × blocking-fraction × where-the-time-concentrates` from agentlogs. The
   testmon win shrank from "31-77x faster testing" to "collapse the 2.5% slow-run
   tail + correct auto-scope" once measured (99.3% blocking, but 77% of runs already
   <5s). Quoting the per-run number as a session number is the overclaim this step
   exists to catch. Worked example:
   `agent-infra/research/2026-06-08-honest-factor-testmon-case-study.md`.
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

## Dependencies (this is an orchestrator over primitives — a soft dependency)

`/leverage` does not reimplement ideation, research, review, or verification — it
sequences the primitives that already do those, and owns only what they don't (the
blind-spot frame, the five axes, measure-the-floor, pilot-correction, ratchet). The
dependency is **soft and agent-mediated**: these aren't function calls, they're
hand-offs the running agent performs by reading this file. Two rules keep that
healthy:

- **Reference by capability, not internals.** Step 2 needs "divergent axis
  generation," which `/brainstorm` provides; if brainstorm's techniques change,
  leverage still works. Don't re-teach a primitive's method inline — hand off to it.
- **Keep the orchestrator thin.** If a step is doing a primitive's job, delete it and
  hand off. If you're tempted to copy brainstorm's perturbations or critique's axes
  in here, that's drift — link, don't duplicate.

| Step | Primitive | What leverage adds on top |
|------|-----------|---------------------------|
| 2 discover axes / 5 options | `/brainstorm` | the five-axis taxonomy + "pick the biggest gap" |
| 5 frontier scan | `/research`, `/deep-research`, subagent fan-out | currency-verify + maintenance-gate + consumer-reframe |
| 6 review | `/critique model` | runs it on the *proposal*, buckets the findings |
| 3 / 7 measure | `/verify-before` | the floor, and "let measurement correct the plan" |
| — twin | `/observe` | the retrospective, error-oriented counterpart |

**Failure modes of the soft dependency:** *step-skipping* (agent free-associates
axes instead of handing off to brainstorm — the dep silently doesn't fire) and
*duplication drift* (the orchestrator re-states a primitive's method). Both are
caught by the two rules above. Do **not** merge leverage into brainstorm/observe:
each has standalone value (pure ideation; pure retro; the measured-win loop), and one
mega-skill-with-modes would bloat all three. (The `missing` and `generators` modes were
folded IN — 2026-06-13 — because they are *specialized divergent-discovery moves that already
orbited leverage* with no standalone pure-ideation/retro value, not separate primitives. The
boundary that holds: hand off to brainstorm/critique/research/verify-before; absorb the
discovery moves that only ever served the leverage hunt.)

(`/sweep` and `/upgrade` are adjacent but orthogonal — drift and bug audits, not
leverage's axes.)

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
