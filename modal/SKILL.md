---
name: modal
description: "Use when: Modal deploy/run/debug, GPU/resource config, `from modal import`. v1 API gotchas. NOT generic cloud (/bash only)."
---

# Modal (operate on the pinned 1.x with CLI/venv parity)

Use this skill for Modal as an operational system, not just an SDK reference.
Start from the question, choose the truth surface, then reason about failure mode.

Shared status contract:
`references/status-reconciliation.md`

## Version baseline (genomics, as of 2026-10)

- The pin lives in genomics `pyproject.toml` and `uv.lock` (1.6.1 since 2026-10-06, `b209b73be`); read it there, not from this file. Align the shell CLI with `uv tool install 'modal[api-proxy-support]==<pin>' --force` (keep the proxy extra).
- Parity check: `modal --version` must equal `uv run python3 -m modal --version`, and `uv run python3 scripts/modal_version_parity.py` must pass. A split reopens C4.
- 1.5+ CLI JSON keys differ from 1.4.x: use the repo normalizer, never raw `.get("App ID")` / `.get("app_id")`.
- `genomics-data` is a v1 volume, so the Volumes v2 grep speedups do not apply.
- Dated platform notes, the historical 1.5.2 baseline and the 1.5.1/1.5.2 feature-adoption tables: `references/changelog.md`.

## Workflow

1. State the operational question.
2. Pick the primary truth surface before opening logs.
3. Join by identity: `stage`, `run_id`, `attempt_id`, `sample_id`.
4. If surfaces disagree, name the mismatch class.
5. Only then choose the repair action.

## Truth Surface By Question

"Is it running?" splits into three liveness planes, and the obvious check is wrong on each (full wording: `references/status-reconciliation.md`):

- Is a STAGE executing on Modal now? -> live app state, read `task_count`/ephemeral, not `is_running` (a deployed infra app shows `is_running: true` at `task_count: 0`).
- Is the local DRIVER alive? -> local `ps` on the driver subprocess, not Modal: a local driver's planning/volume-crawl/repin phase runs on the host before any app is dispatched.
- Is it ADVANCING or hung? -> the driver's progress log (`backing off`, `N/M probed`), not CPU% or a frozen log: rate-limit backoff (`VolumeListFiles`) mimics a deadlock for tens of seconds.
- `Did the worker finish?` -> immutable receipt / terminal artifact
- `Why did it fail?` -> container logs, app logs, stderr tails, worker receipt error
- `Can I trust the output?` -> volume artifact plus checksum/validation, not app state
- `What did this cost?` -> billing rows joined by tags. In genomics `stage-telemetry`, `billing_actual` and `planning_cost_projection` are separate; if billing is unavailable, never substitute the projection or call the attempt `$0`.

Do not answer a live-state question from a volume file.
Do not answer a billing question from app state.
Do not answer driver/orchestrator liveness from Modal app state; an empty Modal app list does NOT mean nothing is running.
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

## GPU Choice

- Inference: L4 if the model fits <24GB, L40S for 24-48GB (best cost/perf), T4 if <16GB. >48GB or SM80 flash-attn: A100-80GB. H100 high-perf training, H200 memory-bound, B200 flagship.
- **Never A10G** (same VRAM as L4, 50% more); `gpu=["L4", "A10G"]` only as an availability fallback.
- Multi-GPU: `gpu="H100:8"`. Fallback: `gpu=["H100", "A100-80GB"]`.
- Put a two-layer check (nvidia-smi + framework device count) at the top of every GPU function so split-brain CUDA fails at launch, not after hours of CPU fallback.
- Before pricing a run or picking a GPU, read `references/gpu.md` ($/hr table, specs, split-brain CUDA fix).

## v1 API Renames (old -> new; full table: `references/migration.md`, read when touching pre-1.0 code)

`modal.Stub` -> `modal.App`; `modal.Mount`/`mount=` REMOVED -> `Image.add_local_python_source()`; `modal.gpu.H100()` -> `gpu="H100"`; `@modal.build` -> `Image.run_function()` or Volumes; `modal.web_endpoint` -> `modal.fastapi_endpoint`; `.lookup()` -> `.from_name()` + `.hydrate()`; `allow_concurrent_inputs=N` -> `@modal.concurrent(max_inputs=N)`; `concurrency_limit`/`keep_warm` -> `max_containers`/`min_containers`/`scaledown_window`.

