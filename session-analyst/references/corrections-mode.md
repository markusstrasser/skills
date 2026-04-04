<!-- Reference file for session-analyst skill. Loaded on demand. -->
# Corrections Mode (`--corrections`)

When invoked with `--corrections`, extract user correction patterns instead of behavioral anti-patterns.

## Step C1: Extract Corrections (zero LLM)

Scan transcripts structurally for correction signals:

1. **User negation after assistant action:** User messages containing "no", "don't", "wrong", "not that", "stop", "instead" immediately following an assistant tool call or response
2. **#f feedback tags:** Run `uv run python3 ~/Projects/meta/scripts/extract_user_tags.py --project <project> --days 7` to get tagged feedback
3. **Tool retry patterns:** Same tool called 3+ times with different parameters (trial-and-error)
4. **Failure->correction->success:** Tool failure, followed by user message, followed by successful tool call with different approach

For each pattern, extract the (trigger, correction) pair -- what went wrong and what fixed it.

## Step C2: Classify with Haiku

For each extracted pair, classify using Haiku (cheap, ~$0.001/call):

```bash
llmx chat -m claude-haiku-4-5-20251001 "
Given this agent correction pattern:
TRIGGER: [what the agent did wrong]
CORRECTION: [what the user said to fix it]

Classify as exactly one of:
- hook-candidate: a deterministic check could prevent this (e.g., always use uv run, never delete X)
- prompt-hook-candidate: needs LLM judgment to prevent (e.g., check if claims are sourced)
- code-fix: should be fixed in the code itself (e.g., script should validate input)
- routing-rule: agent used wrong tool for this query type
- stale: about a specific vendor version that may have changed
- already-covered: an existing rule or hook already addresses this
- keep-as-rule: genuinely needs to be an instruction/memory

Output: {category, pattern_summary, suggested_action}
"
```

## Step C3: Stage Candidates

Append classified corrections to `$HOME/Projects/meta/artifacts/rule-candidates.jsonl`:

```json
{"date": "2026-03-21", "project": "meta", "session": "abc123", "category": "hook-candidate", "trigger": "...", "correction": "...", "pattern_summary": "...", "suggested_action": "...", "recurrence": 1, "promoted": false}
```

## Step C4: Check Promotion Gates

Before promoting any candidate to improvement-log.md, ALL three constitutional gates must pass:
1. **Recurs 2+ sessions** -- check recurrence count in `rule-candidates.jsonl`
2. **Not already covered** -- grep existing rules/ and hooks for the pattern
3. **Checkable predicate OR architectural change** -- is this enforceable?

Only promote when all three pass. Output promotion decisions with evidence.

## Step C5: Integration

Wire correction output into existing analytics:
- `uv run python3 ~/Projects/meta/scripts/hook-outcome-correlator.py` -- join with hook telemetry
- Compare extracted corrections against hook trigger logs to find gaps
