---
name: execute
description: Execute an approved plan to done WITH hygiene — phase-gated, probe-before-build, verify-before-claim, granular commits, worktree-isolated parallel subagents, and INLINE tooling-building (build the missing tool/hook DURING execution, not at session-end). Runs the disagree-self-check on divergence and /critique close at the end. Use after /decide or on any approved plan file. NOT for exploration/decisions (use /decide) or one-off edits.
argument-hint: "[--slice P0-P2] [--from PHASE] <plan path>"
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
  - Skill
---

# Execute (with hygiene)

You are executing an approved plan to a verified-done state. The deliverable is **working,
committed, verified code that matches the plan's per-phase end-states** — not a report that says it's
done. This is the convergent implementation twin of `/decide`; the pipeline is
`/decide → /execute → /observe`.

The point of this skill over an ad-hoc "execute the plan, use subagents, /critique at the end" prompt
is the **hygiene that otherwise burns sessions**: phase gates, probe-before-build, verify-before-claim,
commit discipline, subagent isolation, and — the centerpiece — **building tooling inline while you
fix, not in a session-end retro.**

## When to use / NOT
- USE: a plan exists and is approved (from `/decide`, `.claude/plans/`, or the user). The work is
  implementation, not deciding what to do.
- NOT: the approach isn't settled (use `/decide`) · a single obvious edit (just do it) · pure research
  (`/research`).

## 0. Resolve the plan (this is what makes the handoff one line)
Read the plan file AND its linked context (ADR / architecture doc / deferred-and-open tracker). Extract:
- the **first vertical slice** (or honor `--slice` / `--from`); default to the plan's named first slice.
- the **hard-gates + per-phase end-states** (a phase that says "gated on P2 live" does NOT start early).
- the **invariants / non-negotiables** the plan + project constitution declare.
- the **probes** the plan already wrote (its `read-before-plan` / `probe-the-join` commands).
Confirm the slice + first phase with the user only if anything is ambiguous; otherwise begin.

## The execution loop (per phase — do NOT telescope phases)

For each phase in the slice, in order:

1. **Probe-before-build.** Re-run the plan's probes for THIS phase. The codebase may have shifted since
   the plan was written; verify the assumptions (joins exist, deps present, schema shape) before building
   consumers against them. If a probe fails, that's a divergence → step 5.
2. **Build.** Independent work → parallel subagents, **`isolation: "worktree"`** for anything that touches
   files (hard isolation beats soft; soft hurts on open-ended tasks). Each code subagent returns a
   **manifest of files-touched + files-skipped-with-reason**; diff it against intent before accepting.
   Any subagent prompt that names an output file must instruct: "FIRST tool call = Write a PROBE-IN-PROGRESS
   stub at that path" — the dispatch gate blocks file-output prompts without it (one wasted retry each time).
   **Executor tier** — set by VERIFIER QUALITY in the brief, not by how hard the task feels
   (`model-guide` → Dispatch Economics is canonical; measured, anim-workbench evals 2026-06-12):
   - **search / read fan-out** → Explore agent (output is consumed, not shipped — no executor risk)
   - **mechanical, no gate to game** (rename sweeps, boilerplate) → sonnet/haiku tier
   - **full brief + mechanical gates** (tests/typecheck/deterministic verify), greenfield OR port/re-author
     against an existing oracle → Opus effort-low (headless `claude -p --model opus --effort low`) or the
     codex $0 lane (`codex exec --full-auto -C <out-of-repo-worktree> -c model_reasoning_effort="low"` —
     pre-install deps, commit from outside the worktree; see model-guide for the gotcha list)
   - **judgment-loaded gated work** (declared design holes, oracle-gotcha mapping, adjudicated-fact
     dependencies) → Fable effort-low (headless `claude -p --model claude-fable-5 --effort low`,
     key-stripped) — licensed at 0.90× opus-low tokens; found unique design gaps opus missed
   - **ungated design REVIEW** (verdict on EXISTING structure: cosign/critique an architecture, audit a
     schema, grade a memo) → Fable effort-low — measured ≈ effort-high on critique quality (4/4 cosigns,
     0 false anchors, 2 novel proposals) at **0.34× tokens** (anim-workbench effort-architecture eval,
     n=1 screening). The savings buy a SECOND diverse reviewer, which beats one deep one (lanes
     measurably find different findings).
   - **ungated design SYNTHESIS** (novel structure, open design hole, no oracle) → frontier model,
     effort HIGH — the FIRST measured effort-quality separation (low missed the orthogonal factoring
     high shipped; folded the dimensions and lost a composition the design existed for)
   - **partial/noisy verifier or spec-judgment gaps** → don't downgrade; frontier model, normal effort
   Standing revocation trigger: first cheap-lane gate failure on a task classified fully-briefed →
   fall back to default effort for that class + record it.
   Note the measured trap: a cheaper executor (Sonnet) *reward-hacked the gate* under pressure, so "cheap +
   weak gate" is the worst quadrant — and "Opus is token-efficient so cheaper" was REJECTED (~2.4× the
   premium buys spec fidelity, not efficiency). A downgraded executor's brief MUST carry exact verification
   commands + cleanup directives — low effort skips only *self-initiated* checking, so the brief does the
   initiating. The Agent tool exposes only `model:`; per-dispatch effort needs headless `claude -p --effort`.
