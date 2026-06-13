<!-- Reference file for observe skill (drift mode). Loaded on demand. -->
# Drift Dispatch Prompt

Full prompt sent to the `deep_review` profile (gemini-3.5-flash, 1M context) in drift mode
via the shared dispatch wrapper. Same wiring rule as `gemini-dispatch-prompt.md`: read files
with `Path.read_text()`, concatenate, send ONE context string. The wrapper owns model routing.

Drift differs from `sessions` mode in TIME SCALE and QUESTION. Sessions asks "what broke in
this session." Drift asks "what is true ACROSS many sessions that no single retro can see" —
slow-moving patterns that look like noise at 1×/day but are signal over weeks.

The prompt content to send (after the concatenated wide-window context):

```text
You are analyzing a WIDE window of session transcripts (typically 2-4 weeks, many sessions)
for SLOW-MOVING patterns that single-session retros are structurally blind to. Sessions come
from TWO harnesses sharing the working directory: Claude Code (Anthropic) and Codex CLI (OpenAI).
Attribute harness-specific behavior correctly:
- Claude Code tools: Bash, Read, Edit, Write, Grep, Glob, Agent, WebSearch, WebFetch, mcp__*
- Codex CLI tools: exec_command, apply_patch, read_file, update_plan, spawn_agent, mcp__*

SESSION ID ANCHORING: Use ONLY the 8-char prefixes from the "VALID SESSION IDS" table(s) in the
input. Include source in parens — "019d7aab (codex)", "82777db1 (claude-code)". Never invent IDs.
If you cannot attribute, say "unattributed".

The attached coverage-digest.txt lists findings, hooks, rules, and project-memory entries that
ALREADY EXIST and are SANCTIONED. Do NOT re-report anything covered there.

Do NOT report per-session anti-patterns — that is a different mode's job. Report ONLY the four
drift classes below. For each finding, give the EVIDENCE that makes it a TREND, not an instance:
session-id list (or count), and the direction over time.

1. RECURRENCE (promotion gate). Patterns appearing in 2+ DISTINCT sessions across the window.
   The constitution promotes a finding to a rule/fix ONLY if it recurs 2+ sessions. You are the
   recurrence counter the operator currently eyeballs. Output: pattern, distinct-session count,
   session-id list, whether it is already covered (if so, drop it).

2. PROPOSED-BUT-NEVER-BUILT. Fixes/hooks/tools proposed or queued in EARLIER sessions in the
   window with NO follow-through in LATER sessions or in the git-commit operational context.
   These are the silent drops. Output: what was proposed, where (session-id), and the absence
   of any landing commit.

3. RISING FRICTION. Friction whose RATE is trending UP over the window — repeated manual steps,
   growing tool-call counts for the same task class, recurring same-error loops, latency/cost
   creep. Output: the friction, early-window rate vs late-window rate, direction.

4. CONVENTION DRIFT. A convention/pattern that was consistent early in the window and has
   diverged later (naming, structure, dispatch choices, commit hygiene). Output: the convention,
   the early form, the drifted form, session evidence.

For EVERY finding, end with a one-line PROPOSED ACTION typed as one of:
[rule] [hook] [skill] [architectural] [obs-only]. Use [obs-only] when it is a behavioral
calibration observation with no concrete build — most recurrence findings are [obs-only] until
they cross a build threshold.

Be terse. One finding per block. No preamble, no summary paragraph. If a drift class has no
genuine signal, write "CLASS N: none" and move on. Do not pad.
```

## Output contract

Drift findings stage into the SAME `candidates.jsonl` flow as sessions mode (see
`references/artifact-contract.md`). Tag each candidate `"mode":"drift"` and carry the
distinct-session count in the evidence field so the promotion gate (2+ recurrences) is
machine-checkable. `[obs-only]` findings go to the improvement-log as `[obs]` entries, never `[ ]`.
