---
name: decide
description: "Architecture/strategy decision arc — diverge → principle → code → cross-model critique → capture. Use for hard-to-reverse decisions (schema, breaking refactor, tech choice). Composes /brainstorm + /critique. NOT trivial (/critique) or ideation (/brainstorm)."
argument-hint: "[--quick] the consequential decision to make"
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

# Decision Arc

You are orchestrating a consequential architecture/design/strategy decision to a durable, hardened
conclusion. The deliverable is not an answer — it's a **decision that survived adversarial pressure
without reversal, captured so it can't be lost or re-litigated.**

This skill exists because `/brainstorm` is only the diverge step and `/critique` is only one
convergent step. The value here is the **glue between them** — the discipline that stops a decision
from sycophantically drifting. agent-infra's `agent-failure-modes.md` repeatedly names this surface
as the missing *"decision-point gate."* This is it.

## When to use (scope gate — read FIRST)

ALL must hold (same bar as the plan-review-gate):
- Consequential and **hard to reverse** (>1 session to undo if wrong).
- New system / schema / breaking refactor / new dependency or pattern / strategic direction.
- Multiple genuinely-different approaches exist.

**Do NOT use for:** trivial or single-correct-answer choices (just decide + mention it) · a single
diff/plan review (use `/critique`) · pure ideation with no decision to commit (use `/brainstorm`) ·
bug fixes / routine implementation.

If the scope gate fails, say so and stop. Over-applying this is its own failure mode (toxic
proactivity, FM14).

## The arc (six phases — each phase's OUTPUT gates the next)

### Phase 0 — Frame & find the axis
Do NOT jump to a plan or an answer. First:
- **List the hidden assumptions explicitly** (Contract 3). What is being taken for granted?
- **Find the real decision axis.** The first framing is usually wrong. (Canonical example: the real
  axis was "verify vs synthesize," not "personal vs general.") State it in one sentence.
- Engage the user as the authority on their own constraints; ground in prior work, prior decisions
  (`git log`, ADRs, `docs/decisions/`, vetoed-decisions). **Inventory before dispatch** — has this
  been decided/built already?

Output: the framing, the axis, the assumption list. Get a read from the user before diverging.

