---
name: modal
description: "Use when: Modal deploy/run/debug, GPU/resource config, `from modal import`. v1 API gotchas. NOT generic cloud (/bash only)."
effort: low
---

# Modal (operate on 1.5.x with CLI/venv parity)

Use this skill for Modal as an operational system, not just an SDK reference.
Start from the question, choose the truth surface, then reason about failure mode.

Shared status contract:
`references/status-reconciliation.md`

## Genomics baseline: Modal 1.5.1, parity required

For `/Users/alien/Projects/genomics`, the current baseline is Modal 1.5.1:
`pyproject.toml` pins `modal>=1.5.1,<1.6`, `uv.lock` resolves `modal==1.5.1`,
`modal --version` and `uv run python3 -m modal --version` both report
`modal client version: 1.5.1`, and
`uv run python3 scripts/modal_version_parity.py` passes.

The old pre-1.5 freeze was superseded. The rule that survived the 1.4/1.5
split incident is stricter and still current: keep the **shell-global
`modal` and the project venv on the SAME version**. A `--json` key-schema
difference across CLI planes silently breaks any poller written against the
other. In this repo, verify:

```bash
modal --version
uv run python3 -m modal --version
uv run python3 scripts/modal_version_parity.py
```

Modal 1.5.x normalizes CLI JSON keys differently from the old 1.4.x output.
Consumers should use the repo's normalizer where one exists and should still
avoid raw `.get("App ID")` / `.get("app_id")` parsing.

## Workflow

1. State the operational question.
2. Pick the primary truth surface before opening logs.
3. Join by identity: `stage`, `run_id`, `attempt_id`, `sample_id`.
4. If surfaces disagree, name the mismatch class.
5. Only then choose the repair action.

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
- `What did this cost?` -> billing rows joined by tags

Do not answer a live-state question from a volume file.
Do not answer a billing question from app state.
Do not answer driver/orchestrator liveness from Modal app state — join with the
local process plane (`ps`); an empty Modal app list does NOT mean nothing is running.
Do not read `is_running` as "doing work" — join with `task_count`/ephemeral.
Do not merge these into one synthetic status.

## First Response Pattern

Report work in this shape:

- `question`
- `primary source`
- `supporting sources`
- `mismatch class` if any
- `next action`

If you cannot name the source artifact, the question is still open.

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

Usual checks:

- `modal billing report --json --tag-names ...`
- app tags: `question_id`, `run_id`, `stage`
- per-stage billing aggregation

See `references/attribution.md` for the reporting template.

## Field-tested failure patterns (multi-stage DAG, Modal 1.4/1.5)

Fundamental, recurring Modal-platform failure modes distilled from an 8-week
many-stage DAG (IDs kept for cross-reference; full operational catalog incl. the
non-Modal orchestration classes lives in the consuming repo). These are platform
truths, not one project's bug list — they reappear on any large stage graph.

- **C1 — VolumeListFiles quota is WORKSPACE-wide.** A full-DAG or recursive volume
  crawl fans out per-stage list RPCs that compete with live stage *writers* for one
  shared list quota and **throttle-hang with no backoff line** — the crawl just stops
  advancing (looks like a deadlock). Never fan out recursive volume lists while stage
  apps are writing; scope to a single directory, or wait for writers to drain.
- **C2 — one volume RPC can block a control loop forever.** `VolumeListFiles` /
  `vol.reload()` has no built-in per-call timeout; a single stalled RPC freezes a
  reconcile/poll tick at 0% CPU with zero output. Wrap control-loop RPCs in a tick
  watchdog that aborts a stalled call. A frozen log ≠ a hung process (rate-limit
  backoff mimics a deadlock for tens of seconds).
- **C4 — a CLI version split silently breaks pollers.** `--json` key shape differs
  across Modal versions and CLI planes. If the shell-global `modal` and the project
  venv resolve to **different** versions, a poller written against one reads keys
  ABSENT against the other — for minutes, while the app really runs. Pin ONE version
  across both planes; in genomics assert `modal --version` ==
  `uv run python3 -m modal --version` and run `scripts/modal_version_parity.py`.
