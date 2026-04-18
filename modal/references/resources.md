<!-- Reference file for modal skill. Loaded on demand. -->

# CPU, Memory, and Disk Resources

## Default Resources

Each Modal container has default reservations:
- **CPU**: 0.125 cores
- **Memory**: 128 MiB

Containers can exceed minimum if worker has available resources.

## CPU Cores

Request CPU cores as floating-point number:

```python
@app.function(cpu=8.0)
def my_function():
    # Guaranteed access to at least 8 physical cores
    ...
```

Values correspond to physical cores, not vCPUs.

Modal sets multi-threading environment variables based on CPU reservation:
- `OPENBLAS_NUM_THREADS`
- `OMP_NUM_THREADS`
- `MKL_NUM_THREADS`

## Memory

Request memory in megabytes (integer):

```python
@app.function(memory=32768)
def my_function():
    # Guaranteed access to at least 32 GiB RAM
    ...
```

## Resource Limits

### CPU Limits

Default soft CPU limit: request + 16 cores
- Default request: 0.125 cores → default limit: 16.125 cores
- Above limit, host throttles CPU usage

Set explicit CPU limit:

```python
cpu_request = 1.0
cpu_limit = 4.0

@app.function(cpu=(cpu_request, cpu_limit))
def f():
    ...
```

### Memory Limits

Set hard memory limit to OOM kill containers at threshold:

```python
mem_request = 1024  # MB
mem_limit = 2048    # MB

@app.function(memory=(mem_request, mem_limit))
def f():
    # Container killed if exceeds 2048 MB
    ...
```

Useful for catching memory leaks early.

### Disk Limits

Running containers have access to many GBs of SSD disk, limited by:
1. Underlying worker's SSD capacity
2. Per-container disk quota (100s of GBs)

Hitting limits causes `OSError` on disk writes.

Request larger disk with `ephemeral_disk`:

```python
@app.function(ephemeral_disk=10240)  # 10 GiB
def process_large_files():
    ...
```

Maximum disk size: 3.0 TiB (3,145,728 MiB)
Intended use: dataset processing

## Billing

Charged based on whichever is higher: reservation or actual usage.

Disk requests increase memory request at 20:1 ratio:
- Requesting 500 GiB disk → increases memory request to 25 GiB (if not already higher)

## Attribution

Treat status and spend as separate dimensions.

- Status comes from logs, container state, or the dashboard.
- Spend comes from billing reports grouped by tags.
- Tag launches with `question_id`, `run_id`, and `stage` so the two can be joined later.

See `attribution.md` for the reporting template.

## Maximum Requests

Modal enforces maximums at Function creation time. Requests exceeding maximum will be rejected with `InvalidError`.

Contact support if you need higher limits.

## Example: Resource Configuration

```python
@app.function(
    cpu=4.0,              # 4 physical cores
    memory=16384,         # 16 GiB RAM
    ephemeral_disk=51200, # 50 GiB disk
    timeout=3600,         # 1 hour timeout
)
def process_data():
    # Heavy processing with large files
    ...
```

## Monitoring Resource Usage

View resource usage in Modal dashboard:
- CPU utilization
- Memory usage
- Disk usage
- GPU metrics (if applicable)

Access via https://modal.com/apps

## Preemption & Retry Hardening

Modal can preempt containers to reclaim capacity. Detached jobs auto-retry
once on preemption, but that's insufficient for long jobs.

### `modal.Retries` — automatic retry on preemption/failure

Free (no cost multiplier):

```python
@app.function(
    retries=modal.Retries(initial_delay=0.0, max_retries=5),
    single_use_containers=True,  # fresh container on each retry
)
def long_job():
    ...
```

Use on: any function >30 min; any function with preemption history.
`single_use_containers=True` avoids stale state leaking across retries.

### `nonpreemptible=True` — guaranteed non-preemption

**3× CPU+Memory cost**, CPU-only (not available for GPU):

```python
@app.function(nonpreemptible=True, memory=196608)  # 192 GB × 3× cost
def cannot_afford_to_lose():
    ...
```

Use only on: jobs that repeatedly fail from preemption AND lack mid-step
checkpointing. Calculate cost first — 192 GB × 3× ≈ $9-12/hr vs $3-4/hr
preemptible.

**Do NOT use on**: GPU functions (unsupported), jobs with working
checkpoint/retry logic, jobs <15 min (preemption is rare for short jobs).

**Budget kill still bypasses this.** `nonpreemptible=True` protects against
Modal capacity reclamation, not workspace-budget SIGKILL. See debugging.md
"Budget Kill" for the full defense stack.

### High-memory scheduling (>64 GB)

Large-memory containers compete for fewer workers. Symptoms:
`"waiting to be scheduled on a CPU worker. Relaxing requirements
(memory=X) may lead to faster scheduling."`

