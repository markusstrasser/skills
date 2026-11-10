# Digest: Prompting Claude Fable 5.2 (and the pages it leans on)

Fetched 2026-11-10 (14:36 UTC) as Markdown by appending `.md` to each URL. Copies, byte
counts and sha256 sums: `../source/FETCH.txt`. Headings below are the guide's own, in its
order. Quotes are short and only where the wording carries the rule. Everything is
Anthropic's own testing; none of it is measured on our tasks.

Primary page: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2

Scope note: the page covers what differs on Fable 5.2 (behaviour, system-prompt text, harness
settings). How to structure a prompt in general is deferred to "Prompting best practices",
digested in part B.

## A. Prompting Claude Fable 5.2

### (intro and Note)

- Routes by symptom: effort, early stops, approvals, ownership, silence, subagents, caution,
  old instructions, reports, refusals.
- Make system-prompt, tool-description and notes changes "in new conversations only". The API
  enforces a prefix check on Fable 5.2: thinking blocks sent back after `system`, `tools` or an
  earlier message changed can return 400. To change instructions mid-conversation, put them
  in the newest turn (or a mid-conversation system message where available).

### Calibrate effort

- Start at `high` (API default). Move up or down only against your own evals; rerun the sweep
  instead of carrying a 5.1 or Opus 5.5 setting over.
- `low`: quick back-and-forth, well-specified tasks, high volume, fast subagents (scored near
  Fable 5.1 at higher effort). `medium`: interactive coding, chat, everyday knowledge work.
  `high`: hard coding, research, agentic work, long unattended runs. `xhigh`: hardest
  long-running coding and agentic work "where you've measured a gain" (slight gain, many more
  tokens). `max`: ceiling measurement or the rare task where time and tokens do not matter.
- "Most of the gain in capability is already present at `high`."
- Three behaviours: early stops are more likely at `low`/`medium`; at `high`+ it thinks before
  almost every reply, and a "answer directly without deliberating" line did not stop thinking
  at `medium`+; effort barely changes reply length, so set length and tone in the prompt.
- Levels can be mixed: plan at `medium`, raise effort for the long unattended part.

### Finish the whole task

- On long multistep tasks it sometimes ends a turn early: a list of what remains, an offer to
  continue, or a stop at an ordinary obstacle. More often at `low`/`medium`.
- Suggested system-prompt block "# Finishing work" (verbatim copy in `../source/guide.md`,
  lines 58-67). Its point is a split between ordinary obstacles (diagnose, work through:
  retry, fix the request, use another tool) and deliberate blockers (leave alone, report,
  look for another safe way). It keeps confirmation for risky or destructive actions.
- Effect in replayed sessions at `medium`: about half as many sessions ended with doable work
  left; it removed most permission-asking endings but not "list what remains, then stop"
  endings; output tokens rose about 30%.
- Keep your own confirmation step for risky or irreversible actions.

### Approvals

- When you tell it to keep going, say what you want: "Yes, run the migration on the staging
  database", not "go".
- Approval rules are applied as written, so name the exact actions they cover. A rule that
  listed "sending messages to people outside this conversation" made it hold back about half
  of its routine requests to colleagues.

### Say who owns the code

- With no ownership statement, or with the code presented as someone else's, it tends to add
  to existing structure (even repeating code) and to report nearby problems instead of fixing
  them.
- Sentence to use when you want it to improve structure: "This codebase is yours: what it's
  for and how it's built are your call, and you'll keep building on it."
- Effect: merged repeated code in about half of tries vs under a tenth; about 1.5x output
  tokens; unrequested changes (tests, docs); changed an existing feature's behaviour in one
  try in six to ten, more at higher effort; the closing summary often omitted small changes,
  "so review the diff and not only the summary".
- A scope-limiting rule elsewhere does not cancel the sentence. Leave it out where the user
  owns the code and wants minimal change.

### Keep users informed during long turns

- Updates between tool calls arrive as progress-update `thinking` blocks, empty at the default
  `display: "omitted"`; a client must request `"updates"` or `"summarized"` to show them.