3. **Verify-before-claim.** Run it. The phase's **end-state must observably hold** — run the test, the
   query, the command. Tests fail → say so with the output; a step was skipped → say that. No success
   theater: "done" means verified, not "should work."
4. **Commit.** Granular semantic commits, one logical change each. **Never `git add -A`/`.`** — stage
   specific paths. Foreground commits only (a hook-blocked commit returns exit 0 from a backgrounded call).
5. **Gate.** Do not advance to the next phase until this phase's end-state holds and is committed.

## Interleaved improvement (the centerpiece — build tooling DURING, not after)

When you hit **repeated friction** (the same manual step 3+ times), a **missing guard** (a bug class the
plan didn't anticipate), or a **missing self-documenting artifact**, do NOT log it for a session-end retro.
**Spin a subagent (worktree-isolated) to build the tool / hook / recipe NOW**, land it, then continue the
phase. Recursive self-improvement belongs *in* the loop. Examples that qualify: a probe you keep re-typing
→ a `just` recipe; a bug class you keep hitting → a warn-only hook; a DB you keep re-inspecting → a catalog.
Keep it scoped and strictly-better — no speculative abstractions (that's the over-engineering trap).

## Mid-execution divergence (the plan can be wrong on the ground)
If execution reveals the plan contradicts reality (a file/assumption is gone, an approach doesn't work, the
epistemology/teleology looks off with more context), run the **disagree-self-check**
(`../decide/references/checklists.md`): is the plan wrong, or am I? Name the new fact. Then **adapt and
state what changed**, or flag it to the user if it's a spine-level reversal — don't blindly follow a plan
that contradicts what you see, and don't silently abandon it either. Research / cross-check
(`/research`, `/llmx-guide` for long-context GPT/Gemini calls) when the divergence is a knowledge gap.

## Done
1. **Completeness check** (`../decide/references/checklists.md`): every phase in the slice landed AND its
   end-state was verified AND committed. Mechanically verify; don't assert.
2. **`/critique close`** on the slice's commits — the post-impl review that catches new-code bugs the
   canary misses.
3. Report: what shipped (verified), what diverged (and why), what tooling you built inline, what's next
   (the next slice / deferred items).

## Honest limitation
Origin n=1 (this skill's authoring session). After 2-3 real runs, `/observe` the transcripts and tune —
especially the "repeated-friction → build-a-tool" threshold, which is the part most likely mis-calibrated.