### Phase 1 — Diverge → `/brainstorm`
Generate 5+ genuinely-different *mechanisms* (not variations) before converging. First idea = the
hivemind attractor (Pre-Build #7). Invoke `/brainstorm` on the framed axis. Output: ranked directions.

### Phase 2 — Settle the principle BEFORE the plan
This ordering is load-bearing. Write the **ADR (the *why* / the governing thesis) first**, then the
plan. Pinning the principle first is what stops the plan from drifting under later pressure.
- ADR → `docs/decisions/NNNN-<slug>.md` (template in `references/templates.md`).
- Record the rejected alternatives in the ADR so they're not re-proposed.

Output: the ADR + the invariants the decision must preserve.

### Phase 3 — Ground & plan
- **Read the code before planning** (read-before-plan). Plans written from memory diverge within days.
- **Probe every join/fact the plan asserts** (probe-the-join): inline the literal `git grep`/SQL that
  proves the join site or fact exists. Plan-writers invent joins that look right but don't exist.
- **Probe storage/identity/hash contracts at the WRITE site** (probe-the-write — extends probe-the-join
  beyond relational joins): when the decision rests on "store X holds field Y" or "identity/hash Z is
  computed as…", read where the value is *stamped* (the writer), NOT where it's read. Consumer-side
  reasoning silently substitutes an *assumed* contract for the real one — silent-proxy-as-truth at the
  schema layer — and produces confidently-wrong specs that survive to Phase 4 unchallenged. Assert the
  load-bearing invariant empirically: a one-line assertion in the probe/generator falsifies a bad
  premise in seconds. (Canonical miss: a spec compared two hash functions assumed equal — different
  widths, one never written for half the entities; caught only by reading the writer, after the arc
  had already produced an ADR on it.)
- **Every BLOCKER gets its OWN falsification probe — the highest-leverage claims deserve MORE probing, not
  less.** A "precondition / must-close-before / gates-the-rest" claim is where a wrong premise does the most
  damage (it reorders the whole plan), yet it is the easiest to assert by analogy from a nearby true fact.
  For each blocker, write the literal command that would prove it FALSE and run it — separate from the facts
  it is derived from. **Probe the WRITER/BUILDER of the artifact the decision rests on, not just its readers:**
  "X reads the monolith" (true of the current instance) does NOT establish "the product reads the monolith"
  (false when the product artifact is built by a different pipeline). Reader-probes prove the wrong thing.
  (Canonical miss 2026-06-16: plan blocker "the 566-claim subject_scope leak gates the release" survived the
  whole arc and was falsified by one grep at execute time — `build_claims_public.py:4` never reads the
  monolith, so the leak cannot reach the product base; the blocker had probed the monolith readers, never the
  base builder, and named the wrong gate — `subject_scope` instead of the real `safe_to_share`/clean-room
  boundary that already contained it.)
- Write the plan with probes embedded → `.claude/plans/<session>-<slug>.md`.

Output: a plan grounded in *verified* facts, not assumptions.

### Phase 4 — Escalating adversarial, closed-loop → `/critique model`
Rounds: **standard → deep (`--axes deep`) → confidence pass.** Cross-model (Gemini + GPT), never
same-model (FM11 peer-review theater).

**For codebase-coupled decisions, ALSO run REPO-GROUNDED agents — not only cold API models.** A cold
reviewer (Gemini/GPT over a pasted spec) produces good *generic* failure modes but cannot tell which
are *already handled by existing code*. Run cursor agents with real repo read access:
`cursor-agent -p --mode ask --trust --model composer-2.5 "verify the design against the
ACTUAL code, cite file:line — which findings are already-handled vs genuinely-open"`. They routinely
**overturn the cold round's "must-build" list** (lived 2026-06-16: a cold round flagged the release
boundary + overlay model + retraction as "build these"; repo-grounded review showed all three already
built but *dark/unwired* — changing the decision from greenfield to convergence). **Cursor transport
uses the CURSOR model (`composer-2.5`) — NEVER route opus/gpt/sonnet through cursor-agent** (#g
2026-06-18: off-policy + separately metered; hook-enforced by `pretool-cursor-model-guard.py`; the
cursor-agent skill is the single owner — load it, don't re-state a model). The repo-grounding comes
from cursor's LIVE REPO ACCESS, not the model. For any NON-cursor arch critique (cold cross-lab via
llmx), use a FRONTIER tier (opus / gpt-high), never a weak model — a sonnet repo-critique once built
a "HALT, reverse the spine" conclusion on a search-error false premise.

