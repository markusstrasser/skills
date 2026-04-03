---
name: modal
description: "Modal serverless Python cloud compute. Use when writing or debugging Modal scripts, deploying to Modal, or choosing GPU/resource configs. Covers v1.0–v1.4.x API (current as of March 2026)."
effort: low
---

# Modal (v1.4.x, March 2026)

## Critical API Changes (v1.0+)

Things that WILL break old code:

```python
# OLD (pre-1.0)              →  NEW (v1.0+)
modal.Stub("name")           →  modal.App("name")  # Stub raises AttributeError
concurrency_limit=N           →  max_containers=N
keep_warm=N                   →  min_containers=N
container_idle_timeout=N      →  scaledown_window=N
allow_concurrent_inputs=N     →  @modal.concurrent(max_inputs=N)  # decorator
max_inputs=N                  →  single_use_containers=True  # v1.3+, now boolean
Function.web_url              →  Function.get_web_url()
modal.web_endpoint             →  modal.fastapi_endpoint  # clarifies FastAPI dep
modal.Mount(...)              →  REMOVED — use Image.add_local_python_source()
mount= parameter              →  REMOVED everywhere
app.run(show_progress=True)   →  REMOVED
modal.gpu.H100() objects      →  gpu="H100" strings (case-insensitive)
@modal.build decorator        →  Image.run_function() or Volumes
Image.copy_local_dir/file     →  Image.add_local_dir/file (default: runtime mount, copy=True for layer)
.lookup()                     →  .from_name() + .hydrate() for metadata
Custom __init__ on @app.cls   →  modal.parameter() annotations (str/int/bool/bytes only)
.resolve()                    →  REMOVED from Modal objects
Function.spawn (generators)   →  REMOVED — spawn no longer supports generators
FunctionCall.get_gen           →  REMOVED
grpclib.GRPCError              →  modal.Error subtypes (v1.3+)
environment_name= (Sandbox)   →  DEPRECATED — use environment=
namespace= (.from_name)       →  DEPRECATED
```

**Automounting disabled (v1.0+)** — local packages no longer auto-included. Must explicitly add:
```python
image = modal.Image.debian_slim().add_local_python_source("my_module")
# Or sync entire project:
image = modal.Image.debian_slim().uv_sync()
```

**CLI flag ordering** — flags go BEFORE the script path:
```bash
# CORRECT:
uv run modal run --detach scripts/modal_foo.py::run_analysis
# WRONG (silently fails or errors):
uv run modal run scripts/modal_foo.py --detach
```

**Lifecycle hooks** — use decorators, not `__init__`:
```python
@app.cls(gpu="L40S")
class Model:
    @modal.enter()      # replaces __enter__ / __init__
    def setup(self): ...

    @modal.exit()        # 30s grace period before kill
    def cleanup(self): ...

    @modal.method()
    def predict(self, x): ...
```

## New Features (v1.4)

### CLI Log Overhaul (v1.4.0 — BREAKING DEFAULT CHANGE)

**`modal app logs` and `modal container logs` no longer follow (stream) by default.** They now show the most recent 100 entries and exit. You MUST pass `--follow` for the old streaming behavior.

```bash
# Historical logs (new default — shows last 100)
modal app logs my-app
modal container logs ct-abc123

# Stream logs (old default — now requires --follow)
modal app logs my-app --follow
modal container logs ct-abc123 --follow

# Count-based history
modal app logs my-app --tail 1000

# Time-based history
modal app logs my-app --since 4h
modal app logs my-app --since 2026-03-15 --until 2026-03-20

# Filter by source (stdout/stderr/system)
modal app logs my-app --source stderr
modal container logs ct-abc123 --source stdout

# Search within logs
modal app logs my-app --search "error"
modal container logs ct-abc123 --search "OOM"

# App-specific filters (app logs only)
modal app logs my-app --function my_function
modal app logs my-app --function-call fc-abc123
modal app logs my-app --container ct-abc123

# Show origin IDs in each line
modal app logs my-app --show-function-id

# Combine filters
modal app logs my-app --function train --source stderr --search "loss" --tail 500

# Filter container list by app
modal container list --app-id ap-abc123
```

**Note:** Historical log access is subject to plan-level retention limits.

### Sandbox Filesystem API (v1.4.0 beta — replaces Sandbox.open)

New, more reliable file I/O for Sandboxes:

