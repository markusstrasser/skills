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
corpus. Answer each question below yourself. Then sort each one:

- **Act**: every answer he could plausibly give leads to the same plan. Record your answer
  as an assumption and don't ask, even if his wording would differ.
- **Ask**: his plausible answers lead to different plans.
- **Repair**: the brief can't succeed as stated. Propose the smallest change to the
  constraints that would fix it, and ask him to approve it.

Models over-ask on the first case (Li et al. 2026). Questions that are worth asking split the
plan, not just the wording of his answer (Kobalczyk et al., ICLR 2025).

| Axis | What to elicit |
|---|---|
| Altitude | What should happen after this is done? What is the goal beyond the goal: what decision, meeting or recurring chore does this task serve, and which outcome would make it unnecessary? ("fix this crash" becomes "keep the apps crash-free") |
| Raw material | Which system of record would a top practitioner start from instead of a digest? That includes the guidance, amendments and data that govern the primary document, not only the document itself. |
| Outside judge | What, other than you or Markus, would show the result is right? Prefer a check the agent can run: a test, a held-out set, a real audience, a reproduction. A judge without tools is an opinion. |
| Methods | Which instruments do the best people in the field use (a database or statistical model, not a markdown table)? |
| Hard target | What is the 200 ms version of the 5 s goal? Name the target that sounds unreasonable. When nobody knows a method that could hit it, set a learning goal first ("find three approaches that could reach 200 ms"). Hard outcome goals help when the strategy is known and can hurt on novel, complex tasks (Seijts & Latham). |
| Assumption | Which current belief could the raw data falsify? ("We think churn is onboarding; reproduce that from the logs.") |
| Range | Restate the deliverable as verbs ("getting busy people to decide under uncertainty in 30 minutes", not "a deck"). Which fields, red team included, would change the method? Borrow what a short seller *does*; never write *as* one. |

## 2. Ask the survivors

Ask at most three questions per round with AskUserQuestion. A budget of one to three kept
86–94% of the value of unlimited questions at 36–73% less user effort (Zhang et al. 2026).
Offer concrete stances as options, each saying what you would do. For the altitude question,
ask open-ended first, because offered options anchor him on your guess.

These probes from interview psychology get at what he knows but wouldn't volunteer:

- **Altitude: laddering.** Ask "why does that matter?" about the stated goal and repeat on
  the answer. Stop when you reach a decision he has to make or a value he holds.
- **Judge: the miracle question.** "If this came out perfectly, what would you notice first,
  and where?" The answer names something observable, which becomes the outside check.
- **Assumption: premortem.** "It's a month from now and this was a waste. Why?" Imagining the
  outcome as already happened surfaces more reasons than asking what could go wrong.
- **Tacit standards: a specific past case.** "Last time this went well, what did you look
  at?" A concrete case recalls criteria that a question about general preferences misses.
- **Soft words.** If he says "interesting", "deeper" or "good", ask for one example and one
  counterexample, then turn the word into a check you can run.

Follow one answer that splits the plan with a single targeted follow-up rather than a fresh
question. If nothing survives step 1, say so and go to step 3.

## 3. Rewrite the brief and do it

Write the deeper brief in these fields: outcome, raw sources, methods and tools, target,
judge, and fields to borrow. Also list what access is missing (data, connectors, machines,
credentials). Felix's crash-free loop first needed crash reports, version-to-commit mapping
and test machines, so building that environment is usually the first step.

Mark each decision you took on that he didn't ask for, so he can revise it. Raising the
altitude increases those decisions: users judged about half of an LLM's reasoning steps as
work they had not requested (Kim et al. 2026).

Then do the work if the task is authorized. Ask one more altitude question after the first
real result. Intent shifts once he sees output, and models track changing intent poorly
(Tack, Laban & Neville 2026). Returning only a rewritten prompt "hands me
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