**Scale to a PANEL of 3–6 repo-grounded cursor agents for a codebase-coupled arch decision** (operator
directive 2026-06-16, "whatever it takes for good design") — all repo-grounded cursor agents run
`composer-2.5` (cursor's model; #g 2026-06-18). Model diversity is NOT obtained by swapping cursor's
model — it comes from a SEPARATE cold cross-lab pass (llmx gemini/gpt) scoped to generic,
non-repo-specific design critique. The cursor panel is ROLE-diverse: **≥1 dedicated FACT-CHECKER** tasked to resolve EVERY `file:line` / count / zero-consumer
claim in the plan → PRESENT / ABSENT / MISMATCH, plus arch/spine critics and **≥1 innovation /
alternative-mechanism explorer**. `/critique model` already runs a cursor premise-scout by default
(`model-review.py`, line ~17 — "the only axis that can falsify a plan's premises; packet-only reviewers
went 0-for-5"); this scales it up and makes the fact-check role explicit. **Why the dedicated fact-checker
(the ADR-0029 lesson):** 5 ground-truth errors survived 4 critique rounds *including* two repo-grounded
ones — because the cursor critics were aimed at ARCHITECTURE (and nailed the spine) but were never tasked
with exhaustive fact-verification; a reviewer anchors on a plausible asserted `file:line` and reasons
about the design around it instead of grepping whether it resolves. The fact-check role + a deterministic
resolver gate (re-run every pinned probe, diff vs claimed) is the cure — not more architecture critique.
(`feedback_repo_grounded_critique`, `feedback_opus_not_sonnet_for_arch`, `feedback_critique_panel_include_composer`.)

After EACH round, the two non-negotiable checkpoints:

1. **Verify-before-fold.** Grep every model claim against the actual code before folding. Model
   line-numbers and symbol names lie; the critique verifier inflates "hallucinated." Trust convergence
   + code-verification, never the confidence field. (FM15 silent-semantic; FM5 error-amplification —
   you are the orchestrator-mediated verification step.)
2. **Disagree-self-check.** Per finding: HOLD or FLIP — and if FLIP, **name the new fact that drives
   it.** "The model said it with conviction" is not a fact. Sycophantic flips dressed as reasoning are
   the failure this catches (FM7). Run the checklist in `references/disagree-self-check.md`.

Fold verified findings; record what you HELD against and why. Closed-loop iteration neutralizes >40%
of faults that linear workflows miss (FM15). See `references/critique-loop.md`.

### Phase 5 — Completeness & capture
- **Mechanically verify** every decision/input landed in a durable doc (Post-Synthesis Completeness
  Check). Don't assert completeness — check it. (This is where orphaned memos and untriaged options
  hide.) Checklist in `references/completeness-and-capture.md`.
- Emit the **artifact contract** (below).

## Success criterion (state this loudly — it's the most-gotten-wrong part)

Success is **zero architecture reversals across the escalating rounds** — NOT a toothless final
critique. A critique that finds *nothing* means you over-specified into implementation. The signal of
a sound decision is that each round only resolves one level *deeper* (WHATs → HOWs), never overturns
the spine.

**Stop condition:** when rounds stop producing reversals and only produce implementation-HOWs, the
decision is closed. Those HOWs become the first build tasks — hand off, don't keep critiquing.

## Discipline checkpoints (the glue — this is what makes it more than two skills)

| Contract | Guards against (agent-infra FM) |
|---|---|
| List assumptions before analysis | Contract 3 (hidden-assumption) |
| Principle before plan | reasoning drift downstream (FM15) |
| Probe-before-assert; read-before-plan; probe-the-write (storage/identity at the writer) | phantom joins / stale plans / silent-proxy schema assumptions |
| Cross-model, not same-model peer | FM11 peer-review theater |
| Orchestrator-mediated verify-before-fold | FM5 amplification, FM15 silent-semantic |
| Disagree-self-check (name the new fact) | FM7 post-hoc rationalization, sycophantic flips |
| Completeness-before-done; deferred tracker | dropped decisions, re-litigation |
| Reversal-count, not finding-count, is the metric | over-specification mistaken for rigor |

## Artifact contract (the durable output — nothing lost, nothing re-litigable)

- **ADR** → `docs/decisions/NNNN-<slug>.md` — the principle, the why, the rejected alternatives.
- **Plan** → `.claude/plans/<session>-<slug>.md` — the what/sequence, with inline probes + per-phase
  end-states + a named first vertical slice.
- **Deferred/open/rejected tracker** → `docs/decisions/deferred-and-open.md` (or per-project) — every
  decision + open fork + deferred item + rejected option + the critique audit trail. So nothing is
  lost and nothing is re-proposed.
- **Vocabulary glossary** — one canonical term per concept, once the semantics are clear.

Templates for all four: `references/templates.md`.

## `--quick`
For a consequential-but-smaller decision: Phase 0 → 1 (inline, skip the full /brainstorm fan-out) →
2 (lightweight ADR) → 4 (one standard `/critique` round) → 5. Keep the disagree-self-check and the
completeness check — those are never optional.

## Honest limitation
This skill encodes one operator's process (n=1 origin). After 2-3 real uses, run `/observe` or
session-analyst over its transcripts and tune the checklists against what actually recurs — not what
the author guessed would.
