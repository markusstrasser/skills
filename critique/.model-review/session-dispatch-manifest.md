# Session close: manifest-first critique dispatch

## What shipped this session

### `scripts/review_gate.py`
- `infer_dispatch_policy()` — deterministic scout/scope/budget from packet + manifest
- Triage output includes `schema_version: dispatch.v1` and `dispatch_policy`
- Triage exits 1 when blockers non-empty
- `--budget-seconds` passes through to policy

### `scripts/model-review.py`
- `--dispatch-manifest` reads policy; explicit CLI flags override unset defaults
- Manifest blockers → exit 1 before dispatch
- `DispatchBudget` skip-or-full; `_resolved_axis_timeout()` for high/xhigh scale
- Writes execution receipt after dispatch; incomplete overall → exit 2
- `--axes` omitted → from manifest preset/axes

### Tests in `scripts/test_review_gate.py` and `scripts/test_model_review.py`

## Design invariants
1. Triage owns policy; dispatch executes manifest
2. Never start axis if full resolved timeout won't fit budget
3. Partial dispatch must not look like success (execution receipt)

## Open risks
- Regex context_scope inference brittle
- model-review does not read extract/verify from manifest yet
- Pre-v1 manifests without schema_version only warn

## Docs
- `references/dispatch.md`
- `SKILL.md`
