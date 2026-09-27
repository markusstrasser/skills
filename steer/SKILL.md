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
asked, the construct or comparison that is off. If nothing comes to mind, run
`operator-deck next --n 2` (two of his usual thinking prompts for this project; process steps
are filtered out) or skim `operator-deck list`.

Check the idea against the existing work before calling it a miss. Apply at most one whose
When fits. If none fits, say so in one line and continue.

Report the angle or the hole in plain words, with what you did about it. The move names are
agent-written labels he may not recognize ("run agents as a staffed organization" drew
"wdym?"), so don't quote them.

Log it: `operator-deck log <id> --outcome applied --note "…"` (`--outcome na` for one
you checked that doesn't apply).

Full lists: `~/Projects/skills/research/references/follow-up-moves.md` (moves) and
`~/Projects/skills/references/operator-frames.md` (how he thinks).