- automounting is off; local packages are not included unless you add them
- CLI flags go before the script path: `modal run --detach script.py`
- lifecycle hooks use `@modal.enter()` / `@modal.exit()`
- `modal app logs` needs `--follow` on v1.4+

## Preemption, Retries & Budget

- Stage >30 min or ever preempted: `retries=modal.Retries(initial_delay=0.0, max_retries=5)` + `single_use_containers=True` (free); the default detached retry is once.
- Chunk size is the preemption-loss budget: ~30 min per `.map()` chunk; never a per-step `timeout=` on a monolithic all-or-nothing step.
- `nonpreemptible=True`: 3x CPU+memory, CPU-only, not death-proof (infra events, budget kill, OOM, `app stop`); only for short critical stages that cannot checkpoint.
- "Waiting to be scheduled ... relaxing requirements" also fires at the budget cap: run `modal billing report --for today` before blaming capacity.
- `modal app stop` on a stage a driver awaits deadlocks the driver.
- Budget kill SIGKILLs every container: no grace, no `@modal.exit()`, no retry. Only committed volume state survives.
- Spend-cap freeze: endpoints 404 "workspace disabled" or 503 with zero bootlogs, `app list` empty, new containers never schedule, running ones later die with `ConflictError: workspace ... is disabled`. Check the workspace first; poll loops must fail fast on the "disabled" body.
- Live Usage >85% = no long jobs. Billing lags (same-day `modal billing report` is not final; book actuals at next-day close); pair polling with launch admission (a `modal.Dict` halt flag).
- When sizing retries/chunks, considering `nonpreemptible`, or a stage won't schedule, read `references/preemption.md`. When querying spend, writing a budget watchdog, or after a budget kill, read `references/budget-and-spend.md`. `modal.Dict` control plane and the identity API: `references/debugging.md`.

## Progress Survivability

A long step that commits only at its end loses everything on interruption; design for survival from the start. When writing `@modal.exit`, `.SUCCESS` sentinels, mid-step checkpoints or tee-to-volume, read [references/checkpointing.md](references/checkpointing.md) for the copy-paste patterns.

- Ephemeral disk (`/tmp`, `/root`, container-local) is wiped on preemption, budget kill, OOM, and between retries of the same call.
- `vol.commit()` persists only what is already on the mount: copy from `/tmp` to the mount FIRST, then commit.
- `@modal.exit()` needs `@app.cls`, not `@app.function` (convert `.map()` workers to a class); it fires on preemption (30s grace), NOT budget kill; use dirty-flag logic, since an unconditional `vol.commit()` can overrun the grace window.
- Resume trusts only artifact + `.SUCCESS` sentinel pairs: write the sentinel AFTER `vol.commit()` returns, then commit again; size-only checks pass truncated files.
- Subprocess steps >30 min: copy partial artifacts to the volume in the heartbeat loop with a ONCE-only flag (a naive loop recopies 21GB every heartbeat).
- Set `PYTHONUNBUFFERED=1` on every subprocess env, and tee partial stdout to a volume-visible log.
- Timeout = max expected + 50%; a timeout equal to the runtime kills at the finish line.
- `print()` at step boundaries in `.map()` workers; volume commits land only at unit completion.

## Failure-Mode Cheatsheet

- Import error or crash loop after detach -> live app state first; `retries=0` does not stop container crash retries; a poller keyed on "app exists" sees flat `running` through a crash-loop (C6): judge by logs, fresh `task_count`, retry count.
- Receipt says running forever -> likely `stale_receipt`; compare its timestamp to live logs/progress.
- Detached app alive for hours -> app age is not progress; check latest worker logs and receipt heartbeat.
- `Runner interrupted due to worker preemption` / `Worker disappeared` -> unhealthy until fresh progress after the restart.
- Old results visible after stop -> outputs need run identity; volume state is not liveness.
- Large sync or probe slow/heavy -> Modal SDK reads, not repeated CLI subprocesses.
- Download/write looks complete but is wrong -> validate integrity, not size; atomic completion markers.
- Unexpected GPU bill -> check `max_containers`, tags, and `.starmap()` fanout first.

## Durable Gotchas (when debugging odd platform behavior, read `references/gotchas.md` for wording and incidents)

