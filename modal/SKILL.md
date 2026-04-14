---
name: modal
description: "Modal serverless Python cloud compute. Use when writing or debugging Modal scripts, deploying to Modal, or choosing GPU/resource configs. Covers v1.0-v1.4.x API (current as of March 2026)."
effort: low
---

# Modal (v1.4.x, March 2026)

Use this skill for Modal as an operational system, not just an SDK reference.
Start from the question, choose the truth surface, then reason about failure mode.

Shared status contract:
`references/status-reconciliation.md`

## Workflow

1. State the operational question.
2. Pick the primary truth surface before opening logs.
3. Join by identity: `stage`, `run_id`, `attempt_id`, `sample_id`.
4. If surfaces disagree, name the mismatch class.
5. Only then choose the repair action.

## Truth Surface By Question

- `Is it running right now?` -> live Modal app state
- `Did the worker finish?` -> immutable receipt / terminal artifact
- `Why did it fail?` -> container logs, app logs, stderr tails, worker receipt error
- `Can I trust the output?` -> volume artifact plus checksum/validation, not app state
- `What did this cost?` -> billing rows joined by tags

Do not answer a live-state question from a volume file.
Do not answer a billing question from app state.
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

Usual checks:

- `modal app list --json`
- app tags
- `modal app logs --follow`
- receipt timestamp vs latest heartbeat/progress
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

### `nonpreemptible=True` (3x CPU+Memory cost, CPU-only)
```python
@app.function(nonpreemptible=True, memory=196608)
```
Guarantees no preemption. **3x multiplier on CPU and Memory billing.** Not available for GPU functions. Use for: stages that repeatedly fail from preemption AND lack mid-step checkpointing. Calculate cost impact first.

### High-memory scheduling constraints
Containers requesting >64GB RAM compete for fewer workers. Symptoms: `"waiting to be scheduled on a CPU worker. Relaxing requirements (memory=X) may lead to faster scheduling"`. Mitigations:
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

### Rule: budget monitoring before launch
Check Modal Live Usage before launching anything significant. >85% = don't launch long jobs. There's no graceful budget-aware degradation; you hit the limit and everything dies.

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
