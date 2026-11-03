---
name: steer
description: "Use when: stuck, about to wrap up, or the operator asks what you haven't thought of. One thinking prompt or hole-poke from his usual moves (operator-deck): a divergent angle or an obvious miss, never process or agent orchestration. NOT a checklist to run through."
user-invocable: true
---

# Steer — a thinking prompt or a hole to poke

This is for what a sharp outsider would raise: a divergent angle on the question, or a hole
in the current result that nobody has checked. It is not for process (running agents,
parallelizing, reporting, tidying up); you do those anyway.

Ask what the operator would push on here: the weakest result, the obvious question nobody
asked, the construct or comparison that is off.

Misses inside the session (a number that changed since an earlier turn, a check that passes
for the wrong reason, a change with a side effect beyond its intent) mostly arrive already, as
"Heads up" cards that side-watch relays into the conversation. Spend /steer on the moves those
cards don't make. Pick the one register most likely to move the result:

- **Abstract:** which founding assumption, if false, flips the conclusion? Test that one. No nitpicks.
- **Abductive:** which single hidden mechanism would explain the open surprises together, and
  what observation would refute it? Where has the work never looked? Look there.
- **Multimodal:** what evidence is sitting in another form you hold but haven't read (image,
  3D model, screenshot, nested media)? What does the problem look like redrawn as a map,
  timeline or diagram?
- **Invariant:** does the result hold across the other elections, countries or decades, or
  under a natural intervention that moves the cause within the same person?

If none of these moves anything, run `operator-deck next --n 2` (two of his usual thinking
prompts for this project; process steps are filtered out) or skim `operator-deck list`.

Check the idea against the existing work before calling it a miss. Apply at most one whose
When fits. If none fits, say so in one line and continue.

Report the angle or the hole in plain words, with what you did about it. The move names are
agent-written labels he may not recognize ("run agents as a staffed organization" drew
"wdym?"), so don't quote them.

Log it: `operator-deck log <id> --outcome applied --note "…"` (`--outcome na` for one
you checked that doesn't apply).

Full lists: `~/Projects/skills/research/references/follow-up-moves.md` (moves) and
`~/Projects/skills/references/operator-frames.md` (how he thinks).
