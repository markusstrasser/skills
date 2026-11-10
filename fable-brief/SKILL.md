---
name: fable-brief
description: "Use when: /fable-brief, 'big task', 'big prompt', 'brief for Fable', 'write the prompt for Fable', or before handing one large piece of work to a fresh Claude Fable 5.2 session. Reads the repo first, grills Markus one decision at a time (each question with a recommended answer, never one the code can settle) until a coverage checklist built from Anthropic's Fable 5.2 prompting guide is filled, writes the prompt to files and gives the launch command. NOT small or briefed checkable work (Opus subagents), taste calls (/taste), goal discovery alone (/ambition), plan review (/critique)."
user-invocable: true
argument-hint: "[task, or path to a rough brief]"
---

# Fable brief: one large, complete prompt for a fresh Fable 5.2 session

Fable 5.2 pays off on big tasks, and a big task needs a large, clear prompt. This skill turns
Markus's rough task into that prompt. It interviews him only on what the code, docs and memory
cannot answer, checks the result against Anthropic's guide, writes it to two files and says
how to run it. It does not run the task itself. Markus starts the run in a new session.

Rules about prompting Fable come from the fetched guide, digested in
`references/guide-digest.md` (A = Fable 5.2 page, B = best-practices page). Lines marked
*choice* are this skill's own. The operator's model notes are in
`~/.claude/skills/model-guide/references/models/claude-fable-5-2.md` and
`PROMPTING_CLAUDE.md`. Do not restate them here.

## When to use it

Use it for work that will take a long agentic run: a multi-file port, a subsystem, a research
synthesis over many sources, or a migration. Skip it when:

- the work fits in a handful of tool calls, or is briefed and checkable, so an Opus subagent
  does it (Markus, 2026-11-10);
- the call is about taste or feel (/taste), or the goal itself is unclear (run /ambition
  first);
- the brief is a plan that meets the /critique trigger in `~/.claude/CLAUDE.md`. Write the
  brief, then run /critique before launch.

## 1. Read before asking

Read what the task touches before the first question: the files and modules named, recent
`git log` for those paths, README/architecture docs, open plans under `.claude/plans/`, and the
project's `MEMORY.md` entries that bear on the task. Then draft an answer for every checklist
item in step 3, each with its source (file:line, commit, memory file, doc section).

Also list every caution the run will load that this task must cross: a "never" rule, a memory
note, a reviewer condition. Fable 5.2 follows these closely and holds back routine work under
them (A, Keep caution from piling up). Each one becomes a grill question, or a scoped exception
in the brief.

If the goal beyond the task, the raw source or the outside judge is still a guess, run
/ambition's steps 1-2 for those items only. Take its fields (outcome, raw sources, methods,
target, judge, missing access) as answers, and do not do its step 3 here: the run does the work.

## 2. Grill loop

Ask one question at a time (AskUserQuestion, one question per call). Each question:

- names the decision and why the run needs it settled;
- gives your recommended answer first, with the evidence behind it, then one or two real
  alternatives, each saying what the run would do differently;
- is never a question that the code, docs, git history or memory can answer. Answer those
  yourself, record the source, and tell him in one line that you did.

Follow a surprising answer with one targeted follow-up before moving on. Ask in the order of
the checklist below. Outcome and done checks come first, because the rest depends on them.

Stop when every checklist item holds an answer with its source, or reads "n/a: <reason>", and
no open item would change what the run does. Also stop when Markus says so. Then show him the
assembled files (step 4) and ask one last question: "Anything the run would get wrong?"
*(choice: the guide sets no stop rule.)*

## 3. Coverage checklist