- **C6 — an in-app retry crash-loop is invisible to an external control plane.**
  `@app.function(retries=N)` retries *inside* one app; an external DB/poller that keys
  on "app exists" sees a flat `running` for the entire crash-loop (observed: 69 min
  before manual triage). Liveness = app logs / fresh `task_count` / retry count — never
  app existence alone.
- **C9 — `vol.reload()` races under concurrency.** Reload in a tight loop can swallow a
  `ConflictError` and never complete, or hand a worker a stale file handle (FASTA/index)
  → mid-stage crash. Use a best-effort single reload; don't reload-loop under parallel
  workers.
- **C11 — concurrent launches race on shared local staging paths.** Two app launches
  staging into the same host path collide with `[Errno 17] File exists`. Give each
  concurrent launch an isolated staging dir (or flock the path).

## Launch Discipline

Before any significant run, state:

`containers * hours * $/hr = $expected`

Minimum checklist:

1. Name the question and expected artifact.
2. Set `max_containers`.
3. Set `timeout` as the cost circuit breaker.
4. Attach tags: `question_id`, `run_id`, `stage`.
5. Decide how progress will become visible during the run.

## GPU Decision Tree

| GPU | VRAM | $/hr | Use when |
|-----|------|------|----------|
| T4 | 16GB | ~$0.59 | Model fits <16GB |
| L4 | 24GB | ~$0.73 | Model fits <24GB. **Never A10G** (same VRAM, 50% more) |
| L40S | 48GB | ~$1.65 | Best cost/perf. 24-48GB models |
| A100-80GB | 80GB | ~$3.73 | Need >48GB or SM80 flash-attn |
| H100 | 80GB | ~$3.95 | High-perf training |
| H200 | 141GB | ~$4.54 | Memory-bound workloads |
| B200 | 192GB | ~$6.25 | Flagship, sparse FP4 |

Multi-GPU: `gpu="H100:8"`. Fallback: `gpu=["H100", "A100-80GB"]`.

**Rules:** Inference -> prefer L4/L40S. Use `gpu=["L4", "A10G"]` for availability fallback only. See `references/gpu.md` for full specs.

## Critical Breaking Changes

```python
modal.Stub("name")           ->  modal.App("name")
modal.Mount(...)             ->  REMOVED -- use Image.add_local_python_source()
mount= parameter             ->  REMOVED everywhere
modal.gpu.H100() objects     ->  gpu="H100" strings
@modal.build decorator       ->  Image.run_function() or Volumes
modal.web_endpoint           ->  modal.fastapi_endpoint
.lookup()                    ->  .from_name() + .hydrate()
allow_concurrent_inputs=N    ->  @modal.concurrent(max_inputs=N)
concurrency_limit/keep_warm  ->  max_containers/min_containers/scaledown_window
```

Also remember:

- automounting is off; local packages are not included unless you add them
- CLI flags go before the script path: `modal run --detach script.py`
- lifecycle hooks use `@modal.enter()` / `@modal.exit()`
- `modal app logs` needs `--follow` on v1.4+

See `references/migration.md` for the full migration table.

## Preemption & Retry Resilience

Modal can preempt containers at any time to reclaim capacity. Default detached behavior: auto-retry once. Not enough for long stages.

### `modal.Retries` (free, no cost multiplier)
```python
@app.function(
    retries=modal.Retries(initial_delay=0.0, max_retries=5),
    single_use_containers=True,  # fresh container per retry, avoids stale state
)
```
Add to: any stage >30min, any stage that has been preempted before. Cost: zero — just re-queues. `single_use_containers=True` prevents state leaks between retries.

### Chunk size IS your preemption-loss budget
For any `.map()`/`.starmap()` fanout, chunk size bounds what a single preemption / budget-kill / timeout destroys — lose a chunk, redo a chunk. Aim ~30 min runtime per chunk (60×30min beats 6×5h: a Modal infra event costs you <$1 instead of ~$10). **Never put a per-step `timeout=` on a monolithic all-or-nothing step** — a single subprocess that buffers internally (`samtools sort`, a `bwa-mem2 mem | view` pipe) whose `.SUCCESS` only writes at the very end is worthless under interruption; split it into sub-checkpoints or fan it out over data partitions instead. For memory-floored algorithms (fixed 25-30GB index), shrink chunks AND cap `.map(max_concurrent=N)` rather than leaning on chunk size alone to ease scheduling. Full sizing + scale-extrapolation guidance: `references/scaling.md`.