Fixes, in order:
1. Reduce memory if possible.
2. Reduce parallelism (fewer concurrent containers of the same class).
3. Add `modal.Retries(...)` so preempted containers re-queue automatically.

A common anti-pattern: spawning 100 × 80 GB preemptible containers in one
`.map()` — scheduling storm causes constant preemption, none complete
even over 6 hours. Cap concurrent heavy containers to ~10 and use
retries + checkpointing to absorb preemption losses.

## `@modal.exit()` — Graceful Preemption Handler

Fires on **preemption** with a 30-second grace period. Source:
`modal.com/docs/guide/lifecycle-functions`.

```python
@app.cls(...)
class Worker:
    @modal.enter()
    def setup(self):
        self.state = WorkerState(...)

    @modal.exit()
    def on_exit(self):
        emergency_save(self.state, vol=vol)   # dirty-flag-aware, 30s-safe
```

### What `@modal.exit()` does NOT protect

- **Workspace budget kill**: SIGKILL bypasses the 30 s grace.
- **Container OOM**: SIGKILL, no grace.
- **C-extension segfaults**: no Python-level catch.
- **Network partition where Modal marks the container dead before the
  handler fires**: rare but possible.

For all four, the defense is `vol.commit()` checkpoints between steps +
a sentinel file written on successful completion + an orchestrator-side
sweep that demotes stale RUNNING records past a TTL.

### Rules for exit handlers

1. **Never blind-`vol.commit()` in the handler.** 30 s is not enough for
   a multi-GB volume sync; mid-sync SIGKILL risks corruption. Write a
   small marker file atomically, commit it, and return.
2. **Don't rely on `@modal.exit()` for budget kills.** Pair with a budget
   watchdog + admission control (see debugging.md).
3. **Don't add to `nonpreemptible=True` functions.** Won't be preempted;
   budget-kill bypasses anyway. Use heartbeat-only for those.
4. **Test with `modal.experimental.simulate_preemption()`** if available on
   your SDK version. Validates the handler actually fires and writes the
   expected marker.

## Worker State via `modal.Dict` — Canonical Schema

When you need to know what long-running workers are doing *right now*
(across preemption, across detached apps, from outside the container),
write a single canonical dataclass to `modal.Dict`. See debugging.md
"`modal.Dict` for Live Control Plane" for the transport rules
(7-day TTL, run-id namespacing).

Recommended shape:

```python
from dataclasses import dataclass

@dataclass
class WorkerState:
    run_id: str            # orchestrator-assigned, namespaces all keys
    app_id: str            # modal.current_app_id() at write time
    container_id: str      # modal.current_container_id()
    stage: str             # semantic job name
    unit_id: str           # per-input identity for .map(); "main" otherwise
    step: str              # "start" | "step1_done" | ... | "interrupted"
    started_at: float
    last_heartbeat: float  # refreshed on every step emit
    needs_commit: bool     # main loop flips True after writes
    last_commit_at: float  # main loop sets after vol.commit()
    interrupted_at: float | None
    interrupt_artifact: str | None
```

Emit on every step boundary:

```python
def emit_step(state, step: str, **extras):
    state.step = step
    state.last_heartbeat = time.time()
    # 1) stdout — survives without vol.commit(), visible in `modal app logs`
    print(f"[{state.stage}.{state.unit_id}] {step} {extras}", flush=True)
    # 2) live control plane — queryable from outside
    d = modal.Dict.from_name("worker_state", create_if_missing=True)
    d[f"{state.run_id}.{state.stage}.{state.unit_id}"] = state
    # 3) (optional) append-only JSONL on volume for audit trail
```

## INTERRUPTED State Machine

When a job can be preempted mid-run, model INTERRUPTED as a distinct
status alongside SUCCESS / FAILED / RUNNING. The reconciler loop that
joins live app state with worker-written receipts needs explicit branches
for every combination:

| Condition | Action |
|---|---|
| Receipt = INTERRUPTED | Promote to pending, clear current_attempt_id, emit `observed_interrupted` |
| Receipt = RUNNING + app dead + matching interrupt marker | Promote to pending, emit `observed_interrupted` |
| Receipt = RUNNING + app dead + NO marker | Emit `observed_dead_no_marker`; DO NOT refresh heartbeat (avoid creating immortal zombies); age out past TTL |
| Receipt = RUNNING + app alive | Refresh heartbeat, emit `observed_running` |
| Live-app-check returns unknown | Leave RUNNING, re-poll next tick |

### Marker scoping

Interrupt markers MUST be filtered by `app_id` on read and deleted by
`run_id` on write-success. Stage-wide deletes race with overlapping runs;
global scans pick up stale markers from prior attempts. Two rules:

- **Read**: a marker only promotes the current attempt to pending if its
  `app_id` matches the current attempt's `app_id`.
- **Delete**: on SUCCESS, only delete markers whose `run_id` matches the
  current run. Never delete "all markers for this stage."
