# Modal — durable gotchas and field-tested failure patterns

> Moved verbatim from modal/SKILL.md (2026-10-21, context-cost reduction). SKILL.md keeps a short list of the most-hit items. Numbering below is the original (it contains duplicate numbers 23-25; cite items by text, not number).

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