- Harness option: after several silent tool steps, append a turn-scoped system reminder ("The
  user hasn't heard from you in a while: say in a few words what you're doing, then
  continue."). Roughly halved the longest silent stretch.
- System-prompt option for a human in the loop: say in a line what you are about to do, give
  brief updates, close with a recap that stands on its own. Spoke before its first tool call
  every time; about 20% more output tokens.
- Without harness control: "Every few tool calls, give the user a one-line update on where
  things stand."
- On long asynchronous tasks, where the user comes back for the result, gaps matter less.

### Set expectations for subagents

- Delegation depends on harness and tasks: rare with a minimal subagent tool, ready in a
  product whose prompts invite delegation.
- First review lines in system prompts, skills and agent files that tell it to delegate.
  Rewrite the subagent tool's description only if it still over-delegates.
- A good description states what a subagent adds to session cost (first), when delegation is
  and is not worth it, and how to brief the subagent. Delegated about a third less, same task
  success.
- At `xhigh`/`max` it used subagents to review its own work. Early testers did well with it as
  planner and orchestrator for other models. "Check which model your harness runs subagents
  on by default."

### Keep caution from piling up

- Cautious instructions accumulate in memory, notes, instruction files and messages between
  agents; Fable 5.2 follows them closely and may ask for approvals it does not need or hold
  back routine work, mostly in multi-agent setups.
- Remove notes you no longer need (one "never retry" note among a dozen cut retries after a
  busy tool from nearly all to about four in ten).
- Name the steps that need no approval (listing retries raised retries from almost none to
  about half; a general "act more freely" changed nothing). Name retries only for calls safe
  to repeat.
- Check what reviewer agents attach (a reviewer's "stop at the first error" suppressed
  retries in about a third of tries).
- Write the exception into the rule itself: under a "never" rule an approved step was taken
  about one in ten; when the rule itself said to get a go-ahead first, about nine in ten.
- Keep your own confirmation step for risky or irreversible actions.

### Review instructions written for earlier models

Reconsider, when carrying prompts over:

- Standing instructions to delegate (system prompts, skills, agent files).
- A token budget the harness writes into the prompt: removing a large one lowered cost at equal
  performance (`high`/`xhigh`). This is prompt text, not the API's task budgets.
- Harness code that edits earlier turns (invalidates preserved thinking; keep history
  append-only apart from compaction or context editing).
- The Opus 5.5 "treat that answer as done" lines: reduced follow-up thinking but made it far
  less likely to point out its own earlier mistakes.
- Instructions to think less: no effect at `medium`+; lower effort instead.
- Style rules for writing: followed closely, so hard limits ("20 words or fewer") make prose
  choppy; remove unneeded ones before adding the report text.
- Rules, notes and memories that have built up: delete cautions whose reason no longer holds;
  rewrite absolute rules to state their scope and reason; a stuck system can restart with
  trimmed memory (keep the originals).

### Make reports easy to follow

- Readers of a final report have not seen the tool calls or files. Suggested block
  "# Communicating clearly" (`../source/guide.md`, lines 178-183): low-context reader, key
  points first, progressive disclosure, no terms coined during the work, plain full sentences
  in the style of ASD-STE100, prose where ideas connect, bullets for separate items.
- Effect: less dense reports, fewer semicolons, shorter sentences. Length and required details
  can be added.

### Safeguard refusals

- Classifier refusals return `stop_reason: "refusal"` with a category: `cyber`, `bio`,
  `frontier_llm`, `reasoning_extraction`, `general_harms`.
- Remove any instruction that asks the model to write its reasoning in the response; read
  thinking blocks with `display: "summarized"` instead.
- Retry on another model via fallback (What's new: permitted targets Opus 4.8 and Opus 5).

### Where to start

1. Set `effort` to `high` explicitly; also run `medium` and `xhigh`.
2. Read the system prompts, skills, agent files, memory, notes and harness text you carry over;
   remove or test the instructions in "Review instructions written for earlier models".
3. Run the longest agentic tasks; note early stops, unneeded approvals, silence,
   over-delegation, and adding where restructuring was wanted.
4. Apply the guidance one behaviour at a time; measure its effect and its token cost.

## B. Prompting best practices (sections the skill uses)

URL: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices.
The page says its general techniques apply to Fable 5.2; techniques that name another model
were measured on that model.

### Be clear and direct

- "Think of Claude as a brilliant but new employee who lacks context on your norms and
  workflows." Ask explicitly for anything beyond the strict task.
- "**Key test:** Show your prompt to a colleague with minimal context on the task and ask them
  to follow it. If they'd be confused, Claude will be too."
- Be specific about output format and constraints; use numbered steps when order or
  completeness matters.

### Add context to improve performance

- Give the reason behind an instruction; "Claude can generalize from the explanation."

### Use examples effectively

- Examples steer format, tone and structure; make them relevant, diverse, wrapped in
  `<example>`/`<examples>`; 3-5 for best results.

### Structure prompts with XML tags

- Wrap each kind of content (`<instructions>`, `<context>`, `<input>`) in its own tag; use
  consistent names; nest where content has a hierarchy.

### Give Claude a role

- One sentence in the system prompt focuses behaviour and tone.

### Long context prompting

- At 20k+ tokens: put long documents at the top, query and instructions at the end ("up to 30
  percent" better in tests); wrap each document with `<source>` and `<document_content>`; for
  long-document tasks ask for relevant quotes first.

### Control the format of responses

- Say what to do instead of what not to do; match the prompt's own style to the wanted output.

### Tool usage

- Precise instruction following: "Can you suggest some changes" may produce suggestions only;
  "Change this function..." produces changes.

### Long-horizon reasoning and state tracking

- Multi-window work: a different prompt for the first window (set up tests, scripts), then
  iterate on a to-do list; tests in a structured file (`tests.json`); setup scripts
  (`init.sh`); a fresh window can rediscover state from the filesystem ("Review progress.txt,
  tests.json, and the git logs."); give verification tools; structured formats for state,
  free text for progress notes, git for checkpoints; ask for incremental progress.
- In a harness that compacts context, tell it so, so it does not wrap up early near the limit.

### Balancing autonomy and safety

- Name which actions need confirmation (destructive, hard to reverse, visible to others) and
  that local reversible actions do not; do not use destructive shortcuts around obstacles.
  (The page states the default behaviour for Opus 4.6; the sample prompt is generic.)

### Research and information gathering

- Give clear success criteria; ask for verification across sources; for complex research,
  competing hypotheses, confidence tracking, a notes file.

### Subagent orchestration

- Make subagent tools available and described; if it over-delegates, say when subagents are and
  are not warranted.

### Avoid focusing on passing tests and hardcoding

- Ask for a general solution; tests verify correctness and do not define the solution; report
  wrong tests instead of working around them.

### Minimizing hallucinations in agentic coding

- Never speculate about code it has not opened; read referenced files before answering.

## C. Related pages (only the facts the skill uses)

- What's new in Claude Fable 5.2
  (https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2), "Behavior
  differences": lists the same six behaviours (no think-less, early turn end, ownership,
  quiet tool runs, harness-dependent delegation, style rules followed closely). "Refusals,
  fallback, and billing": fallback targets Opus 4.8 and Opus 5. "Pricing": $8 input, $40
  output per MTok.
- Effort (https://platform.claude.com/docs/en/build-with-claude/effort), "Recommended effort
  levels", Fable 5.2 paragraph: start `high`; `xhigh` for hardest long-running work where a gain
  was measured; at `high`+ set a large `max_tokens` (hard limit on thinking plus text); `max`
  "often for only a small gain". The level table describes `xhigh` as for "Long-running agentic
  and coding tasks (over 30 minutes) with token budgets in the millions".
- Prompting Claude Opus 5.5
  (https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5),
  "Thinking instructions in chat system prompts": the source of the "treat that answer as done"
  lines that the Fable page warns against. Fetched only for that section.
