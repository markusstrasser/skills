# Big-task prompt for Claude Fable 5.2: template

Two files per task, written to `.claude/plans/<session8>-<slug>.system.md` and
`.claude/plans/<session8>-<slug>.brief.md` in the repo the run works in. The first holds the
behaviour text the guide says belongs in a system prompt; the second is the run's first user
message. Section names cite `guide-digest.md`. Lines marked "choice" are this skill's, not the
guide's.

Delete any part that does not apply. Do not leave a placeholder or an empty tag in the file.

## File 1: `<slug>.system.md` (passed with `--append-system-prompt "$(cat <file>)"`)

The guide puts each of these in the system prompt and says to change system-prompt text only in
a new conversation (A, intro Note). Claude Code already loads CLAUDE.md, AGENTS.md and memory;
do not repeat them here.

```text
# Finishing work
[Only if the harness lacks it. Claude Code 2.1.322 carried its own "Finishing work" section in
the drafting session's system prompt; in that case leave this out. Otherwise paste the guide's
block from source/guide.md lines 58-67, adapted to this task's real deliberate blockers.]
-- why: A, Finish the whole task. Early stops cluster at low/medium effort.

[Ownership sentence, only if the operator chose it:]
This codebase is yours: what it's for and how it's built are your call, and you'll keep
building on it.
-- why: A, Say who owns the code. Raises merging and adjacent fixes, ~1.5x output tokens,
   occasional behaviour changes. Leave out when the operator wants minimal change.

# Approvals
These actions need a go-ahead from {{OPERATOR}} first: {{EXACT_ACTIONS}}.
These need no approval: {{ROUTINE_STEPS, e.g. rerunning a failed test or build, which is safe
to repeat; committing to main under the repo's rules; starting subagents on {{MODEL}}}}.
[For each standing "never" rule the run will load that this task must cross, write the
exception into the rule's restatement here: "Never X, except Y, which {{OPERATOR}} approved
for this task on {{DATE}}."]
-- why: A, Approvals and Keep caution from piling up. Rules are applied as written; a general
   "act freely" line changed nothing; an exception inside the rule works, a separate line
   does not.

# Subagents
[choice] A subagent costs {{WHAT, e.g. a fresh context that rereads the files, and the plan
allowance of its model}}. Delegate {{WHEN_WORTH_IT}}; do {{WHEN_NOT}} yourself. Run briefed,
checkable subtasks on {{SUBAGENT_MODEL}}. Brief each one with the goal, the files, what is
ruled out and the exact check it must pass.
-- why: A, Set expectations for subagents (cost first, when worth it, how to brief, which
   model subagents run on).

# Updates
[Interactive run only:] Before you start, say in a line what you're about to do; brief updates
while you work help the user follow along. Close with a short recap that stands on its own
(what you found, what you did, and what's next), so a reader who only sees the last message
has the full picture.
[Headless run: leave this out.]
-- why: A, Keep users informed during long turns. ~20% more output tokens; gaps matter less on
   asynchronous runs.
```

## File 2: `<slug>.brief.md` (the first message)

Order follows B, Long context prompting: long material first, the instruction last. Tags follow
B, Structure prompts with XML tags.

```xml
<documents>
  [Only when the brief inlines long material (20k+ tokens): one <document> per source with
  <source> and <document_content>. Otherwise list paths in <sources> below and let the run
  read them.]
</documents>

<context>
{{ONE-SENTENCE ROLE, if the task wants one}}                       -- B, Give Claude a role
Why this task exists: {{GOAL BEYOND THE GOAL, what decision or outcome it serves}}
                                                                   -- B, Add context
Current state: {{what exists, what was tried, what failed, with commit SHAs or file paths}}
Settled decisions the run must not reopen: {{each with its reason}} -- B, Add context
</context>

<sources>
{{Paths, URLs and commands that are the system of record, each with what it is for.
Read before claiming anything about it.}}               -- B, Minimizing hallucinations
</sources>

<task>
{{The outcome as imperative actions: "Port X", "Change Y", "Write Z to path P".
Numbered when order or completeness matters.}}           -- B, Be clear and direct; Tool usage
Deliverables:
1. {{artifact, path, form}}
</task>

<scope>
In scope: {{...}}   Out of scope: {{...}}   Do not touch: {{paths and why}}
                                                     -- A, Finish the whole task (deliberate
                                                        blockers must be named to be honoured)
</scope>

<done>
The task is done when these pass, run by you:
- {{exact command}} -> {{expected result}}
- {{exact command}} -> {{expected result}}
Write a general solution; the checks verify it and do not define it. If a check is wrong,
say so instead of working around it.        -- B, Research (success criteria); Avoid focusing
                                               on passing tests; Long-horizon (verification)
</done>

<state>
[choice: include when the run may outlast one context window]
Keep progress in {{progress file path}} and test status in {{tests file path}}; commit
working steps with git. If your context is compacted, reread those files and the git log
before continuing.                           -- B, Long-horizon reasoning and state tracking
</state>

<examples>
[Only when output format matters: 3-5 relevant, varied examples.]  -- B, Use examples
</examples>

<report>
The report is read by {{reader}}, who has not seen your tool calls or files. Open with
{{what they need first}}. Include {{required items, e.g. what changed with SHAs, which done
checks ran and their output, what is left and why}}.     -- A, Make reports easy to follow
</report>

{{Restate the task in one or two sentences as the last line.}}    -- B, Long context prompting
```

## Lines that must not appear in either file

Each is from A, Review instructions written for earlier models, or A, Safeguard refusals.

- A request to think less or answer without deliberating (use a lower effort instead).
- "Treat that answer as done" or similar lines that stop it revisiting earlier work.
- A request to write out its reasoning in the response (`reasoning_extraction` refusals).
- A token budget written into the prompt.
- A standing instruction to delegate that this task does not need.
- Hard style limits such as maximum words per sentence.
- Cautions copied in from notes or memory whose reason does not hold for this task.
