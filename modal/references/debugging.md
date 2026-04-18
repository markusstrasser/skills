<!-- Reference file for modal skill. Loaded on demand. -->

# Debugging & Development

## CLI Commands

```bash
# Interactive container shell
modal shell scripts/script.py

# Shell into a RUNNING sandbox
modal shell sb-12345abcdef

# Container logs (v1.4+: defaults to last 100 entries, NOT streaming)
modal container logs <container-id>                    # last 100 entries
modal container logs <container-id> --follow           # stream (old default)
modal container logs <container-id> --all              # complete log history
modal container logs <container-id> --search "error"   # filter by text
modal container logs <container-id> --source stderr    # stdout/stderr/system

# App logs (v1.4+: rich filtering, defaults to last 100 entries)
modal app logs <app-name>                              # last 100 entries
modal app logs <app-name> --follow                     # stream (old default)
modal app logs <app-name> --tail 1000                  # last N entries
modal app logs <app-name> --since 4h                   # time-based
modal app logs <app-name> --since 2026-03-15 --until 2026-03-20
modal app logs <app-name> --search "OOM"               # text search
modal app logs <app-name> --source stderr              # stdout/stderr/system
modal app logs <app-name> --function my_fn             # filter by function
modal app logs <app-name> --function-call fc-abc123    # filter by call
modal app logs <app-name> --container ct-abc123        # filter by container
modal app logs <app-name> --show-function-id           # prefix lines with origin

# Volume inspection
modal volume ls my-volume
modal volume get my-volume remote.txt local.txt

# Container listing
modal container list                                   # all containers
modal container list --app-id ap-abc123                # filter by app (v1.4+)

# Dashboard
modal dashboard
modal dashboard apps
modal dashboard volumes

# Changelog query (v1.3.5+ -- useful for discovering features)
modal changelog --since=1.2
modal changelog --since=2025-12-01
modal changelog --newer
```

## Eager Image Building (v1.2+)

Build an image without running any function -- catches all apt/pip/conda failures early:
```python
app = modal.App.lookup("probe", create_if_missing=True)
image = modal.Image.debian_slim().apt_install("samtools").pip_install("pysam")

with modal.enable_output():
    image.build(app)  # Blocks until build completes. Fails fast on bad deps.
```

## Sandbox-as-REPL Workflow

Use Sandboxes programmatically to validate images before deploying. This replaces the
write-deploy-fail-fix cycle with probe-verify-deploy:
```python
import modal

app = modal.App.lookup("probe", create_if_missing=True)
image = modal.Image.debian_slim().apt_install("samtools", "bcftools")

# Step 1: Build image (catches apt/pip failures -- no GPU cost)
with modal.enable_output():
    image.build(app)

# Step 2: Spawn a sandbox and test interactively
sb = modal.Sandbox.create(image=image, app=app, timeout=300)

# Verify tools exist and work
p = sb.exec("samtools", "--version")
print(p.stdout.read())  # Works? Great. Doesn't? Fix image and rebuild.

# Check library linkage (the Aldy problem -- C shared libs)
p = sb.exec("python3", "-c", "import pysam; print(pysam.__version__)")
print(p.stdout.read(), p.stderr.read())

# Check volume paths (mount read-only for safety)
vol = modal.Volume.from_name("my-data")
sb2 = modal.Sandbox.create(image=image, app=app, volumes={"/data": vol.read_only()})
p = sb2.exec("ls", "/data/input/")
print(p.stdout.read())

sb.terminate()
sb2.terminate()
```

## Named Sandboxes (v1.1.1+ -- persistent dev environments)
```python
# Create a named sandbox that persists across script runs
sb = modal.Sandbox.create("python3", "-m", "http.server", name="dev-server", app=app)

# Later, reconnect to it
sb = modal.Sandbox.from_name("dev-server")
p = sb.exec("curl", "http://localhost:8000/")
```

## Sandbox Snapshots (v1.3.4+)
```python
# Snapshot a directory to persist across sandbox lifetimes
snapshot = sb.snapshot_directory("/project")
sb.terminate()

# Mount the snapshot into a new sandbox
sb2 = modal.Sandbox.create(app=app)
sb2.mount_image("/project", snapshot)

# Full filesystem snapshot -> reusable image
snapshot_image = sb.snapshot_filesystem()
```