### `nonpreemptible=True` (3x CPU+Memory cost, CPU-only)
```python
@app.function(nonpreemptible=True, memory=196608)
```
Stops Modal from *voluntarily* preempting the container for capacity reclaim. **3x multiplier on CPU and Memory billing.** Not available for GPU functions. Use for: stages that repeatedly fail from preemption AND lack mid-step checkpointing. Calculate cost impact first.

**It is not death-proof.** `nonpreemptible=True` still gets SIGKILLed by: Modal infrastructure events (worker-node decommission), budget kill, OOM, and `modal app stop`. Symptom in logs when an infra event hits a nonpreemptible container: `Received a cancellation signal while processing input` → `Runner has been shutting down for too long (grace period: 30 seconds)`. So don't pay 3× expecting bulletproof execution — the resilient combo is still small chunks (bounded loss) + `Retries(max_retries=5)` + frequent `vol.commit()` + `.SUCCESS` sentinels. Reserve `nonpreemptible` for short (<30min) critical-path stages where 3× is bounded AND mid-step checkpointing is impossible. (Evidence: 2026-05-27 — a Modal infra event killed all 6 nonpreemptible 5h×48GB workers mid-run; paid 3× for protection that didn't apply.)

### High-memory scheduling constraints
Containers requesting >64GB RAM compete for fewer workers. Symptoms: `"waiting to be scheduled on a CPU worker. Relaxing requirements (memory=X) may lead to faster scheduling"`.

**⚠ The SAME message also fires when the ACCOUNT BUDGET CAP is hit** — Modal halts scheduling, so queued/preempted work reads "waiting to be scheduled... acquiring more capacity" *identically* to real capacity scarcity. **Before concluding capacity, check spend vs the cap (`modal billing report --for today`).** Tells it's budget-cap not capacity: (a) MANY stages mass-stall at once; (b) zero reschedule for hours even off-peak (real capacity frees off-peak; an exhausted cap never does); (c) spend at/near the limit. Budget-cap is operator-fixable (raise it → scheduling resumes instantly); capacity is wait-only — mis-reading it wastes the whole window on a stall only the operator can clear (2026-06-23: a 4 h stall on 3×32GiB stages was the budget cap, surfaced only when the operator said "budget is back"). A driver/orchestrator that waits on a stage's terminal receipt also DEADLOCKS if you `modal app stop` the stage (no FAILED receipt is written) → recovery = stop the stuck apps + kill & relaunch the driver.