```python
sb = modal.Sandbox.create(app=app, image=image)

# Transfer files between local and sandbox filesystem
sb.filesystem.copy_from_local("local_data.csv", "/work/data.csv")
sb.filesystem.copy_to_local("/work/results.json", "local_results.json")

# Read/write text directly
sb.filesystem.write_text("/work/config.yaml", "key: value\n")
content = sb.filesystem.read_text("/work/output.txt")

# Read/write bytes
sb.filesystem.write_bytes("/work/model.bin", model_bytes)
data = sb.filesystem.read_bytes("/work/model.bin")
```

**Deprecation:** `modal.Sandbox.open()` and `modal.file_io.FileIO` are deprecated. Migrate to `sb.filesystem.*`.

### Deployment Strategies (v1.4.0)

Control what happens during redeploy:

```bash
# Rolling (default) — prioritizes uptime, old containers continue briefly
modal deploy script.py

# Recreate — immediately terminates old containers on deploy
modal deploy --strategy recreate script.py
```

```python
# Programmatic
app.deploy(strategy="recreate")
```

**When to use `recreate`:**
- Development workflows where you need certainty the new version is active
- Apps running at `max_containers` limit (no room for replacement capacity)
- `modal serve` now uses recreate by default during code updates

### Image.from_scratch() (v1.4.0)

Empty image for lightweight Sandbox filesystem mounts:

```python
# Equivalent to Docker's FROM scratch
empty = modal.Image.from_scratch()

# Primarily useful as a lightweight mount
sb = modal.Sandbox.create(app=app)
sb.mount_image(empty)
```

### OIDC Identity Token for Sandboxes (v1.4.0)

```python
sb = modal.Sandbox.create(
    app=app,
    include_oidc_identity_token=True,  # Injects MODAL_IDENTITY_TOKEN env var
)
# Enables OIDC-based auth (e.g., AWS federation) inside sandbox
```

### v1.4.0 Breaking Changes

```python
# .map() exceptions no longer wrapped in UserCodeException
# wrap_returned_exceptions= parameter is deprecated
results = list(fn.map(inputs, return_exceptions=True))
# Exceptions come through as-is, no unwrapping needed

# modal.enable_output() no longer yields a value
with modal.enable_output():  # NOT: with modal.enable_output() as output:
    with app.run():
        fn.remote()

# -m flag now REQUIRED for module path Function references
# modal deploy -m project.app        ← CORRECT
# modal deploy project.app           ← ERROR in v1.4+

# Old autoscaler config removed (keep_warm, concurrency_limit, etc.)
# Use: max_containers, min_containers, scaledown_window

# Function.from_name can't look up Cls methods anymore
# OLD: modal.Function.from_name("app", "MyClass.method")
# NEW: modal.Cls.from_name("app", "MyClass")

# Removed unused namespace parameters from various APIs
```

## New Features (v1.1–v1.3)

### Package Installation with uv (v1.1+, recommended)
```python
# Fast install (up to 50% faster than pip)
image = modal.Image.debian_slim(python_version="3.12").uv_pip_install("torch", "transformers")

# Sync from pyproject.toml + uv.lock
image = modal.Image.debian_slim().uv_sync()
```

### Volume Build Caching (v1.2.2+)
```python
cache_vol = modal.Volume.from_name("pip-cache")
image = modal.Image.debian_slim().run_commands(
    "pip install heavy-package --cache-dir /cache",
    volumes={"/cache": cache_vol}
)
```

### Read-Only Volumes (v1.0.5+)
```python
vol = modal.Volume.from_name("shared-data")
@app.function(volumes={"/data": vol.read_only()})
def reader(): ...
```

### Non-Preemptible CPU (v1.2.3+)
```python
# 3x pricing, but guaranteed no preemption
@app.function(cpu=8, nonpreemptible=True)
def critical_job(): ...
```

### App Tags (v1.2+)
```python
app = modal.App("my-app")
app.set_tags({"team": "ml", "cost_center": "research"})
```

### Object Management API (v1.1.2+)
```python
# New unified API for managing Modal objects
modal.Volume.objects.create("my-vol")
modal.Volume.objects.delete("my-vol")
for vol in modal.Volume.objects.list():
    print(vol.name)
# Also: modal.Secret.objects, modal.Dict.objects, modal.Queue.objects
```

### Dashboard URLs (v1.3.2+)
```python
vol = modal.Volume.from_name("my-vol")
print(vol.get_dashboard_url())  # Works on all Modal objects
```

### Startup Timeout (v1.1.4+)
```python
@app.function(startup_timeout=120)  # separate from execution timeout
def slow_startup(): ...
```

### Named Sandboxes (v1.1.1+)
```python
sb = modal.Sandbox.create("python3", "-m", "http.server", name="dev-server", app=app)
# Later retrieve:
sb = modal.Sandbox.from_name("dev-server")
```

