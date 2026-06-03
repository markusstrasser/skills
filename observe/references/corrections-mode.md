<!-- Reference file for observe skill (sessions --corrections mode). Loaded on demand. -->
# Corrections Mode (`--corrections`)

When invoked with `--corrections`, extract user correction patterns instead of behavioral anti-patterns.

## Step C1: Extract Corrections (zero LLM)

Scan transcripts structurally for correction signals:

1. **User negation after assistant action:** User messages containing "no", "don't", "wrong", "not that", "stop", "instead" immediately following an assistant tool call or response
2. **#f feedback tags:** Run `uv run python3 ~/Projects/skills/harvest/scripts/extract_user_tags.py --project <project> --days 7` to get tagged feedback
3. **Tool retry patterns:** Same tool called 3+ times with different parameters (trial-and-error)
4. **Failure->correction->success:** Tool failure, followed by user message, followed by successful tool call with different approach

For each pattern, extract the (trigger, correction) pair -- what went wrong and what fixed it.

## Step C2: Classify

Classify each extracted pair using the shared dispatcher wrapper and a cheap model profile.
Do not bypass the shared dispatcher.

Classify as exactly one of:
- `hook-candidate`: a deterministic check could prevent this
- `prompt-hook-candidate`: needs LLM judgment to prevent
- `code-fix`: should be fixed in the code itself
- `routing-rule`: agent used wrong tool for this query type
- `stale`: about a specific vendor version that may have changed
- `already-covered`: an existing rule or hook already addresses this
- `keep-as-rule`: genuinely needs to be an instruction/memory

## Step C3: Stage Candidates

Append the deterministic correction signals to `signals.jsonl`, then append classified backlog items to `$OBSERVE_ARTIFACT_ROOT/candidates.jsonl`:

```json
{"schema":"observe.candidate.v1","kind":"user_correction","candidate_id":"candidate_123456789abc","sessions":["abc12345"],"project":"meta","source_signal_ids":["signal_123456789abc"],"state":"candidate","promoted":false,"recurrence":1,"checkable":true,"priority":"needs-triage","dedupe_status":"unchecked","category":"hook-candidate","trigger":"...","correction":"...","pattern_summary":"...","suggested_action":"...","likely_fix_surface":"hook","existing_coverage_match":null}
```

## Step C4: Check Promotion Gates

Before promoting any candidate to improvement-log.md, ALL three governance gates must pass:
1. **Recurs 2+ sessions** -- check recurrence count in `candidates.jsonl`
2. **Not already covered** -- grep existing rules/ and hooks for the pattern
3. **Checkable predicate OR architectural change** -- is this enforceable?

Only promote when all three pass. Write non-promoted results to `digest.md` and keep the candidate row append-only.

## Step C5: Integration

Wire correction output into existing analytics:
- `uv run python3 "${OBSERVE_PROJECT_ROOT:-$HOME/Projects/agent-infra}/scripts/hook-outcome-correlator.py"` -- join with hook telemetry
- Compare extracted corrections against hook trigger logs to find gaps

## Step C6: Reflect loop (FM-spine — automated)

Correction + omission signals are ALSO captured automatically at session end by
the zero-API `sessionend-reflect-capture` hook → `~/.claude/reflect-capture.jsonl`
(test bed: intel, agent-infra). The deep pass `just reflect-classify` (agent-infra,
deterministic/$0; `--llm` for $0 claude -p enrichment) clusters those signals,
classifies them against the failure-mode taxonomy (`scripts/fm.py`,
`agent-failure-modes.md`) under a **merge-before-mint** invariant, and routes each
to the cheapest enforcer. It **auto-records** evidence to existing FM dossiers and
**quarantines** new-FM mints + enforcer proposals for the human (auto-record-never-
auto-apply). This is the generalization layer that turns one-off corrections into
FM dossiers — `--corrections` here is the manual/triage view of the same signals.
See `agent-infra/.claude/plans/4d40085a-recursive-session-learning-loop.md`.
