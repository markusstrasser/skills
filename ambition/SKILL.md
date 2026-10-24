---
name: ambition
description: "Use when: /ambition, 'make this more ambitious', or before a substantive task whose brief is the operator's first guess at a means. Elicits from Markus the goal beyond the goal, the raw source, the outside judge and the fields to borrow, then rewrites the brief and does the work. NOT speed tasks, taste calls (/taste) or plan review (/critique)."
user-invocable: true
argument-hint: "[task, prompt, or brief path]"
---

# Ambition: elicit the deeper version of a task

A brief is the operator's best guess at a means. This skill pulls out what sits behind it,
following Felix Rieseberg's "How to be more ambitious" (2026-10-13). The interview turns his
four depth questions on Markus, because Markus knows the goal, the source and the judge, and
the model does not. The quotes and the one test of these ideas are in
`references/sources.md`.

Skip it for speed work (the same task, faster) and for taste or creative calls. Felix says
altitude "works less well for creative endeavors"; use `/taste` for those.

## 1. Draft your own answers first

Read the task and whatever context is on file: the repo, memory, `CURRENT.md` files and the
corpus. Answer each question below yourself. Ask Markus only where your answer is a guess or
where his plausible answers diverge. Drop any question you can answer for him, and say that
you dropped it.

| Axis | What to elicit |
|---|---|
| Altitude | What should happen after this is done? What is the goal beyond the goal: what decision, meeting or recurring chore does this task serve, and which outcome would make it unnecessary? ("fix this crash" becomes "keep the apps crash-free") |
| Raw material | Which system of record would a top practitioner start from instead of a digest? That includes the guidance, amendments and data that govern the primary document, not only the document itself. |
| Outside judge | What, other than you or Markus, would show the result is right? Prefer a check the agent can run: a test, a held-out set, a real audience, a reproduction. A judge without tools is an opinion. |
| Methods | Which instruments do the best people in the field use (a database or statistical model, not a markdown table)? |
| Hard target | What is the 200 ms version of the 5 s goal? Name the target that sounds unreasonable. |
| Assumption | Which current belief could the raw data falsify? ("We think churn is onboarding; reproduce that from the logs.") |
| Range | Restate the deliverable as verbs ("getting busy people to decide under uncertainty in 30 minutes", not "a deck"). Which fields, red team included, would change the method? Borrow what a short seller *does*; never write *as* one. |

## 2. Ask the survivors

Ask at most three questions per round with AskUserQuestion. Offer concrete stances as
options, taken from your drafted answers. Each option should say what you would do, so he can
correct you in one click. Follow one high-variance answer with a single targeted follow-up
rather than starting a fresh question. If nothing survives step 1, say so and go to step 3.

## 3. Rewrite the brief and do it

Write the deeper brief in these fields: outcome, raw sources, methods and tools, target,
judge, and fields to borrow. Also list what access is missing (data, connectors, machines,
credentials). Felix's crash-free loop first needed crash reports, version-to-commit mapping
and test machines, so building that environment is usually the first step.

Then do the work if the task is authorized. Returning only a rewritten prompt "hands me
homework when I wanted work" (Porres). Stop at the brief only when Markus asked for the brief
or a real gate stands in the way.

A durable preference that comes out of the interview (a standing judge or source for a
domain) goes into a `feedback` memory.

## Evidence status

One public test exists: Porres, n=16 runs, two cross-lab judges. It supports
system-of-record sourcing (13–3 and 11–4 against his previous rules) and a definition of done
that an outsider can run. It also caught one failure: "primary source" collapsed into "the
one document" and missed the governing guidelines. The "what would a top practitioner add"
interview went untested, so it is the least-supported part of this skill. Treat the skill as
a hypothesis and log cases where it helped or got in the way.