### Billing Report (GA in v1.3.3)
```python
report = modal.billing.workspace_billing_report(interval='daily', include_tags=True)
```

### Secret Update (v1.3.5+)
```python
secret = modal.Secret.from_name("my-secret")
secret.update({"NEW_KEY": "value"})
```

### Async Warnings (v1.3+ — enabled by default)
Modal now warns when blocking APIs are called in async contexts. Disable with:
```python
modal.config.set("async_warnings", False)
```

### Eager Image Building (v1.2+)
```python
app = modal.App.lookup("my-app", create_if_missing=True)
image = modal.Image.debian_slim().pip_install("torch")
image.build(app)  # Build now, blocks until done. Catches failures early.
```

### Python 3.14 Support (v1.3+)
Modal supports Python 3.14 (including free-threaded 3.14t). Python 3.9 dropped.

## GPU Selection (current pricing)

| GPU | VRAM | Use Case | $/hr |
|-----|------|----------|------|
| T4 | 16GB | Cheap inference | ~$0.59 |
| L4 | 24GB | Cost-effective inference | ~$0.73 |
| A10G | 24GB | Medium inference | ~$1.10 |
| L40S | 48GB | Best cost/perf balance | ~$1.65 |
| A100-40GB | 40GB | Training | ~$2.78 |
| A100-80GB | 80GB | Large model training | ~$3.73 |
| H100 | 80GB | High-perf training | ~$3.95 |
| H200 | 141GB | Memory-bound workloads | ~$4.54 |
| B200 | 192GB | Flagship, sparse FP4 | ~$6.25 |

Multi-GPU: `gpu="H100:8"`. Fallback list: `gpu=["H100", "A100-80GB"]`.

## CPU, Memory & Disk Resources

**`cpu` = physical cores, NOT vCPUs.** 1 physical core = 2 vCPUs. So `cpu=8` = 16 vCPUs.

**Soft CPU limit** = request + 16 physical cores. To guarantee sustained throughput, increase `cpu`.

**Ephemeral disk** — fast NVMe scratch (up to 3 TiB). Billed at 20:1 memory ratio (500 GiB disk = 25 GiB memory charge).

**Memory limits** — set hard OOM kill threshold:
```python
@app.function(memory=(4096, 8192))  # (request, limit) in MB
def bounded(): ...
```

**CPU limits** — set burst ceiling:
```python
@app.function(cpu=(2.0, 8.0))  # (request, limit) in physical cores
def bursty(): ...
```

**Resource tiers:**
```python
# Light work (API calls, small data)
@app.function(cpu=2, memory=4096, timeout=600)

# Medium work (data processing)
@app.function(cpu=8, memory=16384, timeout=7200)

# Heavy I/O (large file processing)
@app.function(cpu=16, memory=65536, ephemeral_disk=200_000, timeout=28800)
```

## Volumes

```python
vol = modal.Volume.from_name("my-vol", create_if_missing=True)

@app.function(volumes={"/data": vol})
def process():
    # write files to /data/...
    vol.commit()  # REQUIRED to persist changes
```

### Volumes v2 (high-concurrency, open beta)
```python
vol = modal.Volume.from_name("my-vol", version=2)
# v2: unlimited files, 100s concurrent writers, up to 1 TiB per file
# v1: <500K files, ~5 concurrent writers
```

### CloudBucketMount (S3/R2/GCS)
```python
mount = modal.CloudBucketMount(
    "my-bucket",
    bucket_endpoint_url="https://abc.r2.cloudflarestorage.com",
    secret=modal.Secret.from_name("r2-creds"),
    force_path_style=True,  # v1.2.2+
)
@app.function(volumes={"/bucket": mount})
def use_bucket(): ...
```

### Batch Upload
```python
with vol.batch_upload() as batch:
    batch.put_file("local.txt", "/remote.txt")
    batch.put_directory("/local/dir/", "/remote/dir")
```

## Image Building

```python
# Recommended: uv for speed
image = modal.Image.debian_slim(python_version="3.12").uv_pip_install("torch", "transformers")

# Docker image
image = modal.Image.from_registry("nvidia/cuda:12.4.0-runtime-ubuntu22.04")

# Micromamba (conda packages)
image = modal.Image.micromamba().micromamba_install("samtools", channels=["bioconda"])

# Dockerfile
image = modal.Image.from_dockerfile("Dockerfile")

# Local project sync
image = modal.Image.debian_slim().uv_sync()

# Force rebuild (cache-bust)
image = modal.Image.debian_slim().pip_install("pkg", force_build=True)
# Or: MODAL_FORCE_BUILD=1 modal run ...
```