## Sandbox Lifecycle (v1.3.4+)
```python
sb.detach()                   # Keep sandbox running after script exits
sb.terminate(wait=True)       # Block until sandbox fully stopped
sb.reload_volumes()           # Refresh mounted volumes (v1.0.5+)
```

## Programmatic Output Control
```python
with modal.enable_output():
    # Shows logs, object creation status, map progress
    with app.run():
        fn.remote()

# Suppress progress bars
from modal import output_manager
output_manager.set_quiet_mode(True)
output_manager.set_timestamps(True)
```

## Subprocess Visibility

Subprocess with `stdout=subprocess.PIPE` buffers ALL output until exit when
there's no TTY. For a multi-hour subprocess, `process.communicate(timeout=60)`
returns empty `TimeoutExpired.stdout` for hours — you see the container
image banner then nothing until the process ends.

Always set `env["PYTHONUNBUFFERED"] = "1"` on subprocess invocations. For
multi-hour jobs, also tee partial stdout to a volume-visible log file so
you can inspect progress via `modal volume get` without waiting for exit:

```python
import os, subprocess
env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"
process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, env=env, text=True)
log_path = volume_results_dir / f"subprocess_{step}.log"
with open(log_path, "w") as fh:
    for line in process.stdout:   # line-buffered iteration
        fh.write(line); fh.flush()
        print(line, end="")        # also to modal app logs
```

## Timeout Sizing

Set `timeout=` to **1.5× observed max**, never equal. A subprocess killed
at the timeout boundary with its artifact built but not yet flushed to
volume loses everything on retry — no checkpoint was saved because the
subprocess didn't exit cleanly. Better to pay the occasional idle tail
than lose the whole run to a Modal-side kill.

Also note: `@app.function(timeout=N)` caps **each invocation**, regardless
of `--detach`. The timeout is per-input; when the container hits it, Modal
cancels with `Task's current input hit its timeout of <N>s`. `--detach`
keeps the *app* alive across local disconnects but cannot extend the
per-input timeout. Size for projected runtime at full scale, not observed
probe runtime.

## CLI disconnect on `modal run --detach` is a false alarm

`modal run --detach` CLI exits 1 on gRPC stream termination
(`ConnectionError: Deadline exceeded`, `StreamTerminatedError: Connection lost`,
`[Errno 8] nodename nor servname provided`) but the **detached app
survives on Modal's backend**. Task-complete notifications in scripted
launchers will show `status=failed` while the app runs fine.

Always verify via `modal app list` before treating as a real failure.
If the app shows `ephemeral` with >0 tasks, it's alive.

## `.map()` Fanout Invisibility

When using `.map()` or `.starmap()` to run N containers in parallel, each
container writes its own logs — but `vol.commit()` in each unit only fires
at unit completion. Until the FIRST unit finishes, you have zero visibility
into what any container is doing. `modal app list` shows "10 tasks" but
can't distinguish "all in step 1" from "all stuck."

Defense: add explicit `print()` statements at step transitions. These go
to stdout and are captured by `modal app logs` without waiting for any
volume commit. Volume-backed JSONL loggers are not enough for `.map()`
workloads — you need stdout on every step change.

## Safe Stop Rule

**Never `modal app stop` without checking stage status first.** If the
receipt says RUNNING, the container is doing work — stopping it loses
progress.

`.map()` apps show `tasks=0` on the parent app even while child containers
are active. The parent dispatches and exits; children run independently.
`tasks=0` does NOT mean idle for `.map()` apps — check the child function
calls or the live worker state before stopping.

## SDK Probe Before Building Against New Primitives

Modal's SDK moves fast. Before building a feature that relies on a
specific primitive, verify it exists on the installed version:

