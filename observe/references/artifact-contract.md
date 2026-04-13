<!-- Reference file for observe skill. Loaded on demand. -->
# Observe Artifact Contract

This skill uses one canonical artifact tree:

```bash
export OBSERVE_PROJECT_ROOT="${OBSERVE_PROJECT_ROOT:-$HOME/Projects/agent-infra}"
export OBSERVE_ARTIFACT_ROOT="${OBSERVE_ARTIFACT_ROOT:-$OBSERVE_PROJECT_ROOT/artifacts/observe}"
```

Use the same root in docs, scripts, and manual runs. If a legacy workspace still points somewhere
else, override it with the env vars above instead of copying a second hard-coded root.

## Mandatory Run Artifacts

Each non-trivial observe run should write:

- `manifest.json`
- `signals.jsonl`
- `candidates.jsonl`
- `digest.md`
- `dispatch.meta.json` when an external dispatch ran

`improvement-log.md` is not a primary run artifact. It is a promotion sink for candidates that
already passed the gates below.

## Deterministic-First Flow

1. Write `manifest.json` with mode, project filter, session ids, and run inputs.
2. Extract transcripts into `input.md` and optionally `codex.md`.
3. Build `coverage-digest.txt` and `operational-context.txt`.
4. Run deterministic pre-filters such as `session-shape.py`.
5. Append raw observations to `signals.jsonl`.
6. Derive backlog items in `candidates.jsonl`.
7. Write a human-readable `digest.md`.
8. Only then synthesize or promote to `patterns.jsonl` or `improvement-log.md`.

Signals are source-of-truth observations. Candidates are backlog items. Findings are only final
after promotion gates pass.

## Signal Record

`signals.jsonl` is append-only. One line per deterministic observation.

Required fields:
- `schema`: `"observe.signal.v1"`
- `kind`: short signal type such as `"session_shape"` or `"correction_signal"`
- `signal_id`: stable id derived from the source facts
- `session_id`: full session uuid when available
- `project`: project slug
- `source`: script or extractor that produced it
- `status`: always `"signal"`

Useful optional fields:
- `evidence`
- `features`
- `threshold`
- `reasons`
- `start_ts`

## Candidate Record

`candidates.jsonl` is the backlog queue. One line per proposed action item.
Records are append-only. When a candidate moves from `candidate` to `triaged`,
`promoted`, or `suppressed`, write a new line with the updated state.

Required fields:
- `schema`: `"observe.candidate.v1"`
- `kind`: candidate type such as `"session_shape_anomaly"` or `"user_correction_pattern"`
- `candidate_id`: stable id derived from the source signal(s)
- `sessions`: list of full session uuids or prefixes when applicable
- `project`: project slug
- `source_signal_ids`: list of signal ids that justify the candidate
- `state`: one of `candidate`, `triaged`, `promoted`, `suppressed`
- `promoted`: boolean
- `recurrence`: integer recurrence count, if known
- `checkable`: boolean indicating whether a deterministic gate exists
- `summary`: short backlog description
- `priority`: triage priority or numeric score
- `dedupe_status`: `unchecked`, `matched`, `novel`, or `suppressed`

Useful optional fields:
- `evidence`
- `evidence_anchors`
- `suggested_action`
- `severity`
- `source`
- `wasted_turn_estimate`
- `likely_fix_surface`
- `existing_coverage_match`

## Promotion Rule

Do not write candidates to `improvement-log.md` unless all three gates pass:

1. Recurs across 2+ sessions
2. Not already covered by existing hooks or rules
3. Checkable predicate or architectural enforcement exists

If any gate fails, keep the item in `candidates.jsonl` with an explicit `state`.
State transitions are append-only. Do not rewrite old rows.