**Image caching:** Layers cached per method call. Put frequently-changing layers LAST. `run_commands` with volume mounts lets you cache package managers across builds.

**GPU at build time:**
```python
image = modal.Image.debian_slim().pip_install("bitsandbytes", gpu="H100")
```

## Scaling & Concurrency

### Autoscaling Config
```python
@app.function(
    max_containers=100,      # upper limit
    min_containers=2,        # keep warm
    buffer_containers=5,     # pre-warmed buffer
    scaledown_window=60,     # idle seconds before shutdown
)
def my_function(): ...
```

### Input Concurrency
```python
@app.function()
@modal.concurrent(max_inputs=100, target_inputs=80)
def io_bound(input: str):
    # Sync: threads. Async: asyncio tasks.
    ...
```

### Parallel Execution
```python
# .map() for single arg
results = list(process.map(range(100)))

# .starmap() for multiple args
results = list(add.starmap([(1, 2), (3, 4)]))

# With error handling
results = list(fn.map(inputs, return_exceptions=True))
```

### Dynamic Autoscaler Updates (no redeploy)
```python
f = modal.Function.from_name("my-app", "f")
f.update_autoscaler(max_containers=100)
```

### Scaling Limits
- 2,000 pending inputs (not yet assigned)
- 25,000 total inputs (running + pending)
- 1,000 concurrent inputs per `.map()` invocation
- `.spawn()`: up to 1M pending inputs

## Functions

```python
# Basic
@app.function()
def hello(): ...

# Run remotely
result = hello.remote()

# Run locally (testing)
result = hello.local()

# CLI entrypoint with auto arg parsing
@app.local_entrypoint()
def main(name: str, count: int):
    hello.remote()

# Run specific function
# modal run script.py::app.hello
```

### Spawn (background execution)
```python
call = process_job.spawn(data)
result = call.get(timeout=60)
```

### Generators (streaming)
```python
@app.function()
def stream():
    for i in range(10):
        yield i

for val in stream.remote_gen():
    print(val)
```

### Programmatic Execution
```python
with modal.enable_output():
    with app.run():
        result = fn.remote()
```

### Function Stats (v1.3.5+)
```python
stats = fn.get_current_stats()
print(stats.num_running_inputs)
```

## Secrets

```python
# From dashboard/CLI
@app.function(secrets=[modal.Secret.from_name("my-secret")])
def use_secret():
    import os
    val = os.environ["MY_KEY"]

# From .env file
@app.function(secrets=[modal.Secret.from_dotenv()])
def use_dotenv(): ...

# Inline (for local dev)
@app.function(secrets=[modal.Secret.from_dict({"KEY": "val"})])
def inline(): ...
```

## Web Endpoints

```python
# Simple endpoint
@app.function()
@modal.fastapi_endpoint()
def hello():
    return "Hello!"

# Full ASGI app
@app.function()
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def api():
    from fastapi import FastAPI
    web_app = FastAPI()
    @web_app.get("/")
    async def root():
        return {"msg": "hello"}
    return web_app

# Development (live reload): modal serve script.py
# Production (stable URL):   modal deploy script.py
```

Rate limit: 200 req/s default. Request body up to 4 GiB.

## Scheduled Jobs

```python
@app.function(schedule=modal.Cron("0 6 * * *", timezone="America/New_York"))
def morning_job(): ...

@app.function(schedule=modal.Period(hours=6))
def periodic(): ...
```

Deploy to activate: `modal deploy script.py`. Redeploying resets Period timers.

## Sandboxes

```python
sandbox = modal.Sandbox.create(app=app, image=image, timeout=300)
process = sandbox.exec("python", "-c", "print('hello')")
print(process.stdout.read())
sandbox.terminate(wait=True)  # v1.3.4+: wait param
```

**Filesystem API (v1.4.0 beta — preferred over Sandbox.open):**
```python
sb = modal.Sandbox.create(app=app, image=image)

# File transfer between local and sandbox
sb.filesystem.copy_from_local("input.csv", "/work/input.csv")
sb.filesystem.copy_to_local("/work/output.json", "output.json")

# Direct text/bytes read/write
sb.filesystem.write_text("/work/config.ini", "[section]\nkey=value")
content = sb.filesystem.read_text("/work/results.txt")
sb.filesystem.write_bytes("/work/model.bin", model_data)
raw = sb.filesystem.read_bytes("/work/model.bin")
```

