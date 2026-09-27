---
name: steer
description: "Use when: stuck, about to wrap up, or unsure what's next in a long session. Pick at most one of the operator's usual follow-up moves (operator-deck). NOT a checklist to run through."
user-invocable: true
---

# Steer — the operator's usual next move

Ask what the operator would push on here. If nothing comes to mind, run
`operator-deck next --n 2` (two of his usual moves for this project) or skim
`operator-deck list`.

Apply at most one whose When fits. If none fits, say so in one line and continue.

Log it: `operator-deck log <id> --outcome applied --note "…"` (`--outcome na` for one
you checked that doesn't apply).

Full lists: `~/Projects/skills/research/references/follow-up-moves.md` (moves) and
`~/Projects/skills/references/operator-frames.md` (how he thinks).
