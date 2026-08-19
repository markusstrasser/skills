---
name: modal
description: "Use when: Modal deploy/run/debug, GPU/resource config, `from modal import`. v1 API gotchas. NOT generic cloud (/bash only)."
---

# Modal (operate on 1.5.x with CLI/venv parity)

Use this skill for Modal as an operational system, not just an SDK reference.
Start from the question, choose the truth surface, then reason about failure mode.

Shared status contract:
`references/status-reconciliation.md`

## Baseline: Modal 1.5.2, parity required

**Shell-global CLI** is a `uv tool` install (`~/.local/bin/modal` →
`uv tool install 'modal==1.5.2'`). That is what **arc-agi** uses: it does
**not** pin Modal in `pyproject.toml`; scripts are launched with `modal run`
(the tool env), and local `import modal` is guarded so project-venv
`--help` / tests still work.

**Genomics** pins the project venv: `pyproject.toml` has
`modal>=1.5.1,<1.6`, `uv.lock` resolves `modal==1.5.2`, and
`uv run python3 scripts/modal_version_parity.py` must pass. Bumping the
global tool without refreshing genomics (or vice versa) reopens C4.

Verify both planes:

```bash
modal --version
# genomics only:
uv run python3 -m modal --version
uv run python3 scripts/modal_version_parity.py
```

Modal 1.5.x normalizes CLI JSON keys differently from the old 1.4.x output.
Consumers should use the repo's normalizer where one exists and should still
avoid raw `.get("App ID")` / `.get("app_id")` parsing.

## Modal 1.5.2 Features (2026-07-10)

Ops/DX patch — not an architecture power-up. Prefer unfinished **1.5.1**
adoption (billing → named images) over chasing these.

| Feature | Use when | Do not use for |
|---|---|---|
| `modal.Workspace.settings.list()` / `.set()` · `modal workspace settings …` | Read/set workspace-level knobs. As of 1.5.2 the live keys are `default-environment` and `image-builder-version` only (manager/owner). | Budget/spend caps, admission control, or stage readiness — **budget is not exposed here**. |
| `modal.types` | Type-annotate wrappers around Modal return dataclasses. | Constructing these types in user code (they are API return shapes). |
| `Function.with_options(..., routing_region=…)` | Invoke-time regional routing. Best fit for **arc-agi** GPU train/farm/serve paths that already use `with_options`. | Substituting for capacity/budget diagnosis; still check spend vs cap first. |
| `modal container stop --graceful` | Drain: stop fetching new inputs, finish in-flight Function inputs (not cancel+reschedule). Useful for long train steps or served endpoints. | App-wide halt (`modal app stop`); budget kill; Sandbox stop. Graceful is Function/Server containers only. |
| `modal container logs` includes startup | Debug cold-start / import crash-loops (vLLM serve, detached import failures). | Liveness or completion — still join receipts / `task_count`. |
| `Workspace.members.list()` role `user` → `member` | Match UI/docs for lowest-privilege role when auditing membership. | Pipeline readiness. Update any code that compared role == `"user"`. |
| `Sandbox.reload_volumes(timeout=…)` (default 55s) | Blocking reload until volumes are current; raises `modal.exception.TimeoutError` on stall. Narrow win for probe/canary sandboxes. | Stage hot path — that remains `vol.reload()` (still C2/C9; no per-call timeout on Volume.reload). |

**Arc-agi lean-in (optional):** `--graceful` drain, startup logs, `routing_region` on existing `with_options` call sites.
**Genomics lean-in (optional):** settings only if you need image-builder/default-env automation; Sandbox reload timeout on probe paths. Do not treat settings as budget API.

## Modal 1.5.1 Features: How Genomics Should Use Them

Verified against `modal changelog --since 1.4.9` on 2026-06-30. Still the
adoption priority over 1.5.2.