```bash
uv run python3 - <<'PY'
import modal, inspect
print("modal version:", modal.__version__)

d = modal.Dict.from_name("sdk_probe", create_if_missing=True)
d["probe"] = {"v": 1}
print("Dict ok; sig:", inspect.signature(modal.Dict.from_name))

try:
    from modal import billing
    print("billing:", dir(billing))
    print("workspace_billing_report sig:",
          inspect.signature(billing.workspace_billing_report))
except (ImportError, AttributeError) as e:
    print("BILLING NOT ON THIS SDK:", e)

from modal.exception import ResourceExhaustedError, InputCancellation
print("ResourceExhaustedError, InputCancellation: ok")

try:
    from modal.experimental import simulate_preemption
    print("simulate_preemption: ok")
except ImportError as e:
    print("simulate_preemption not available:", e)
PY
```

If any primitive is missing, revise the plan against the actual SDK
surface. Don't code against the docs alone — published docs often lead
or lag the installed version by multiple releases.

## `modal.Dict` for Live Control Plane

`modal.Dict` persists across app restarts with a 7-day TTL on named Dicts.
It's queryable from outside the app and survives app death — the right
primitive for "what's the worker doing right now?" and "is there a halt
flag?" state.

```python
dict_ = modal.Dict.from_name("orchestrator_state", create_if_missing=True)
try:
    halted = dict_.get("budget_halt")
except (modal.exception.AuthError, ConnectionError, KeyError):
    halted = None   # fall back; log the failure, don't crash
```

Use for: live worker state, cross-app halt flags, cross-app counters.
Don't use for: large artifacts (>KB scale), append-only provenance (use
JSONL on a volume), anything that must survive workspace auth revocation
(wrap reads in try/except).

**Run-id namespacing is mandatory.** Without `run_id` prefixes on every
key, a prior failed run's entries (7-day TTL) get misread as current
progress on re-run. Shape: `{run_id}.{stage}.{unit_id}` at minimum.

**Duplicate-truth rule**: `modal.Dict` is the LIVE channel (low-latency,
queryable from outside). Volume JSONL is the AUDIT/PROVENANCE channel
(append-only, permanent). One truth per axis — don't write heartbeat
JSON files on the volume when `modal.Dict` already holds live state.

**`modal.Queue` does NOT persist across app restarts** — cleaned up at
app completion. Don't use it for checkpointing or control flow that
needs to survive a crash.

## Budget Kill — The Nuclear Failure Mode

When workspace spend hits the account limit, ALL running containers die
instantly. No grace period, no `@modal.exit()` handler, no checkpoint
write. Everything on ephemeral disk (`/tmp`, `/root/...`) is lost.

Defense layers (all required for long-running jobs):

1. `vol.commit()` between every logical step
2. Mid-step checkpoints during >30-min subprocesses — copy large artifacts
   to the volume, commit, set a once-only flag to prevent repeat copies
3. Subprocess stdout teed to a volume-visible log file (see Subprocess
   Visibility above) so partial state is diagnosable
4. A **budget watchdog** sidecar: poll `modal.billing.workspace_billing_report()`
   every 60 s, set a `modal.Dict("orchestrator_state")["budget_halt"]` flag
   at ~90% of cap. The billing API typically lags 5–15 min, so the watchdog
   must fire well before the cap.
5. **Forecast-based admission control** in whatever schedules launches:
   `remaining_budget >= projected_remaining(active_apps) + projected(new_launch) + safety_margin`.
   Static-percent thresholds alone don't model concurrent burn.
6. Monitor Live Usage on the dashboard BEFORE launching — >90% = don't
   launch long jobs. Static rules can't replace a human look.

**gRPC-side catch**: the container may be SIGKILLed without ever raising
an in-container exception; the local launcher often sees a gRPC disconnect
or auth failure instead. Wrap `modal run`, `app.deploy()`, and `.map()` calls
at the launcher layer:

```python
try:
    ...
except (grpc.RpcError, modal.exception.AuthError,
        modal.exception.ConnectionError) as e:
    if _looks_like_budget_kill(e):
        _set_state("budget_halt", reason=str(e))
        raise BudgetHaltError(...) from e
    raise
```

**In-container catch (empirical gate)**: `ResourceExhaustedError` exists
in `modal.exception`, but whether it fires on workspace-budget kill is
SDK-dependent and historically UNVERIFIED. Don't build in-container
emergency-save paths without an empirical probe first ($1 test workspace,
observe actual signal).
