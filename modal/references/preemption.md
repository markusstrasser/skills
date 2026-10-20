# Modal — preemption, retries and scheduling

> Moved verbatim from modal/SKILL.md (2026-10-21, context-cost reduction). SKILL.md keeps the one-line rules.

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

### Testing preemption handling
Do not assume `modal.experimental.simulate_preemption` exists; probe the active
SDK before building around it. Historical 1.4.1 probe: importing it from
`modal.experimental` failed. To force-test `@modal.exit()` handling, use
`modal app stop <app-id>` mid-work — imperfect proxy because it fires the
graceful-shutdown path but does NOT validate budget-kill behavior (which
SIGKILLs with no handler run).
