---
name: modal
description: "Use when: Modal deploy/run/debug, GPU/resource config, `from modal import`. v1 API gotchas. NOT generic cloud (/bash only)."
---

# Modal (operate on 1.5.x with CLI/venv parity)

Use this skill for Modal as an operational system, not just an SDK reference.
Start from the question, choose the truth surface, then reason about failure mode.

Shared status contract:
`references/status-reconciliation.md`

## Version baseline (genomics, as of 2026-10)

- Genomics requires `modal[api-proxy-support]>=1.5.5,<1.6` and locks 1.5.5. Align the shell CLI with `uv tool install 'modal[api-proxy-support]==1.5.5' --force` (keep the proxy extra).
- Parity check: `modal --version` must equal `uv run python3 -m modal --version`, and `uv run python3 scripts/modal_version_parity.py` must pass. A split reopens C4.
- 1.5.x CLI JSON keys differ from 1.4.x: use the repo normalizer, never raw `.get("App ID")` / `.get("app_id")`.
- `genomics-data` is a v1 volume, so the Volumes v2 grep speedups do not apply.
- Dated platform notes, the historical 1.5.2 baseline and the 1.5.1/1.5.2 feature-adoption tables: `references/changelog.md`.

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

## First Response Pattern

Report work in this shape:

- `question`
- `primary source`
- `supporting sources`
- `mismatch class` if any
- `next action`

If you cannot name the source artifact, the question is still open.

## Common Failure Modes

Mismatch classes (`running_live`, `stale_receipt`, `duplicate_live_app`, `incomplete_attempt`, `local_driver_invisible`, ambiguous-output and detached-spend classes) with their usual checks: `references/status-reconciliation.md`. Field-tested platform patterns C1–C11: `references/gotchas.md`.

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

## Preemption, Retries & Budget (rules; detail in references)

- Default detached behavior auto-retries once, which is not enough for long stages. Any stage >30 min or ever preempted gets `retries=modal.Retries(initial_delay=0.0, max_retries=5)` + `single_use_containers=True` (free).
- Chunk size is the preemption-loss budget: aim ~30 min per `.map()` chunk; never put a per-step `timeout=` on a monolithic all-or-nothing step.
- `nonpreemptible=True` costs 3x CPU+memory, is CPU-only, and is not death-proof (infra events, budget kill, OOM, `app stop` still kill it). Reserve it for short critical stages that cannot checkpoint mid-step.
- "Waiting to be scheduled ... relaxing requirements" also fires when the account budget cap is hit. Check `modal billing report --for today` before concluding capacity. `modal app stop` on a stage a driver awaits deadlocks the driver.
- Budget kill SIGKILLs every container: no grace, no `@modal.exit()`, no retry. Only committed volume state survives.
- Spend-cap freeze: endpoints 404 "workspace disabled", `app list` is empty, new containers never schedule. Poll loops must fail fast on the "disabled" body.
- Check Live Usage before launching (>85% = no long jobs). Billing lags; pair polling with launch admission (a `modal.Dict` halt flag).
- Full detail: `references/preemption.md` (Retries, chunking, nonpreemptible, high-memory scheduling, testing `@modal.exit`), `references/budget-and-spend.md` (budget kills, spend-query CLI/API, watchdog daemon). `modal.Dict` control plane and the identity API: `references/debugging.md`.

## Progress Survivability

The commit-at-step-boundary model is a trap for long subprocess steps (>30min): a 4h step that
commits only at the end loses 4h on any interruption. Design for survivability from the start.
Rule one-liners below; full mechanics and copy-paste patterns (`@modal.exit` class pattern,
dirty-flag emergency save, `.SUCCESS` sentinels, mid-step checkpoint loop, tee-to-volume):
[references/checkpointing.md](references/checkpointing.md).

