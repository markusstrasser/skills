---
name: diagnose
description: "Use when: diagnosing ONE bug or perf regression — \"diagnose\", \"debug this\", \"why is X broken/failing/slow\". Build the feedback loop FIRST. NOT repo-wide bug hunt (/debug) or plan critique (/critique)."
user-invocable: true
argument-hint: "[the bug / regression to diagnose]"
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
effort: high
---

# Diagnose

A discipline for ONE hard bug, single-agent. The spine: **a tight feedback loop that goes `red` on
this bug is the whole game** — bisection, hypothesis-testing, instrumentation all just consume it.
Without one, no amount of staring at code finds the cause. Skip a phase only with explicit reason.

> Boundary: this is *single-bug diagnosis*. For adversarial fan-out across a repo (parallel scouts,
> audit handoff) use `/debug`. For "did this change regress something" use `/code-review` on the diff.

## Phase 1 — Build the feedback loop  ← Procedural (THIS IS THE SKILL)

Everything else is mechanical. Spend disproportionate effort here. **Be aggressive; refuse to give up.**
Construct a loop — try in roughly this order, stop at the first that reaches the bug:

1. **Failing test** at whatever seam reaches it (unit / integration / e2e).
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** on a fixture, diffing stdout vs a known-good snapshot.
4. **Headless-browser script** (Playwright) asserting DOM/console/network.
5. **Replay a captured trace** — save a real request/payload/event to disk, replay it through the path.
6. **Throwaway harness** — minimal subset (one service, mocked deps) exercising the bug in one call.
7. **Property / fuzz loop** — for "sometimes wrong", run 1000 random inputs.
8. **Bisection harness** — appeared between two known states → automate so `git bisect run` drives it.
9. **Differential loop** — same input through old-vs-new (or two configs), diff outputs.
10. **HITL bash** (last resort) — if a human must click, drive *them* with a structured script so the
    captured output still feeds back.

**Tighten** the loop like a product: faster (cache setup, narrow scope), sharper (assert the exact
symptom, not "didn't crash"), more deterministic (pin time, seed RNG, isolate fs/network). A 2-second
deterministic loop is a superpower; a 30-second flaky one is barely a loop. Non-deterministic bug → don't
chase a clean repro, raise the **reproduction rate** (loop 100×, parallelise, inject sleeps) until it's
debuggable.

### Completion gate ← Criteria (no `red`-capable loop → no Phase 2)
Done only when you can name **one command you have ALREADY run at least once** (paste the invocation +
its output) that is: **red-capable** (drives the real bug path, asserts the user's *exact* symptom — not
"runs without erroring"), **deterministic**, **fast** (seconds), **agent-runnable** unattended.
**If you're reading code to form a theory before this command exists — STOP. Jumping to a hypothesis
without a loop is the exact failure this skill prevents.** If you genuinely cannot build one, say so
explicitly, list what you tried, and ask for the environment / a captured artifact (HAR, log, core dump)
— do not proceed to hypothesise.

## Phase 2 — Reproduce + minimise  ← Procedural
Run the loop; watch it go `red`. Confirm it's the **user's** failure (not a nearby one — wrong bug =
wrong fix) and reproducible. Then shrink to the **smallest scenario that still goes red**: cut inputs /
callers / config / data one at a time, re-running after each. Done when every remaining element is
load-bearing (removing any one makes it green). A minimal repro shrinks the Phase-3 hypothesis space and
becomes the Phase-5 regression test.

## Phase 3 — Hypothesise  ← Criteria
Generate **3–5 ranked, falsifiable hypotheses BEFORE testing any** (single-hypothesis anchors on the
first plausible idea). Each states its prediction: "if X is the cause, changing Y kills the bug / Z
worsens it." No prediction = it's a vibe; sharpen or discard. **Show the ranked list to the user before
testing** — they re-rank instantly ("we just shipped #3") — but don't block; proceed on your ranking if
they're AFK.

## Phase 4 — Instrument  ← Procedural
Each probe maps to one Phase-3 prediction; **change one variable at a time**. Prefer debugger/REPL (one
breakpoint > ten logs) → targeted boundary logs → never "log everything and grep". **Tag every debug log**
with a unique prefix (`[DBG-a4f2]`) so cleanup is one grep. **Perf branch:** for regressions, logs lie —
establish a baseline measurement (timing harness, profiler, query plan), then bisect. Measure first.

## Phase 5 — Fix + regression test  ← Procedural + Guardrail
Write the regression test **before the fix** — *but only if a correct seam exists* (one where the test
exercises the real bug pattern at the call site). **If the only seam is too shallow to catch this bug,
that absence IS the finding** — note it, don't fake a shallow test for false confidence; the architecture
is preventing lock-down. With a correct seam: turn the minimised repro into a failing test → watch it
fail → apply fix → watch it pass → re-run the Phase-1 loop on the *original* (un-minimised) scenario.

## Phase 6 — Cleanup + post-mortem  ← Guardrail
Before declaring done: original repro no longer reproduces · regression test passes (or absent-seam
documented) · all `[DBG-…]` logs removed (grep the prefix) · throwaways deleted · the **correct**
hypothesis stated in the commit message (the next debugger learns). Then ask **"what would have prevented
this?"** — if the answer is architectural (no seam, tangled callers, hidden coupling), hand off to
`/improve` with specifics. Make that call *after* the fix, when you know the most.

---
_Single-agent diagnosis folded from mattpocock/diagnosing-bugs into our idiom; the fan-out sibling is
`/debug`. Leading words (`red`, `tight`) per skill-authoring. See
`agent-infra/research/2026-06-19-mattpocock-skills-best-ideas.md`._
