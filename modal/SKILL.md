---
name: modal
description: "Modal serverless Python cloud compute. Use when writing or debugging Modal scripts, deploying to Modal, or choosing GPU/resource configs. Covers v1.0–v1.3.x API (current as of March 2026)."
---

# Modal (v1.3.x, March 2026)

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
image = modal.Image.debian_slim().pip_install("torch")
image.build()  # Build now, don't wait for function invocation
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

# Container logs
modal container logs <container-id>
modal app logs <app-name> --timestamps

# Volume inspection
modal volume ls my-volume
modal volume get my-volume remote.txt local.txt

# Dashboard
modal dashboard
modal dashboard apps
modal dashboard volumes
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

## MANDATORY: Test Before Deploying

**Never deploy a new Modal script straight to a full run.** Follow this order:

1. **Local syntax check**: `python -c "import ast; ast.parse(open('script.py').read())"`
2. **Dry-run validate**: Quick function that checks inputs exist and tools work (< 2 min)
3. **Smoke test on small data**: Subset or first N records (< 5 min)
4. **Interactive debug**: `modal shell scripts/script.py` for container access
5. **Full run**: Only after steps 1-3 pass

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
