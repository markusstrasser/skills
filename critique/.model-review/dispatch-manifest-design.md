# Design: manifest-first critique dispatch

## Problem
Session agent running `/critique` carried scout/budget/scope as CLI flags. Policy should live in deterministic triage output.

## Solution

### `scripts/review_gate.py` triage → dispatch manifest
Adds top-level `dispatch_policy`:
- `premise_scout` (bool)
- `context_scope` (`repo` | `packet`)
- `budget_seconds` (int | null)

Heuristics (no LLM):
- Packet with path refs → `repo` + scout on
- Self-contained packet, no refs → `packet` + scout off
- Manifest `review_targets.design_target.*` overrides win

### `scripts/model-review.py`
- `--dispatch-manifest` reads policy; explicit CLI overrides when set
- Exits 1 if manifest `blockers` non-empty
- `--axes` omitted → from manifest `layers.design.axes` or `preset`
- Budget gate uses `_resolved_axis_timeout()` (llmx high=600s scale)

### Budget (opt-in)
Skip axis if remaining wall clock < resolved profile timeout. Never truncate.

## Open questions
1. Should model-review read extract/verify flags from manifest?
2. Regex context_scope inference — brittle?
3. Drop formal axis in triage when budget too small?
4. Require manifest on every dispatch?