- **Ephemeral disk is ephemeral** — `/tmp`/`/root`/container-local paths are wiped on preemption, budget kill, OOM, and between retries of the same call.
- **`vol.commit()` only persists what's already on the volume mount** — `shutil.copy` from `/tmp` to the mount FIRST, then commit.
- **`@modal.exit()` requires `@app.cls`, not `@app.function`** — convert `.map()` workers to a class for 30s-grace preemption handling; fires on preemption, NOT budget kill; handler needs dirty-flag logic (an unconditional `vol.commit()` can overrun the grace window mid-sync).
- **Checkpoint durability = `.SUCCESS` sentinels** — size-only resume checks pass truncated files; write the sentinel AFTER `vol.commit()` returns, commit again; resume trusts only artifact+sentinel pairs.
- **Mid-step checkpoint for subprocess steps >30min** — copy partial artifacts to volume in the heartbeat loop with a ONCE-only flag (a naive loop copies 21GB every 60s heartbeat).
- **Subprocess stdout is fully buffered without `PYTHONUNBUFFERED=1`** — multi-hour runs show nothing until exit; set it on every subprocess env.
- **Tee subprocess partial stdout to a volume-visible log** — heartbeat-captured output must survive the container.
- **Timeout = max expected + 50%** — a timeout equal to the actual runtime kills at the finish line (sven: 4h job, 4h timeout, artifact lost, retry from scratch).
- **`.map()` containers are invisible without per-step stdout prints** — volume commits land at unit completion; `print()` at step boundaries so `modal app logs` shows transitions.

## Failure-Mode Cheatsheet

- **Import error or crash loop after detach** -> inspect live app state first; `retries=0` does not stop container crash retries
- **Receipt says running forever** -> likely `stale_receipt`; compare receipt timestamp to live logs/progress
- **Detached app looks alive for hours** -> app age is not progress; check latest worker logs and receipt heartbeat before assuming compute is still happening
- **Logs show `Runner interrupted due to worker preemption` or `Worker disappeared`** -> treat the run as unhealthy until you see fresh progress after the restart
- **Old results still visible after stop** -> outputs need run identity; volume state is not liveness
- **Large sync or probe is slow/heavy** -> use Modal SDK reads, not repeated CLI subprocesses
- **Download or write looks complete but is wrong** -> validate integrity, not just size; use atomic completion markers
- **Unexpected GPU bill** -> check `max_containers`, tags, and `.starmap()` fanout before anything else

## Durable Gotchas (most-hit; full list in `references/gotchas.md`)

- `volume.commit()` is required; no relative paths (cwd is `/root`); no SQLite on volumes.
- Long runs: `modal run --detach` + `.spawn()` + a function-written completion marker. A non-detached run or an awaited `.remote()` dies with the laptop or agent.
- Always cap `max_containers` (`.starmap()` is the easiest runaway cost); `cpu` means physical cores.
- Mutating CLI verbs need `-y` and an exit-code check (non-tty aborts silently); `container stop` is asynchronous.
- Warm zombie containers serve old code after a redeploy: `modal app stop -y NAME`, then deploy.
- Never fan out recursive volume lists while stages write (workspace-wide VolumeListFiles quota, C1); volume RPCs have no per-call timeout (C2).
- Use JSON output for tooling and the SDK, not CLI subprocesses, for volume probes.

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
- `checkpointing.md` -- read when writing `@modal.exit`, `.SUCCESS` sentinels, mid-step checkpoints
- `preemption.md` -- read when sizing retries/chunks, considering `nonpreemptible`, or a stage won't schedule
- `budget-and-spend.md` -- read when querying spend, writing a budget watchdog, or after a budget kill
- `gotchas.md` -- read when debugging any odd platform behavior (durable gotchas, C1–C11, deploy zombies)
- `changelog.md` -- read when bumping Modal, checking a dated platform note, or adopting a 1.5.x feature
- `known-issues.md` -- read when a failure matches a dated incident (memento helper appends here)
- `marker-pdf-extraction.md` -- read when running Marker PDF→Markdown on Modal

**Hit a fresh Modal gotcha or a defect in THIS skill?** Log it so the next deploy inherits the fix:
`~/Projects/skills/hooks/append-skill-memento.sh modal '<one-line issue>'`.

## Known Issues

For matching failures, read [incident history](references/known-issues.md). The memento helper appends there.