| Feature | Use in genomics | Do not use for |
|---|---|---|
| `modal.Workspace.billing.report()` / `modal.Environment.billing.report()` and `modal billing report --show-resources` | Stage telemetry and budget admission. Join rows by `run_id`, `stage`, `attempt_id`; keep CPU, memory, and GPU resource breakdown separate from planning projections. Environment-scoped reports are useful if genomics gets its own Modal environment. | Completion, liveness, or substituting missing billing with `$0`. |
| Named Images: `Image.publish()`, `Image.from_name()` | Canonical stage images (`genomics/base`, `genomics/deepvariant`, etc.) so many one-stage Apps stop rebuilding divergent images. Pin names/tags in stage metadata and fail loud on missing image. | Implicit build fallback. `Image.from_name()` is a lookup, not a builder. |
| `Image.from_id(...).publish()` | Promote a known-good build ID after a probe/canary without rebuilding. Useful for overnight stage-image rollouts. | Re-publishing unverified images or hiding changed dependencies behind the same tag. |
| Version-pinned `Function.from_name(..., version=...)` / `Cls.from_name(..., version=...)` | Deployed helper functions or a future long-lived controller can call a consistent deployed version during one run. Store the version in the run manifest. | Ephemeral one-stage `just dispatch` apps unless they are first deployed and versioned. |
| `@app.server()` / `modal.Server` | Low-latency HTTP diagnostics or a future status/control endpoint with proxy-token auth. Could serve read-only progress/status without cold-starting a CLI. | Batch WGS stages. Stages remain `@app.function`/`@app.cls` jobs with receipts. |
| `modal endpoint` | Production LLM inference endpoints, if a future interpretation model needs a served endpoint. | The pipeline controller itself; do not add an endpoint just to avoid receipts. |
| Proxy tokens + `modal curl` | Authenticated checks against future Modal Servers/Endpoints without manually handling headers. Keep tokens out of logs. | Stage identity or sample authorization inside batch jobs. |
| Sandbox `outbound_domain_allowlist=[...]` | Network-restricted probes, external-tool canaries, and testsample/fake-DAG sandboxes where only declared domains should be reachable. | Normal WGS stages that need broad DB/reference access unless the allowlist is complete. |
| `sandbox.filesystem.watch()` | Fast feedback from sandbox-based experiments: watch log/result files without polling whole directories. | Volume receipt completion; still write terminal receipts and payload summaries. |
| Sandbox connect tokens scoped by `port=` | Safer interactive debugging of a known service port in a Sandbox. | Long-running production control-plane auth. |
| `modal app rollback --strategy rolling|recreate` | Deployed diagnostic/status services. Prefer `recreate` only when stale containers are unsafe. | Ephemeral per-stage apps; stop/reconcile via run identity instead. |
| `modal workspace members` | Operator/audit check for who can see or mutate the workspace. | Pipeline readiness or sample completion. |

Adoption order for this repo:

1. **Billing first:** migrate `stage-telemetry` internals to the 1.5.1
   Workspace/Environment billing APIs or `modal billing report --show-resources`,
   then keep projections visibly separate.
2. **Named images second:** publish canonical, tagged images for high-churn stage
   families and make stage specs reference tags explicitly.
3. **Version-pinned functions third:** only for deployed helper/controller
   surfaces where a run needs one stable function version.
4. **Servers/endpoints only if needed:** useful for a read-only status plane, not
   for replacing batch-stage receipts.

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

**The frozen-workspace TELL (spend-cap disable):** every endpoint returns 404 with a "workspace disabled" body, `modal app list` renders an EMPTY table, and deploys/API calls fail — indistinguishable from a slow cold boot to a naive HTTP poll, so poll loops burn their full timeout on it (2026-07-11 arc-agi: 2700s poll against a capped workspace read as "boot never ready"). Poll loops must check the 404 body for "disabled" and fail fast + distinctly (reference: arc-agi `modal_serve_lib.sh::msl_poll_ready` exit 2). Same-day `billing report` lag (gotcha 23) means the freeze usually arrives BEFORE the dashboard shows the spend that caused it.

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
For current 1.5.1 work, prefer the new Workspace/Environment billing API or its
CLI frontend. The CLI check is:

```bash
modal billing report --for today --json --show-resources --tag-names run_id,stage,attempt_id
modal environment billing report <environment> --for today --json --show-resources --tag-names run_id,stage,attempt_id
```

The Python-side replacement for the old workspace API is:
`modal.Workspace().billing.report(...)` or
`modal.Environment.from_name(...).billing.report(...)` after probing the active
SDK shape. These reports include resource-level cost breakdowns (CPU, memory,
specific GPU types), which stage telemetry should preserve.

