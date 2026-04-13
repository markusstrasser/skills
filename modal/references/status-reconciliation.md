# Status Reconciliation Contract

Answer one operational question at a time. Do not collapse every surface into one fake status.

## Primary Truth Surfaces

- `Is it running right now?` -> live Modal app state
- `What should be happening?` -> orchestrator / control-plane state
- `What did the worker say?` -> immutable worker receipt
- `Can I use the result locally?` -> local mirror / bridge state
- `What is this costing?` -> billing rows joined by tags

## Rules

- Pick the primary truth surface from the question before reading anything else.
- Join surfaces by strong identity first: `stage`, `run_id`, `attempt_id`, `sample_id`.
- If you only have keyword or description matching, label it as heuristic.
- Status and spend are separate reports. Never use one as a proxy for the other.
- When surfaces disagree, name the mismatch class instead of inventing a blended status.

## Common Mismatch Classes

- `running_live`: live app exists for the stage/run now
- `stale_receipt`: latest receipt still says running but live runtime signal is gone
- `incomplete_attempt`: control plane says work should be active, but there is no matching live/runtime signal
- `duplicate_live_app`: more than one live app claims the same stage/run
- `completed_receipt`: worker wrote a terminal receipt
- `bridge_failed`: worker completed but local mirror is missing or unusable
- `local_stale`: local result exists, but a newer run is active or has failed
- `unattributed_spend`: billing exists without matching tags or identity joins

## Minimal Reporting Shape

For each stage you discuss, report:

`question -> primary source -> supporting sources -> mismatch class -> next action`

Example:

`Is triage running now? -> live Modal app list -> receipt says RUNNING, local mirror old -> local_stale -> inspect app tags/logs before trusting local output`
