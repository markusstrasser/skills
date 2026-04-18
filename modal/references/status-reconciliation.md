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

## INTERRUPTED as a first-class status

For any workflow that can be preempted mid-run, treat `INTERRUPTED` as a
distinct receipt status alongside `SUCCESS` / `FAILED` / `RUNNING`. See
`resources.md` → "INTERRUPTED State Machine" for the reconciler branch
table (receipt × live-app × marker combinations) and the marker-scoping
rules (filter by `app_id` on read, delete by `run_id` on write-success).

## Pre-Launch Survivability Probe

Before any long-duration relaunch, validate the live control plane
round-trips end-to-end. A $0 probe that takes <60 s beats learning your
`modal.Dict` auth is broken two hours into a paid run.

Three sub-probes worth running:

- **worker_state**: write → Dict → read → external observer surfaces it →
  cleanup. Validates the 7-day-TTL live channel.
- **budget_halt**: set flag → read → admission-control path raises →
  clear. Validates the graceful-halt catch.
- **interrupt_markers**: write synthetic markers (one matching app_id,
  one stale) → strict filter returns only the match → run-id-scoped
  delete → stage dir clean.

Exit code = count of failed sub-probes. Never launch a full batch if any
sub-probe fails — a broken control plane costs more than it saves.

## Reconciler Testing

`modal.Volume` access in a reconciler makes tests painful. Accept an
injectable volume factory:

```python
class ControllerReconciler:
    def __init__(self, volume_factory=None):
        self._make_volume = volume_factory or (
            lambda: modal.Volume.from_name("my-volume")
        )
```

Tests pass a `FakeVolume` with `listdir`/`read_file`/`remove_file` —
no Modal auth required. The reconciler stays testable offline and
every INTERRUPTED-state-machine branch gets direct coverage.