**Directory Snapshots (v1.3.4 beta):**
```python
snapshot = sandbox.snapshot_directory("/work")
sandbox2 = modal.Sandbox.create(app=app)
sandbox2.mount_image(snapshot)
```

## Debugging & Development

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

# Changelog query (v1.3.5+ — useful for discovering features)
modal changelog --since=1.2
modal changelog --since=2025-12-01
modal changelog --newer
```

### Eager Image Building (v1.2+)
Build an image without running any function — catches all apt/pip/conda failures early:
```python
app = modal.App.lookup("probe", create_if_missing=True)
image = modal.Image.debian_slim().apt_install("samtools").pip_install("pysam")

with modal.enable_output():
    image.build(app)  # Blocks until build completes. Fails fast on bad deps.
```

### Sandbox-as-REPL Workflow
Use Sandboxes programmatically to validate images before deploying. This replaces the
write-deploy-fail-fix cycle with probe-verify-deploy:
```python
import modal

app = modal.App.lookup("probe", create_if_missing=True)
image = modal.Image.debian_slim().apt_install("samtools", "bcftools")

# Step 1: Build image (catches apt/pip failures — no GPU cost)
with modal.enable_output():
    image.build(app)

# Step 2: Spawn a sandbox and test interactively
sb = modal.Sandbox.create(image=image, app=app, timeout=300)

# Verify tools exist and work
p = sb.exec("samtools", "--version")
print(p.stdout.read())  # Works? Great. Doesn't? Fix image and rebuild.

# Check library linkage (the Aldy problem — C shared libs)
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

### Named Sandboxes (v1.1.1+ — persistent dev environments)
```python
# Create a named sandbox that persists across script runs
sb = modal.Sandbox.create("python3", "-m", "http.server", name="dev-server", app=app)

# Later, reconnect to it
sb = modal.Sandbox.from_name("dev-server")
p = sb.exec("curl", "http://localhost:8000/")
```

### Sandbox Snapshots (v1.3.4+)
```python
# Snapshot a directory to persist across sandbox lifetimes
snapshot = sb.snapshot_directory("/project")
sb.terminate()

# Mount the snapshot into a new sandbox
sb2 = modal.Sandbox.create(app=app)
sb2.mount_image("/project", snapshot)

# Full filesystem snapshot → reusable image
snapshot_image = sb.snapshot_filesystem()
```

### Sandbox Lifecycle (v1.3.4+)
```python
sb.detach()                   # Keep sandbox running after script exits
sb.terminate(wait=True)       # Block until sandbox fully stopped
sb.reload_volumes()           # Refresh mounted volumes (v1.0.5+)
```

### Programmatic output control
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

## Common Gotchas

1. **`volume.commit()` required** — forgetting = silent data loss. Background auto-commits happen every few seconds but are not guaranteed before container exit.

2. **No relative paths** — container cwd is `/root`. Relative writes vanish on container shutdown. Always use absolute paths to your volume mount point.

3. **No SQLite on volumes** — Modal volumes are NFS-based. SQLite POSIX locking fails silently. Use per-file JSON with atomic `os.replace()`, or `modal.Dict` for concurrent state.

4. **Image build caching** — layers cached per method call. Put slow/stable deps first, fast/changing code last. Use `force_build=True` or `MODAL_FORCE_BUILD=1` to bust cache.

5. **`--detach` with `.spawn()`** — `modal run --detach` only keeps the LAST triggered function alive. To detach multiple functions, run them individually: `modal run --detach script.py::fn1`.

6. **Lazy imports for shared modules** — if a module runs both locally and on Modal, never `import modal` at module level. Guard with `if TYPE_CHECKING` or import inside functions.

7. **Volume inode limits (v1)** — v1 volumes have a 500K file hard limit. Hit it = no new writes. Solutions: upgrade to v2, archive small files, or return results locally instead of writing to volume.

8. **Exit code 144** — Modal API timeout killed the process. Often from volume operations or slow API calls. Use `--local` flags where available for quick checks.

9. **ASGI scope state leak** — fixed in v1.3.3. If on older versions, scope `state` can leak between requests in `@modal.asgi_app`.

