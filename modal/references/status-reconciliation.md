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

> Sections below relocated verbatim from modal/SKILL.md (2026-10-21).

## Common Failure Modes

### Live State Disagrees With Worker State

- `running_live`: live app exists now; worker state may simply be lagging
- `stale_receipt`: latest receipt still says running, but live runtime is gone
- `duplicate_live_app`: multiple live apps claim the same stage/run
- `incomplete_attempt`: control plane or launcher says work should be active, but no matching live/runtime signal exists
- `local_driver_invisible`: Modal app list is empty, but a LOCAL orchestrator/driver subprocess is mid-run (planning / volume crawl / repin, *before* any Modal dispatch). An empty Modal does NOT mean idle — check `ps` for the driver + its progress log before concluding "nothing is running". The inverse of `stale_receipt`: there the receipt lies alive; here Modal lies dead.

Usual checks:

- `modal app list --json`
- `ps` for the local driver/orchestrator subprocess (the plane Modal can't see)
- app tags
- `modal app logs --follow`
- receipt timestamp vs latest heartbeat/progress
- driver progress log (distinguishes rate-limit backoff from a true hang)
- If the live app is stopped but a stage receipt still says `RUNNING`, call it `stale_receipt`.
- If the app has high wall-clock age but no fresh logs/heartbeats, do not treat app age as proof of useful compute.

### Output Exists But Meaning Is Ambiguous

- volume file exists but no receipt: manual artifact or partial write
- receipt says success but validation fails: output is present, not trustworthy
- local mirror exists while a newer run is active: `local_stale`
- worker completed but local bridge is missing: `bridge_failed`

Usual checks:

- immutable receipt
- completion marker or validation function
- local bridge state
- run-scoped output path or manifest hash

### Spend Is Detached From Execution State

- `unattributed_spend`: billing row has no usable tag join
- running work with no tags: expect future attribution gap
- spend after failure can be real; do not call it `running`
- stage-local progress `run_id` can differ from the pipeline run id in billing
  tags; join strictly first, then fall back only when
  `sample+stage+attempt_id` maps to a unique billing pipeline run

Usual checks:

- `modal billing report --json --tag-names ...`
- app tags: `question_id`, `run_id`, `stage`
- per-stage billing aggregation

See `references/attribution.md` for the reporting template.

<!-- moved-from modal/SKILL.md L30-60 2026-10-26 -->
## Truth Surface By Question (full wording) (moved verbatim from SKILL.md)

> Moved verbatim from modal/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

## Truth Surface By Question

"Is it running?" is NOT one question — it splits across three liveness planes, and
the *obvious* check is wrong on each:

- `Is a STAGE executing on Modal right now?` -> live Modal app state — but read
  `task_count`/ephemeral, NOT `is_running`. An always-deployed infra app reads
  `is_running: true` at `task_count: 0` (idle, not working).
- `Is the local DRIVER/orchestrator alive right now?` -> the LOCAL process plane
  (`ps` for the driver subprocess), NOT Modal. A local-driven workflow's heavy
  phase (planning, volume crawl, repin) runs on your host and dispatches Modal
  apps only AFTER it — so Modal is empty while the driver grinds. Modal app state
  is structurally blind to the driver.
- `Is it ADVANCING (vs hung)?` -> the driver's own progress log, NOT CPU% or "the
  log looks frozen". Rate-limit backoff (e.g. Modal `VolumeListFiles`) freezes CPU
  and stdout for tens of seconds and mimics a deadlock — the log line
  (`backing off`, `N/M probed`) is the liveness signal, not process vitals.
- `Did the worker finish?` -> immutable receipt / terminal artifact
- `Why did it fail?` -> container logs, app logs, stderr tails, worker receipt error
- `Can I trust the output?` -> volume artifact plus checksum/validation, not app state
- `What did this cost?` -> billing rows joined by tags. In genomics,
  `stage-telemetry` reports `billing_actual` from Modal billing and
  `planning_cost_projection` separately; if billing is unavailable, do not
  substitute the projection or treat the attempt as `$0`.

Do not answer a live-state question from a volume file.
Do not answer a billing question from app state.
Do not answer driver/orchestrator liveness from Modal app state — join with the
local process plane (`ps`); an empty Modal app list does NOT mean nothing is running.
Do not read `is_running` as "doing work" — join with `task_count`/ephemeral.
Do not merge these into one synthetic status.

<!-- moved-from modal/SKILL.md L160-169 2026-10-26 -->
## Failure-Mode Cheatsheet (full wording) (moved verbatim from SKILL.md)

> Moved verbatim from modal/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

## Failure-Mode Cheatsheet

- **Import error or crash loop after detach** -> inspect live app state first; `retries=0` does not stop container crash retries
- **Receipt says running forever** -> likely `stale_receipt`; compare receipt timestamp to live logs/progress
- **Detached app looks alive for hours** -> app age is not progress; check latest worker logs and receipt heartbeat before assuming compute is still happening
- **Logs show `Runner interrupted due to worker preemption` or `Worker disappeared`** -> treat the run as unhealthy until you see fresh progress after the restart
- **Old results still visible after stop** -> outputs need run identity; volume state is not liveness
- **Large sync or probe is slow/heavy** -> use Modal SDK reads, not repeated CLI subprocesses
- **Download or write looks complete but is wrong** -> validate integrity, not just size; use atomic completion markers
- **Unexpected GPU bill** -> check `max_containers`, tags, and `.starmap()` fanout before anything else
