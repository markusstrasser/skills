---
name: extract-generators
description: Mint new idea-generators from miss patterns — when valuable findings repeatedly arrive from OUTSIDE your existing frames/checklists/generators, extract the generator that would have produced them, retrodiction-test it, and install it one level up (charter, menu, checklist). Use when a session's wins came from luck/outside prompts rather than the standing process, when a frame menu cycles without yield while out-of-band finds accumulate, or on explicit "extract more generators".
---

# Extract Generators

Turn "we keep finding gold off-trail" into a new trail. A generator is anything that
mechanically produces candidate ideas: a frame menu entry (heretic G1–G6), a checklist
question, a brainstorm perturbation, an audit lens. This skill extracts NEW generators from
the pattern of findings your existing generators MISSED.

## When to fire

- A retro shows the period's biggest wins came from outside the standing generators (user
  questions, accidental file reads, cross-model asides) — that's a miss-pattern, not luck.
- A generator menu has cycled with thin yield while out-of-band findings accumulated.
- The user says "extract more generators" / "the checklists aren't enough."

## Procedure

1. **Collect the out-of-band finds** (the last N days' adopted findings that no standing
   generator produced). For each, write one line: what was found + what question WOULD have
   produced it.
2. **Cluster the questions.** Each cluster is a candidate generator. Name the abstract move,
   not the instance ("audit a layer treated as vendor-fixed", not "read fx2's makefile").
3. **Retrodiction-test** each candidate: would it have produced ≥2 of the collected finds
   BEFORE they happened, mechanically, from inputs available then? If not, it's a story about
   the finds, not a generator. Write the retrodiction into the generator's text (it doubles
   as the usage example).
4. **Check the dual:** for every generator about content, ask if a meta-generator about the
   PROCESS exists (the loop/harness/checklist itself is a config — e.g. "harness heresy").
5. **Install one level up, with ownership.** Generators live in owner-controlled standing
   files (charter menus, CLAUDE.md checklists, skill steps) — propose to the owner if that
   isn't you; standing instructions are owned one level up from their executor.
6. **Add the coverage substrate when the domain allows:** generators SAMPLE; an enumeration
   artifact (component × constraint map with explicit UNKNOWN cells, e.g. a LEVERS.md) makes
   coverage trackable — each generator firing cites the cell it sampled. Generators without a
   map drift back to vibes.
7. **Retirement rule:** a generator that cycles twice with zero adopted output gets demoted
   to an appendix; menus accrete cruft exactly as fast as codebases.

## Worked example (hutter, 2026-06-10/11)

Out-of-band finds in one day: time-budget-binds (user-adjacent question), fast-math 1.8×
(makefile read), the in-tree int16 mixer (research scan), dark-54% clock (audit of a profile
summary), 100 GB disk + source-zip submission clauses (rules re-read). None produced by the
standing G1–G4 frames. Extraction yielded two generators that retrodict 4+ of them:
**G5 stack-depth audit** ("pick ONE layer treated as vendor-fixed — allocator, number
representation, libm, build pipeline — and price a bespoke replacement against ALL budgets")
and **G6 representation audit** ("pick ONE data structure; what mathematical object is it
really, and does a representation with better algebraic properties exist — log-domain,
low-rank, lookup-vs-compute"). Installed in the heretic charter (owner-applied); coverage
substrate = LEVERS.md; first sweep of the map surfaced 8 virgin cells immediately.

## Anti-patterns

- Minting a generator per find (over-fitting; cluster first, retrodiction-test always).
- Installing generators in your own executor-level notes where they decay — they belong in
  the owner's standing file.
- Generators without a consumption path: every firing's output needs a triage/disposition
  channel, or you build a backlog machine (generation-without-consumption).