Deprecated historical surface: `modal.billing.workspace_billing_report(...)`.
Do not build new code on it.

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
17. **Budget kill ≠ preemption** -- preemption triggers `retries`; budget kill SIGKILLs everything with no grace period, no exit handler, no retry. Only committed volume state survives.
18. **`.map()` containers are invisible until they commit** -- PipelineLogger JSONL writes go to volume but commits happen at trait end. 10 containers running for 6h with 0 commits = 0 visibility into what they're doing. Add explicit `print()` at step transitions for stdout trace.
19. **Artifact file watchdogs are fooled by retry leftovers** -- if a subprocess times out with a 21GB file on ephemeral disk, the retry's new container starts fresh. If the watchdog runs before the retry subprocess touches the dir, it sees `annotation_mb=21793.4` but that's the OLD file from a DIFFERENT container (Modal cleans `/tmp` between retries... usually). Verify via timestamps, not presence.
20. **Mutating CLI verbs prompt `[y/N]` and ABORT in non-tty** -- `container stop`, `app stop`, `volume delete`... under nohup/scripts print "no interactive terminal detected" and exit non-zero; an unchecked exit reads as success while NOTHING happened. Scripts: always `-y`/`--yes` AND check the exit code. (2026-07-11 arc-agi: "1s snapshot restores" were the never-stopped container still answering -- the measurement, not just the teardown, was silently wrong.)
21. **`container stop` is asynchronous** -- returning 0 ≠ container dead. Anything keyed on "stopped" (restore timing, port reuse) must poll `container list` until the ID is gone, and assert the answering container ID CHANGED afterward. Reference implementation: arc-agi `scripts/modal_serve_lib.sh::msl_container_stop_verified`.
22. **`@app.server` (flash) endpoints live on `*.modal.direct`, not `*.modal.run`** -- and `modal deploy` stdout wraps at terminal width (80 in non-tty), truncating URLs mid-domain. Parse deploy output only with `COLUMNS=300` set, match BOTH domains, or skip parsing: `@modal.web_server` URLs are deterministic (`https://<workspace>--<app>-<fn>.modal.run`).
23. **A non-detached `modal run` dies WITH your laptop** -- system sleep / network blip drops the client's gRPC heartbeat and the server CANCELS the remote function ("Stopping app - local client disconnected"), killing an otherwise-healthy GPU run. ANY `modal run` whose remote wall exceeds minutes-you'd-bet-on-no-sleep MUST use `--detach` (client death then can't kill it; monitor via `modal app logs` + volume checkpoints, and read a dead local log tail as CLIENT state, not job state). Nohup/bgrun does NOT protect against this -- the client process survives but its network doesn't. (2026-08-19 arc-agi: 47-min training run killed at step 350/1330, ~$3.5, by a morning laptop sleep; the error message itself names the fix.)
24. **Workspace-disabled (spend cap) is a SILENT scheduling starvation, not an error** -- reads (`app list`, `volume ls`) keep working, deploys "succeed", but new containers never schedule: web endpoints 503 forever with ZERO bootlogs, and running containers die later at retry boundaries with `ConflictError: workspace ... is disabled`. A long 503 streak with no new bootlog on a boot-instrumented serve = check the workspace FIRST, before any boot-failure theory. (2026-08-19 arc-agi: two probe reruns + one training run mis-diagnosed twice before the ConflictError named it.)
25. **An AWAITED `.remote()` is coupled to the local client even under `modal run --detach` -- use `.spawn()` + `--detach` + a volume completion-marker for anything long.** Measured 2026-08-19 (arc-agi): a training task was server-cancelled in the SAME MINUTE its local client died of a DNS blip, at step 1290/1330 (~97%, --detach was set). Causal arrow undetermined at available resolution (client-death-cancels-call vs infra-preemption-then-reconnect-DNS-fail both fit) -- but the defensive form is identical either way, and its two halves are each independently required: `.spawn()` WITHOUT `--detach` dies the moment the entrypoint returns ("Stopping app - local entrypoint completed", measured same day), and `--detach` without spawn leaves the call awaited by a mortal client. Completion signal = an artifact the FUNCTION writes at its end (manifest/marker json + vol.commit), polled by the launcher's watcher; per-block/step partial commits bound the loss of any mid-run kill. Reference implementations: arc-agi scripts/modal_merge_requant.py + modal_g1_gate.py (spawn modes, death-capture, partials).

23. **Same-day `modal billing report` lags** -- identical totals hours apart while serves burned in between. Never book same-day $ actuals as final; pull at next-day close (arc-agi `just modal-cost` reads this source).
24. **GPU-memory-snapshot restore: vendor "5-12s" is the internal `/wake_up` only** -- full trigger→ready for a 27B (sleep level 1, ~51 GiB CPU-side snapshot) measured ~93s (still 5-10x over a compile-cache cold boot). And the vLLM compile cache (volume-mounted `~/.cache/vllm`) is keyed per engine-config hash: changing `max_inputs`/quant/spec = new hash = full recompile (~660-1100s); same-config redeploys ~200-330s.

25. **flashinfer sampler JIT-compiles (ninja) during vLLM warmup -- >18min on a cold container, silently eating any readiness poll.** vLLM 0.24 defaults to the flashinfer top-k/top-p sampler; when the wheel lacks AOT kernels for the GPU arch it ninja-builds them at first sample, so `/health` never comes up inside a 1200s window and teardown SIGINTs mid-compile (arc-agi student-regret probe 2026-07-11 -- looked like a hung serve, was a compiler). Fix: bake `VLLM_USE_FLASHINFER_SAMPLER=0` into the image `.env()` (torch fallback is negligible at small batch). If flashinfer perf ever matters, bake the JIT cache at image-build time on a GPU builder -- never pay a kernel compile inside a readiness window.

26. **Prefix caching crashes the EngineCore on Mamba/GDN-hybrid models (Qwen3-Next / Qwen3.6) under repeated-shared-prefix workloads.** Any driver that scores/samples many candidates against the SAME long context (batch-scoring, pass@k over one prompt, `prompt_logprobs` scoring loops) hits this: the FIRST long-prompt request returns HTTP 500 `"EngineCore encountered an issue"`, and every request after it returns empty HTTP 204s for the rest of the container's life (the engine is dead, not just that one call -- redeploying is the only recovery, retries within the same container do nothing). vLLM's hybrid attention block size (528 tokens, aligned to the Mamba page size) plus documented Mamba-Attention-hybrid prefix-cache defects (vLLM issues #40696 "prefix caching completely ineffective for Mamba-hybrid when prompt < block_size", #43587 "prefix caching fails for incremental multimodal requests on Mamba-Attention hybrid (Qwen3.5)", #39809 "Mamba prefix caching + MTP crashes on startup") are the documented root-cause class; arc-agi hit the crash empirically (not from those exact issue numbers -- inferred from the vendor-documented defect CLASS, then confirmed the fix worked) via `experiments/passk_support/likelihood_scorer.py`'s prompt_logprobs scoring grid, 2026-07-17. **Fix: `--no-enable-prefix-caching`** on the `vllm serve` command for any Qwen3-Next/Qwen3.6/other GDN-Mamba-hybrid model whose workload repeats a shared long prefix across many requests -- pass it via `modal_serve_adapter.py`'s existing `SERVE_EXTRA_ARGS` passthrough, never a hand-edit of the adapter. Symptom signature to grep for when diagnosing a "serve went dark mid-grid": first request in a batch returns 500 with `EngineCore`, all subsequent requests return 204 with an empty body.

(Four former items — ephemeral-disk wipe, PYTHONUNBUFFERED, timeout+50%, commit-doesn't-copy — moved up into the Progress Survivability rules; one fact, one home.)

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
  it warm. **Subagent corollary (2026-07-15, elwr double-death):** an AGENT going
  idle/yielding kills its backgrounded `modal run` children the same way — any
  agent-launched run expected >10 min MUST use `modal run --detach` (server-side,
  survives client death) plus per-unit `vol.commit()` checkpoints, so a dead client
  loses at most one unit and the parent can grade from volume artifacts. Two
  launches died to this in one day before the detach; brief templates should cite
  this bullet, not restate it.

**Hit a fresh Modal gotcha or a defect in THIS skill?** Log it so the next deploy inherits the fix:
`~/Projects/skills/hooks/append-skill-memento.sh modal '<one-line issue>'`.

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-07-09] add_local_dir/add_local_python_source copy the WORKING TREE at dispatch, not git HEAD — uncommitted edits ship to containers, and a stage dispatched mid-edit records a code fingerprint that exists in no commit (unreproducible run). Commit before a dispatch wave; "predates the commit" is never the fix boundary — the mount is.**

- **[2026-07-23] Volume mount point (e.g. /data) is itself a SYMLINK in 1.5.x containers; storage layers that reject symlink roots must resolve the one boundary hop at the call site (Path(mount).resolve()) while staying strict beneath — sealed-but-never-invoked shadow apps die on first contact otherwise (genomics kernel G0, 2026-07-23).**

- **[2026-07-23] Modal materializes the function-defining module at /root/<module>.py in-container, NOT at its add_local_dir location — __file__-relative resource lookup silently breaks; resolve shipped resources against the fixed add_local_dir remote path constant (genomics kernel G0, 2026-07-23).**

- **[2026-07-23] An app module committed "define only; do not deploy/invoke" is a dead-on-arrival landmine: without an explicit image (debian_slim + add_local_dir + PYTHONPATH env) the container cannot import its own function module (automount off). First invoke must be a real remote-call smoke, not a green codec test (genomics kernel G0, 2026-07-23).**

- **[2026-07-24] bitsandbytes 4-bit (BitsAndBytesConfig load_in_4bit=True/NF4) silently no-ops on Qwen3.6-27B's GDN/Mamba hybrid param mass -- near-full-precision load despite the config, no error/warning. Verified: config.json shows 48/64 layers are linear-attention (GDN) with mamba_ssm_dtype forced float32 independent of quantization config; vendor docs describe a custom fine-grained FP8 (block-size 128) scheme for this architecture, not generic bitsandbytes coverage. Symptom: OOM at near-identical GPU memory (~79GB/80GB H100) before AND after wiring 4-bit quant -- zero quant/bitsandbytes/nf4 log lines either way. arc-agi cert-gate Stage-1a launch, 2026-07-24, $0.30 spent diagnosing across 3 attempts (research/2026-07-24-certgate-launch-prep.md). Fix for this model class: plain bf16 (no bitsandbytes) on a bigger-VRAM GPU (H200 141GB), or the vendor's own official FP8 checkpoint/quantization pipeline -- not a naive BitsAndBytesConfig wrap.**

- **[2026-07-24] EXTENDS #27: the actual root cause of the Qwen3.6/GDN-hybrid OOM ladder (verified by reading the v4 H200 traceback directly) is NOT quantization or VRAM size -- it's transformers falling back to torch_chunk_gated_delta_rule, the EAGER/pure-PyTorch O(chunk^2)-materializing implementation of the GDN chunk delta rule, used whenever flash-linear-attention + causal-conv1d kernels are absent from the image. bf16-vs-4bit and H100-vs-H200 all OOM'd at ~full-GPU-memory because bigger VRAM just let the same eager blow-up climb higher (79/80GB H100, 139.79/141GB H200) before failing -- three attempts that LOOKED like three different bugs were one bug. Fix: pip_install flash-linear-attention + causal-conv1d (compiled CUDA exts, install after torch on a -devel base image) so transformers takes the kernelized path. arc-agi cert-gate, 2026-07-24, 4 attempts / $0.43 total before this finding (research/2026-07-24-certgate-launch-prep.md).**

- **[2026-07-24] EXTENDS #27, build-toolchain gotcha #3: causal-conv1d's SOURCE COMPILE on a -devel CUDA base fails even with a matched CUDA toolkit -- pip's ISOLATED build env can resolve clang++ at a garbage version ('0.0.0'), failing torch.utils.cpp_extension's compiler-version check before any real compilation starts (root cause: build-isolation not seeing the real toolchain/CXX visibly, not a missing package). FIX: skip source-compile entirely -- causal-conv1d (Dao-AILab) publishes prebuilt wheels keyed by torch+CUDA+cpython+cxx11abi at github.com/Dao-AILab/causal-conv1d/releases (query the raw JSON API for an exact match, do not trust a summarized fetch -- one summarization run claimed a torch2.13 match that did not exist). If the container's auto-resolved (unpinned) torch version has no matching wheel (2026-07-24: unpinned pip_install('torch') resolved 2.13.0, but causal-conv1d's newest wheel matrix tops out at torch2.10), PIN torch to the version the wheel matrix covers (verify the pinned version+CUDA combo is a real download.pytorch.org/whl/cuXXX wheel first) rather than trying to make the newest torch compile -- this also closes the unpinned-torch root-instability class from gotcha 2026-07-24#1 one layer up. flash-linear-attention itself is pure-Triton, never needs any of this. arc-agi cert-gate, 3 build-only failures / $0 total before landing on the wheel-based fix (research/2026-07-24-certgate-launch-prep.md).**

- **[2026-07-24] EXTENDS #27, gotcha #4: on Hopper-class GPUs (H100/H200) the fla (flash-linear-attention) stack for Mamba/GDN-hybrid models needs THREE packages, not two -- flash-linear-attention + causal-conv1d + tilelang. fla's own chunk_bwd_dqkwg (fla/ops/common/chunk_o.py:678) fail-loud-guards against a known Triton>=3.4.0-on-Hopper correctness bug (fla#640: produces WRONG gradients, not a crash) and refuses to run the backward pass without tilelang installed -- error message prints the exact fix ('Please install tilelang: pip install tilelang'). Symptom signature: model loads fine, a full KERNELIZED FORWARD pass succeeds (proof the fla+causal-conv1d kernel install already worked), then the FIRST backward pass raises RuntimeError citing fla#640. This is progress-shaped, not a repeat of the earlier eager-fallback OOM (gotcha #2) -- forward already ran on the real kernels; only backward needs the extra package. Fix: add 'tilelang' as a normal pip package alongside flash-linear-attention (both pure add, no compile). arc-agi cert-gate Stage-1a, 2026-07-24, attempt 5-v4 reached backward pass before hitting this (furthest of 8 total attempts/build-cycles that day; research/2026-07-24-certgate-launch-prep.md).**