10. **Large datasets** — Modal considers >100 GiB "large." Use `CloudBucketMount` (Cloudflare R2 preferred for cost). Download to `/tmp/` first (some tools don't support CloudBucketMount filesystem). Budget `ephemeral_disk` for decompression (100 GiB compressed → 600 GiB working space).

11. **`dev_suffix` in `.modal.toml`** — override ephemeral app URL suffix for consistent dev URLs across runs.

12. **`ephemeral_disk` range** — valid range is 524,288–3,145,728 MiB (~500 GiB–3 TiB). Values outside this range error at function creation. Omit the parameter entirely for default disk.

13. **Volume FUSE partial write leak** — Modal's FUSE layer can expose partially-written files to other containers even without `vol.commit()`. Don't checkpoint on intermediate output files — checkpoint on a completion marker (e.g., summary JSON written atomically via `os.replace()` only after all work finishes).

14. **`modal volume rm` may fail** if the volume is mounted by a running function or sandbox. Stop all consumers first.

15. **`Image.from_registry` Python conflicts** — some Docker images (e.g., `broadinstitute/gatk`) bundle an incompatible Python. Use `Image.micromamba()` with conda packages instead to control the Python version.

16. **C++ build deps in images** — if your image builds C/C++ code, install BOTH `gcc` AND `g++`. Some Makefiles use `$(CXX)` which specifically requires `g++`.

17. **`subprocess` + `capture_output=True` hides errors from `modal app logs`** — container logs only show the parent function's stdout/stderr. Subprocess output captured in Python variables never appears in `modal app logs`. For debugging, write subprocess output to a volume log file instead: `stdout=log_f, stderr=subprocess.STDOUT`.

18. **GPU contention across ephemeral apps** — `.starmap()` holds all worker containers alive for the duration. Workspace-wide GPU limits block ALL new GPU apps, regardless of GPU type. You cannot use `Function.update_autoscaler()` on ephemeral apps (only deployed). Only options: wait for starmap to finish, or stop the blocking app.

19. **Stale volume results after `app stop`** — killing an app mid-run leaves old results on the volume. A subsequent run's results file may actually be from a PREVIOUS run. Always check timestamps or add a run ID/timestamp field to results JSON to distinguish stale data from fresh failures.

20. **Empty files not persisted on volumes** — writing a 0-byte file and calling `vol.commit()` may not persist the file. If you need to detect "ran but produced no output," write a sentinel value (e.g., `"(empty)"`) instead of an empty string.

21. **Subprocess log files invisible until `vol.commit()`** — writing subprocess output to a volume file (`stdout=log_f`) means nothing is visible until the subprocess finishes AND `vol.commit()` runs. If the subprocess hangs, the container burns GPU hours with zero visibility. **Fix:** flush + commit periodically from a background thread, OR use `subprocess.Popen` with a polling loop that commits every N minutes:
```python
import threading, time
def periodic_commit(vol, interval=300):
    while not _done.is_set():
        vol.commit()
        _done.wait(interval)
_done = threading.Event()
t = threading.Thread(target=periodic_commit, args=(vol, 300), daemon=True)
t.start()
# ... run subprocess ...
_done.set()
vol.commit()  # final
```

22. **`.map()` default kills all on first failure** — `.map()` and `.starmap()` default to `return_exceptions=False`. One failed input cancels ALL other running containers. For jobs where partial success is useful (e.g., downloading 24 chromosomes — 23/24 succeeding is better than 0/24), always use `return_exceptions=True`. Then check results for exceptions before proceeding:
   ```python
   results = list(fn.map(inputs, return_exceptions=True))
   failures = [r for r in results if isinstance(r, Exception)]
   if failures:
       raise RuntimeError(f"{len(failures)}/{len(inputs)} failed: {failures[:3]}")
   ```

23. **Validate downloaded files by integrity, not size** — a file that's 9 GB (vs expected 30 GB) passes a `> 100MB` size check. **WARNING:** none of the cheap checks are fully reliable for VCFs: `bcftools index` succeeds on some truncated files, `bcftools quickcheck` doesn't exist on Debian slim's old bcftools (v1.13), and `wget` returns exit 0 on incomplete downloads. The only reliable check is an end-to-end read: `bcftools view file.vcf.bgz | tail -1` (reads every record, fails on corruption). For general files: verify against HTTP `Content-Length`, or use checksums. **Debian slim gotcha:** `apt_install("bcftools")` gives v1.13 — missing `quickcheck`, `+fixploidy`, and other modern subcommands. Pin a newer version via conda or build from source if you need them.

24. **Avoid intermediate files that double disk usage** — before writing a concat/merge step, check if the downstream tool accepts multiple inputs natively. `echtvar encode` accepts `<VCFS>...` ("can be split by chrom") — no concat needed. `bcftools merge` accepts multiple VCFs. Concatenating 500 GB of per-chromosome VCFs into a single file before encoding doubles the disk requirement to 1 TB and hits volume/disk limits. **Rule:** `tool --help` before designing the pipeline.

25. **`.starmap()` cost trap** — `.starmap(args)` with N args on a function with `max_containers` unset will spin up one container per input. Each container stays alive for the full starmap duration even if idle between sequential tasks. **Always set `max_containers` explicitly** and estimate: `cost = max_containers × wall_time × gpu_price`. For 100 tasks at 1h each with 10 containers = 10h × 10 × $1.10 = $110.

26. **Cost guard: always set `timeout` conservatively** — if your script should finish in 2h, set `timeout=10800` (3h), not `timeout=43200` (12h). A hung process with a 12h timeout burns 12h of GPU. The timeout is your cost circuit breaker.

27. **Micromamba/bioconda Python downgrade breaks pip** — installing bioconda packages (e.g., `mmseqs2`, `samtools`) via `micromamba_install` can silently downgrade Python (e.g., 3.11.15 → 3.11.0), which removes pip. Subsequent `.pip_install()` calls fail. **Fix:** use `.uv_pip_install()` instead — it bootstraps its own installer and doesn't depend on system pip:
   ```python
   # BAD: pip may not exist after micromamba downgrades Python
   image = (
       modal.Image.micromamba()
       .micromamba_install("mmseqs2", channels=["bioconda", "conda-forge"])
       .pip_install("torch", "transformers")  # FAILS: pip not found
   )

   # GOOD: uv bootstraps independently
   image = (
       modal.Image.micromamba()
       .micromamba_install("mmseqs2", channels=["bioconda", "conda-forge"])
       .uv_pip_install("torch", "transformers")  # Works regardless of pip state
   )
   ```

28. **`git` binary required for `git+https://` pip installs** — PEP 508 URL specifiers like `"pkg @ git+https://github.com/org/repo.git"` require git in the container. Neither `debian_slim` nor `micromamba` base images include it by default.
   ```python
   # BAD: git not available
   image = modal.Image.debian_slim().uv_pip_install(
       "mylib @ git+https://github.com/org/mylib.git"
   )

   # GOOD: install git first
   image = (
       modal.Image.debian_slim()
       .apt_install("git")
       .uv_pip_install("mylib @ git+https://github.com/org/mylib.git")
   )
   # Or via micromamba:
   image = (
       modal.Image.micromamba()
       .micromamba_install("git", "mmseqs2", channels=["bioconda", "conda-forge"])
       .uv_pip_install("mylib @ git+https://github.com/org/mylib.git")
   )
   ```

29. **`modal deploy` now defaults to rolling strategy** — old containers may still serve requests for minutes after deploy. If you need immediate cutover (e.g., dev iteration, max_containers-limited apps), use `modal deploy --strategy recreate`. `modal serve` already uses recreate by default in v1.4.0.

30. **`modal app logs` no longer streams by default** — if your agent workflow depends on tailing logs (e.g., monitoring a running job), you MUST add `--follow`. Without it, you get the last 100 entries and the command exits. This is the #1 v1.4.0 behavior change that will silently break existing workflows.

31. **`uv_pip_install` breaks CUDA base images with compiled C extensions** — `uv_pip_install("torch")` resolves to the latest torch (e.g., 2.11.0 with CUDA 13.0) regardless of the base image's CUDA version. On a `nvidia/cuda:12.4` base image, this causes: (a) CUDA version mismatch when compiling flash-attn/transformer-engine, (b) ABI mismatch if `uv_pip_install` later overwrites a compiled wheel with a pre-built one. **Use `pip_install` for the entire dependency chain when the image has `run_commands` that compile C extensions against torch.** `uv_pip_install` is safe for `debian_slim` images where torch bundles its own CUDA runtime.
   ```python
   # BROKEN: uv grabs torch 2.11 (CUDA 13.0) on CUDA 12.4 base
   modal.Image.from_registry("nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04")
       .uv_pip_install("torch")  # CUDA 13.0 wheel
       .run_commands("pip install flash-attn --no-build-isolation")  # CUDA 12.4/13.0 mismatch

   # CORRECT: pip resolves CUDA-compatible torch; chain stays consistent
   modal.Image.from_registry("nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04")
       .pip_install("torch")  # resolves CUDA 12.4-compat version
       .run_commands("pip install flash-attn --no-build-isolation")  # matches

   # ALSO CORRECT: debian_slim — torch bundles its own CUDA runtime, no base image conflict
   modal.Image.debian_slim().uv_pip_install("torch", "transformers")  # always safe
   ```

## MANDATORY: Cost Awareness

**Real-world lesson: $400 spent in 2 days, 60% wasted.** #1 cause: unbounded `.starmap()` auto-scaling ($227 when $82 would have sufficed).

**Before launching ANY GPU job, calculate and state the expected cost:**
```
containers × expected_hours × $/hr = $expected
```

### Non-negotiable checklist (every GPU launch):
1. **`max_containers` set** — never let Modal auto-scale GPU containers unbounded
2. **`timeout` = 1.5× expected** — this is your cost circuit breaker. A 12h timeout on a 2h job = 12h of GPU if it hangs.
3. **Cost stated** — say "$X expected" in the launch message. If >$20, get user confirmation.
4. **Log visibility** — any job >30min must have periodic `vol.commit()` (every 5min). A subprocess that writes to a file but never commits = silent GPU burn with zero visibility.
5. **No redundant evals** — don't run serial then parallel. Pick one path. A "quick serial test" at full scale is not a test, it's a redundant full run.
6. **For `.starmap()`**: `max_containers=min(len(tasks), budget / (expected_hours * gpu_price))`
7. **Early stopping** — for training jobs, check eval metrics at intervals. If metrics plateau at useless levels (e.g., 15% eval_acc after 80% of epochs), stop early rather than hoping the last 20% of training will help.
8. **Intermediate snapshots** — any long-running job (>1h) must save intermediate results to the volume, not just at the end. If a 6h job times out at hour 5 with results only saved at completion, all compute is wasted. Pattern:
   - Set periodic evaluation intervals (e.g., every 200 epochs instead of only at the final epoch)
   - In the `vol.commit()` polling loop, detect new output files and copy them to the volume
   - Save with timestamps or step numbers so you can resume from the last snapshot
   ```python
   # In the commit loop, look for new evaluator output:
   for fname in os.listdir(output_dir):
       if fname not in saved_snapshots:
           shutil.copy2(os.path.join(output_dir, fname), volume_snapshot_dir)
           saved_snapshots.add(fname)
   vol.commit()
   ```
9. **Never download large data to `/tmp/` in long-running jobs.** Ephemeral disk is wiped when the container dies. If a job downloads 50 GB over 2 hours to `/tmp/` then crashes at the encode step, all downloads are lost and the retry starts from zero. **Write downloads directly to the Modal volume** (`/data/...`) and `vol.commit()` after each file. On restart, check file existence + size to skip already-downloaded files. The volume costs storage but saves hours of re-download on any failure. Only use `/tmp/` for true scratch (temp files consumed and deleted within minutes).
   ```python
   # BAD: downloads lost on crash
   WORK_DIR = "/tmp/big_download"

   # GOOD: downloads persist, job is resumable
   WORK_DIR = f"{DATA_DIR}/databases/my_dataset/work"
   for file in files_to_download:
       dest = f"{WORK_DIR}/{file}"
       if Path(dest).exists() and Path(dest).stat().st_size > MIN_SIZE:
           print(f"Already downloaded: {file}")
           continue
       download(url, dest)
       vol.commit()  # Persist immediately
   ```

## MANDATORY: Test Before Deploying

**Never deploy a new Modal script straight to a full run.** Follow this order:

1. **Local syntax check**: `python -c "import ast; ast.parse(open('script.py').read())"`
2. **Image probe**: `image.build(app)` — catches ALL image build failures (apt, pip, conda, linkage) without GPU cost. In genomics: `just probe <stage>` for full validation (sandbox + tool checks), or `just run <stage>` which auto-probes build-only.
3. **Smoke test on small data**: Subset or first N records (< 5 min)
4. **Interactive debug**: `modal shell scripts/script.py` for container access, or use the Sandbox-as-REPL workflow above
5. **Full run**: Only after steps 1-3 pass

For new tools with complex C/system dependencies (like Aldy, pysam, htslib), use the full Sandbox probe to verify library linkage BEFORE the first `modal run`.

## Reference Docs

Detailed docs in `references/`:
- `images.md` — base images, deps, build caching, eStargz
- `functions.md` — definition, calling, deployment, parallel execution
- `gpu.md` — GPU types, multi-GPU, fallbacks
- `volumes.md` — creation, commits, concurrent access, v1 vs v2, uploads
- `scaling.md` — autoscaling, .map/.starmap, concurrency, limits
- `secrets.md` — creation, usage, patterns
- `web-endpoints.md` — FastAPI, ASGI/WSGI, streaming, auth, custom domains
- `scheduled-jobs.md` — Period, Cron, timezone, deployment
- `resources.md` — CPU, memory, disk, billing
- `sandboxes.md` — creation, exec, snapshots, named sandboxes
