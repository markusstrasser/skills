# Modal — progress survivability: full mechanics + patterns

> Moved verbatim from modal/SKILL.md (2026-07-06, progressive disclosure). SKILL.md keeps
> the rule one-liners; this file carries the copy-paste patterns: `@modal.exit` class
> pattern, dirty-flag emergency save, `.SUCCESS` sentinels, mid-step checkpoint loop,
> tee-to-volume. Genomics-load-bearing — update HERE and keep the inline rule list in sync.

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