| # | Item | What the brief must say | Guide section |
|---|---|---|---|
| 1 | Outcome | The deliverables as imperative actions with paths ("port", "change", "write to"), not "suggest" or "look into" | B: Be clear and direct; Tool usage |
| 2 | Why | The goal the task serves, the current state, and settled decisions with their reasons | B: Add context |
| 3 | Sources | Systems of record by path or URL; inline long material at the top, instruction last | B: Long context prompting; Minimizing hallucinations |
| 4 | Done | Exact commands the run executes and their expected results; general solution, not one fitted to the tests | B: Research; Avoid focusing on passing tests; Long-horizon |
| 5 | Scope and ownership | In, out, do-not-touch paths. Whether to add the ownership sentence | A: Say who owns the code |
| 6 | Approvals | Exact actions that need a go-ahead; named routine steps that need none (only retries safe to repeat); exceptions written into the rules they break | A: Approvals; Keep caution from piling up; B: Balancing autonomy and safety |
| 7 | Obstacles | Which blockers are deliberate (leave alone, report) and which are ordinary (work through) | A: Finish the whole task |
| 8 | Effort | `high` by default; `xhigh` only for the hardest long coding or agentic run; `max` only when time and tokens do not matter | A: Calibrate effort; Effort page |
| 9 | Subagents | Whether to delegate, what it costs, which model, how to brief | A: Set expectations for subagents |
| 10 | State | Progress file, tests file, git checkpoints, if the run can outlast one context window | B: Long-horizon reasoning and state tracking |
| 11 | Updates | Interactive (add the updates text) or headless (gaps matter less) | A: Keep users informed during long turns |
| 12 | Report | Who reads it, what comes first, what it must include | A: Make reports easy to follow |
| 13 | Examples | 3-5 only if output format matters | B: Use examples effectively |
| 14 | Hygiene | None of the lines the guide says to drop (see the template's last list) | A: Review instructions written for earlier models; Safeguard refusals |
| 15 | Refusal risk | If the task touches the cyber, bio or frontier-LLM categories, say what happens on a refusal or fallback | A: Safeguard refusals |

Notes on items where the guide leaves room:

- **5:** the ownership sentence raises merging and adjacent fixes, and also raises unrequested
  behaviour changes and output by about 1.5x. A scope rule elsewhere does not cancel it. Ask
  when the repo's rules do not already decide it.
- **8:** the guide puts most of the gain at `high`. Recommend `xhigh` only with a reason the
  task is in the "hardest long-running" class. The operator's notes have vendor numbers for
  that trade.
- **12:** the guide's "Communicating clearly" block overlaps
  `~/.claude/rules/answer-format.md`, which every Claude Code session loads. *Choice:* rely on
  that file, and put only the reader and the required contents in the brief. The guide warns
  that stacked style rules get followed literally.

## 4. Assemble

Fill `references/prompt-template.md` into two files in the repo:
`.claude/plans/<session8>-<slug>.system.md` (behaviour text, which the guide puts in the
system prompt) and `.claude/plans/<session8>-<slug>.brief.md` (the first message). *Choice:* two
files, because the CLI accepts an appended system prompt and the guide places this text there.

Before showing it to Markus, run the guide's colleague test (B, Be clear and direct). Give the
brief alone to one fresh-context Opus subagent. Ask it what it would do first, what it would
ask, and which instruction is ambiguous. Fix what it trips on. *(The test is the guide's;
using a subagent as the colleague is this skill's choice.)*

## 5. Run

Start a new session (A, intro Note: system-prompt text changes only in new conversations; later
corrections go in the newest message). From the repo root:

```sh
claude --model claude-fable-5-2 --effort high -n <slug> \
  --append-system-prompt "$(cat .claude/plans/<session8>-<slug>.system.md)" \
  "$(cat .claude/plans/<session8>-<slug>.brief.md)"
```

`--append-system-prompt`, `--effort`, `--model` and `-n` are in `claude --help` (CLI 2.1.322,
checked 2026-11-10). No launch with this command line has been run yet: on the first use, check
in the new session that the system text arrived (ask it to quote its "# Approvals" section)
before the work starts.

That is the interactive form, which Markus watches. For a headless run, add `-p` and
`--output-format stream-json --verbose`, write the output to a log, and drop the updates text
from the system file. Long runs go through `bgrun` (`~/.claude/rules/wakeup-cadence.md`). Do
not dispatch the run as an Agent subagent: the fable agent files record Agent-tool model pins
serving another model. Use the exact model id, not an alias.

When the run stops with work left, reply with what you want, naming the items ("Yes, port the
remaining three handlers and run the test suite"), not "continue" (A, Approvals).

## 6. After the run

1. Confirm the model. The session's model usage should read `claude-fable-5-2`. A safeguard
   refusal can fall back to Opus (A, Safeguard refusals).
2. Run the done checks yourself. The run's claim is not the result.
3. Review the diff, not the summary. With the ownership sentence, the summary often leaves out
   small changes (A, Say who owns the code).
4. Record output tokens and cost next to the outcome (A, Where to start, step 4;
   `~/.claude/rules/eval-token-costs.md`).
5. For each thing the run got wrong, name the checklist item that would have caught it. Edit
   that item's guidance in this skill.
