# Observe: lever

Use this workflow for an explicit improvement search on a known surface; ordinary fixes do not require a frontier scan. [Analysis safeguards](analysis-safeguards.md) apply when evaluating or implementing candidates.

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