Mitigations (real capacity):
- Reduce parallelism (don't request 200×80GB simultaneously)
- Add `retries` so preempted containers re-queue automatically
- Reduce memory if workload permits
- Schedule large-memory jobs when cluster is less busy (off-peak)

### Budget kills
When account spend hits the limit, ALL running containers die instantly — no graceful shutdown, no checkpoint write, no `@modal.exit()` handler. The only defense is frequent `vol.commit()` between steps AND committing partial work during long steps.

Evidence: SBayesRC 80GB×200 parallel containers couldn't schedule. Pangenie 192GB preempted 3+ times across 3 days. Budget limit killed all 3 active apps simultaneously mid-run — 6h of SBayesRC compute, 4h of sven_sv annotation (21.8GB artifact on ephemeral disk), 5h of pangenie genotyping — all lost because ephemeral disk is wiped and the commit-at-step-boundary model saves nothing mid-step (2026-04-13).

## Progress Survivability

The commit-at-step-boundary model is a trap for long subprocess steps (>30min). If a step takes 4h and commits only at the end, you lose 4h on any interruption. Design for survivability from the start.

### Rule: ephemeral disk is ephemeral
Anything written to `/tmp/`, `/root/`, or container-local paths is lost on:
- preemption (auto-retry restarts from scratch unless state is on volume)
- budget kill (instant SIGKILL, no grace period)
- container crash / OOM

Subprocess work directories (e.g. `/tmp/sven_workdir`) are NOT preserved across retries in the same function call — each retry starts with a fresh container and fresh `/tmp`.

### Rule: `vol.commit()` only persists what's already on volume
`vol.commit()` syncs the volume mount to durable storage. It doesn't copy from ephemeral disk. To save a 21GB artifact from `/tmp/`, you must `shutil.copy` it to the volume mount first, THEN `vol.commit()`.

### Rule: `@modal.exit()` requires `@app.cls`, not `@app.function`
`@modal.exit()` is a lifecycle-method decorator on class methods. A plain `@app.function` does not accept it. To get 30s-grace preemption handling on a `.map()` worker, convert the function to a class:

```python
@app.cls(...)
class Runner:
    state: WorkerState | None = None

    @modal.enter()
    def _prepare(self) -> None:
        self.state = None  # reset per container, not per input

    @modal.method()
    def run(self, unit_id: str) -> dict:
        self.state = WorkerState.from_context(stage="foo", unit_id=unit_id)
        try:
            result = do_work(self.state)
        except BaseException:
            emit_step(self.state, "failed", ...)
            raise
        # ... commit, mark success, emit "committed"
        self.state = None  # clear so idle-between-inputs exit handler no-ops
        return result

    @modal.exit()
    def _on_exit(self) -> None:
        if self.state is None or self.state.step in TERMINAL_STEPS:
            return
        emergency_save(self.state)

# Caller: runner = Runner(); runner.run.map(inputs, ...)
```

`@modal.exit()` fires on preemption, NOT on budget kill. 30s grace before SIGKILL. Inside the handler, do NOT `vol.commit()` unconditionally — a large pending diff may overrun the grace window mid-sync and produce a partial durable snapshot. Use dirty-flag logic:

```python
def emergency_save(state):
    write_json_atomic(f"_INTERRUPTED.{state.unit_id}.json", state.to_dict())
    write_worker_state(state)  # update Dict live plane
    if state.needs_commit:  # main loop set this True after new writes
        vol.commit()
```

`@modal.enter()` runs once per container start, not per `.map()` input — containers reuse across inputs. Assignment `self.state = None` in a `finally`-style path at end of `run()` prevents the exit handler from acting on stale state during idle time between inputs.

### Checkpoint durability: `.SUCCESS` sentinels
Size-only checks on resume are unsafe for large artifacts — a SIGTERM mid-write can leave a truncated file that passes `min_bytes=1024`. Write a sidecar sentinel AFTER `vol.commit()` returns; resume trusts only artifacts with their sentinel:

```python
# After work + commit:
vol.commit()
write_json_atomic(f"{artifact_path}.SUCCESS", {"completed_at": time.time()})
vol.commit()  # persist the sentinel itself

# On resume:
def verify_checkpoint(path, require_success_sentinel=True):
    if not Path(path).exists(): return False
    if require_success_sentinel and not Path(f"{path}.SUCCESS").exists(): return False
    return True
```

The sentinel is atomic relative to the artifact because `vol.commit()` completes before it's written — a partial write never has a sentinel, so resume falls through to rebuild.

### Mid-step checkpoint pattern
For subprocess steps >30min, copy partial artifacts to volume during the heartbeat loop:

```python
mid_step_checkpointed = False
while True:
    try:
        stdout, _ = process.communicate(timeout=60)
        break
    except subprocess.TimeoutExpired:
        # Check if large artifact exists, commit ONCE
        if not mid_step_checkpointed:
            sources = [p for p in artifact_sources if p.exists()]
            total_bytes = sum(p.stat().st_size for p in sources if p.is_file())
            if total_bytes > 1_000_000_000:  # >1GB worth saving
                try:
                    shutil.copytree(artifact_dir, volume_checkpoint_dir, dirs_exist_ok=True)
                    vol.commit()
                    mid_step_checkpointed = True  # once-only flag
                except Exception:
                    mid_step_checkpointed = True  # don't retry on error
```

Critical: **ONCE-only flag**. A naive implementation copies 21GB on every 60s heartbeat, blocking the heartbeat thread and burning disk bandwidth.

### Rule: subprocess stdout is fully buffered without PYTHONUNBUFFERED
Python subprocess with `stdout=PIPE` and no TTY buffers ALL output until exit. `process.communicate(timeout=60)` returns empty `TimeoutExpired.stdout` until the subprocess flushes. For multi-hour subprocesses, you see nothing. Set `env["PYTHONUNBUFFERED"] = "1"` on subprocess invocation.

### Rule: tee subprocess output to volume
Even with PYTHONUNBUFFERED, partial stdout is only available via `TimeoutExpired.stdout` during heartbeats. Write it to a volume-visible log file so it survives the container:
```python
subprocess_log = volume_results_dir / f"subprocess_{step}.log"
fh = open(subprocess_log, "w")
# ... in heartbeat loop:
if partial_stdout:
    fh.write(partial_stdout + "\n")
    fh.flush()
```

### Rule: timeout = max expected + 50%, not max expected
A timeout equal to the actual runtime kills the subprocess at the finish line. Sven annotation took 4h; timeout was 4h; killed at 4h+0 with artifact built but subprocess not yet exited, no checkpoint saved, retry starts from scratch. Budget 50% headroom.

### Rule: `.map()` containers are invisible without per-trait logging
A `.map()` fanout over N traits runs N containers. Each has its own PipelineLogger writing to volume. But the volume commit only happens at trait completion. Until the first trait finishes, you have zero visibility into what any container is doing. Add stdout `print()` at step boundaries so `modal app logs` shows step transitions, not just "Starting..."

### Live control plane: `modal.Dict` for per-worker state
`modal.Dict.from_name(name, create_if_missing=True)` gives a durable key-value store: writes persist across app restarts with a 7-day TTL (TTL resets on any read or write).  `modal.Queue` does NOT persist — cleaned up at app completion; don't use it for checkpointing.

Use for: live per-worker progress state, orchestrator control flags (budget_halt), cross-app counters. Don't use for: large artifacts (KB-scale), append-only provenance (use JSONL on volume).

**Namespace mandatory.** With a 7-day TTL, a key like `f"sbayesrc.{trait_id}"` collides with stale state from a prior failed run — the reconciler would see "already completed" when nothing has run this session. Prefix every live key with a run_id: `f"{run_id}.{stage}.{unit_id}"`. Set `WORKER_RUN_ID` env var once per launch so every container inherits the same scope.

```python
d = modal.Dict.from_name("worker_state", create_if_missing=True)
key = f"{run_id}.{stage}.{unit_id}"
d[key] = {"step": "mcmc_start", "last_heartbeat": time.time(), ...}
```

Wrap reads in `try/except (modal.exception.AuthError, ConnectionError, KeyError)` — Dict is the live control plane, NOT the source of truth. JSONL on volume is the audit plane. One truth per axis; never write the same fact to both.

### Identity API
Do not trust memory for Modal runtime identity helpers; verify against the
current client before adopting a new name. Historical probe on 1.4.1: top-level
`modal.current_container_id` and `modal.current_app_id` did NOT exist and were
not on `modal.functions` either. Known-safe fallbacks from that probe:

- `modal.current_input_id()` — unique per `.map()` input (returns Optional[str], None locally)
- `modal.current_function_call_id()` — app invocation identity
- `os.environ.get("MODAL_TASK_ID", "local")` — Modal-runtime-set container identity env var

### Rule: budget monitoring before launch
Check Modal Live Usage before launching anything significant. >85% = don't launch long jobs. There's no graceful budget-aware degradation; you hit the limit and everything dies.

### Programmatic spend queries
For current 1.5.x work, prefer the CLI surface unless you have live-probed the
Python billing API shape in the active venv:
`modal billing report --for today --json`.

Historical 1.4.1 probe: `modal.billing.workspace_billing_report(*, start:
datetime, end: Optional[datetime] = None, resolution: str = 'd', tag_names:
list[str] | None = None)` returned `list[dict]` with keys `{object_id,
description, environment_name, interval_start, cost (Decimal), tags}`. Treat
that as historical evidence, not a current 1.5.x contract.

Cloud billing APIs typically lag 5-15 min. A 60s watchdog poll + 90% threshold can still miss bursts that cross the cap before the poll. Pair polling (belt) with admission control at launch (suspenders).

### Budget defense: sidecar watchdog + halt flag
The most reliable defense against budget kill is prevention: a separate daemon
that polls a live-probed billing surface (CLI JSON or a verified Python API)
and sets a halt flag in `modal.Dict` which every launch path reads before
dispatching.

```python
# Daemon (local process, not on Modal — it'd be killed by the event it detects):
dict_ = modal.Dict.from_name("orchestrator_state", create_if_missing=True)
if mtd >= threshold_usd:
    dict_["budget_halt"] = {"set_at": time.time(), "reason": "...", "remaining_budget": cap - mtd}

# Launcher (orchestrator):
halt = dict_.get("budget_halt")
if halt:
    raise BudgetHaltError(halt["reason"])  # refuse launch cleanly
```

On launch failure, also inspect the subprocess stderr for `ResourceExhausted` / `quota exceeded` / `workspace budget` / `spend limit`. Do NOT include `auth error` / `unauthenticated` in that signature set — `MODAL_TOKEN_ID` rotation gets misclassified and poisons `orchestrator_state` globally until a human clears it.

## Failure-Mode Cheatsheet

- **Import error or crash loop after detach** -> inspect live app state first; `retries=0` does not stop container crash retries
- **Receipt says running forever** -> likely `stale_receipt`; compare receipt timestamp to live logs/progress
- **Detached app looks alive for hours** -> app age is not progress; check latest worker logs and receipt heartbeat before assuming compute is still happening
- **Logs show `Runner interrupted due to worker preemption` or `Worker disappeared`** -> treat the run as unhealthy until you see fresh progress after the restart
- **Old results still visible after stop** -> outputs need run identity; volume state is not liveness
- **Large sync or probe is slow/heavy** -> use Modal SDK reads, not repeated CLI subprocesses
- **Download or write looks complete but is wrong** -> validate integrity, not just size; use atomic completion markers
- **Unexpected GPU bill** -> check `max_containers`, tags, and `.starmap()` fanout before anything else

## Durable Gotchas

1. **`volume.commit()` required** -- forgetting it still causes silent loss.
2. **No relative paths** -- container cwd is `/root`.
3. **No SQLite on volumes** -- NFS locking is the wrong substrate.
4. **`--detach` + `.spawn()`** -- only the last triggered function survives disconnect.
5. **Detached import failures can crash-loop** -- live app stays up retrying failed imports.
6. **Container crashes retry differently from code exceptions** -- `retries=N` is not the whole story.
7. **Dedup before launching** -- check `modal app list --json` before restarting orchestrated work.
8. **Use JSON output for tooling** -- table output truncates and lies by omission.
9. **Use SDK for volume probes/reads** -- repeated CLI subprocesses are slow and memory-heavy.
10. **`modal run --detach` should not be wrapped in local timeouts** -- build can continue server-side after your client dies.
11. **`modal volume get` is silent with captured output** -- monitor file growth yourself for large transfers.
12. **Validate downloads by integrity, not size**.
13. **`.starmap()` is the easiest way to create runaway cost** -- always cap `max_containers`.
14. **`cpu` means physical cores, not vCPUs**.
15. **`uv_pip_install` on CUDA base images can break ABI/toolchain expectations** -- prefer `pip_install` for compiled CUDA stacks.
16. **App wall-clock age lies by omission** -- a detached app can remain listed long after a worker was preempted or disappeared; always join app state with fresh receipt/progress.
17. **Ephemeral disk is wiped on ANY container exit** -- `/tmp`, `/root`, and work dirs are gone on preemption, budget kill, retry, or crash. If a subprocess builds a 21GB artifact in `/tmp` over 3h, that artifact is lost unless explicitly copied to volume mid-step.
18. **Subprocess stdout is fully buffered without a TTY** -- `subprocess.PIPE` with no `PYTHONUNBUFFERED=1` returns empty `TimeoutExpired.stdout` for multi-hour runs. You see CUDA banner then nothing until exit. Always set `env["PYTHONUNBUFFERED"] = "1"`.
19. **Timeout = max runtime kills at the finish line** -- sven annotation took 4h, timeout was 4h, killed at 4h+0 with artifact complete but subprocess not yet exited. Use 1.5x expected max.
20. **Budget kill ≠ preemption** -- preemption triggers `retries`; budget kill SIGKILLs everything with no grace period, no exit handler, no retry. Only committed volume state survives.
21. **`.map()` containers are invisible until they commit** -- PipelineLogger JSONL writes go to volume but commits happen at trait end. 10 containers running for 6h with 0 commits = 0 visibility into what they're doing. Add explicit `print()` at step transitions for stdout trace.
22. **vol.commit() does not copy from ephemeral disk** -- it syncs the volume mount to durable storage. `shutil.copy` to the volume mount first, then `vol.commit()`. Subprocess output in `/tmp` is NOT saved by a naked `vol.commit()`.
23. **Artifact file watchdogs are fooled by retry leftovers** -- if a subprocess times out with a 21GB file on ephemeral disk, the retry's new container starts fresh. If the watchdog runs before the retry subprocess touches the dir, it sees `annotation_mb=21793.4` but that's the OLD file from a DIFFERENT container (Modal cleans `/tmp` between retries... usually). Verify via timestamps, not presence.

### Testing preemption handling
Do not assume `modal.experimental.simulate_preemption` exists; probe the active
SDK before building around it. Historical 1.4.1 probe: importing it from
`modal.experimental` failed. To force-test `@modal.exit()` handling, use
`modal app stop <app-id>` mid-work — imperfect proxy because it fires the
graceful-shutdown path but does NOT validate budget-kill behavior (which
SIGKILLs with no handler run).

## MANDATORY: Test Before Deploying

1. **Local syntax check**: `python -c "import ast; ast.parse(open('script.py').read())"`
2. **Image probe**: `image.build(app)` -- catches all build failures, no GPU cost
3. **Smoke test**: Small data subset (< 5 min)
4. **Interactive debug**: `modal shell script.py` or Sandbox-as-REPL (see `references/debugging.md`)
5. **Full run**: Only after 1-3 pass

## Reference Docs

Detailed docs in `references/`:
- `migration.md` -- v1.0 breaking changes, v1.1-v1.3 features, v1.4 features/breaking changes
- `debugging.md` -- CLI commands, Sandbox-as-REPL, image probing, output control
- `images.md` -- base images, deps, build caching, eStargz
- `functions.md` -- definition, calling, deployment, parallel execution
- `gpu.md` -- GPU types, multi-GPU, fallbacks
- `volumes.md` -- creation, commits, concurrent access, v1 vs v2, uploads
- `scaling.md` -- autoscaling, .map/.starmap, concurrency, limits
- `secrets.md` -- creation, usage, patterns
- `web-endpoints.md` -- FastAPI, ASGI/WSGI, streaming, auth, custom domains
- `scheduled-jobs.md` -- Period, Cron, timezone, deployment
- `resources.md` -- CPU, memory, disk, billing
- `status-reconciliation.md` -- question -> truth surface -> mismatch class
- `attribution.md` -- question/source/status/spend reporting pattern
- `sandboxes.md` -- creation, exec, snapshots, named sandboxes
- `examples.md` -- end-to-end code examples

## Deploy gotchas (2026-06-10, imagegen)

- **Zombie containers serve old code after redeploy.** A warm container from the
  previous version can keep receiving `Cls.from_name` calls (3 identical stale
  tracebacks across 2 redeploys). Force cutover: `modal app stop -y NAME` then
  `modal deploy`. Diagnose: traceback line numbers ≠ local file's.
- **`modal run` dies with the local process.** A Bash-timeout/SIGKILL on the local
  `modal run` tears down the ephemeral app mid-cold-start. For heavy cold starts
  (model downloads), `modal deploy` once + call via `Cls.from_name` from a separate
  client process — the deployed container survives local timeouts and a retry hits
  it warm.