- `volume.commit()` is required; no relative paths (cwd is `/root`); no SQLite on volumes.
- Long runs: `modal run --detach` + `.spawn()` + a function-written completion marker. A non-detached run or an awaited `.remote()` dies with the laptop or agent.
- Always cap `max_containers` (`.starmap()` is the easiest runaway cost); `cpu` means physical cores.
- Mutating CLI verbs need `-y` and an exit-code check (non-tty aborts silently); `container stop` is asynchronous.
- Warm zombie containers serve old code after a redeploy: `modal app stop -y NAME`, then deploy.
- Never fan out recursive volume lists while stages write (workspace-wide VolumeListFiles quota, C1); volume RPCs have no per-call timeout (C2).
- Use JSON output for tooling and the SDK, not CLI subprocesses, for volume probes.
- Before restarting orchestrated work, dedup with `modal app list --json`.
- Never wrap `modal run --detach` in a local timeout (the build continues server-side); `modal volume get` is silent under captured output, so watch file growth.
- `container stop` returning 0 is not death: poll `container list` until the ID is gone and assert the answering container ID changed.
- Heavy cold start (model download): `modal deploy` once, then call via `Cls.from_name` from a separate client so local timeouts don't kill it. Zombie tell: traceback line numbers differ from the local file.
- Compiled CUDA stacks on CUDA base images: `pip_install`, not `uv_pip_install`.
- File watchdogs can read a previous container's retry leftovers: verify by timestamp, not presence.
- `vol.reload()`: one best-effort reload, never a reload loop under parallel workers (C9). Wrap control-loop volume RPCs in a tick watchdog (C2). Give each concurrent launch its own staging dir or flock it (C11, `[Errno 17] File exists`).
- `@app.server` (flash) URLs are `*.modal.direct`, not `*.modal.run`; parse `modal deploy` output only with `COLUMNS=300` (it wraps at 80 in non-tty).
- vLLM: bake `VLLM_USE_FLASHINFER_SAMPLER=0` into the image `.env()` (flashinfer JIT can take >18 min inside a readiness window). Qwen3-Next/Qwen3.6/GDN-Mamba hybrids with a repeated shared long prefix: pass `--no-enable-prefix-caching` via `SERVE_EXTRA_ARGS` (symptom: one HTTP 500 `EngineCore`, then empty 204s; only a redeploy recovers).
- vLLM compile cache is keyed per engine-config hash: changing `max_inputs`/quant/spec forces a full recompile (~11-18 min). GPU-snapshot restore measured ~93s trigger→ready for a 27B, not the vendor 5-12s.

## MANDATORY: Test Before Deploying

1. **Local syntax check**: `python -c "import ast; ast.parse(open('script.py').read())"`
2. **Image probe**: `image.build(app)` -- catches all build failures, no GPU cost
3. **Smoke test**: Small data subset (< 5 min)
4. **Interactive debug**: `modal shell script.py` or Sandbox-as-REPL (see `references/debugging.md`)
5. **Full run**: Only after 1-3 pass

## Reference Docs (in `references/`; read when the trigger fits)

- Writing code against an API you have not used this session: `functions.md`, `images.md` (base images, deps, build caching, eStargz), `volumes.md` (commits, concurrent access, v1 vs v2, uploads), `scaling.md` (.map/.starmap, concurrency, limits), `secrets.md`, `web-endpoints.md`, `scheduled-jobs.md`, `sandboxes.md`, `resources.md` (CPU, memory, disk, billing), `examples.md` (end-to-end code).
- Bumping Modal or porting old code: `migration.md`, `changelog.md`. CLI, Sandbox-as-REPL, image probing: `debugging.md`.
- Reporting status or spend: `status-reconciliation.md`, `attribution.md` (question/source/status/spend pattern).
- A failure matches a dated incident: `known-issues.md`. Marker PDF→Markdown on Modal: `marker-pdf-extraction.md`. Full original index: `index.md`.

**Hit a fresh Modal gotcha or a defect in THIS skill?** Log it so the next deploy inherits the fix:
`~/Projects/skills/hooks/append-skill-memento.sh modal '<one-line issue>'`.

## Known Issues

For matching failures, read [incident history](references/known-issues.md). The memento helper appends there.
