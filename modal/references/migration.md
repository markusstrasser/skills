<!-- Reference file for modal skill. Loaded on demand. -->

# Migration & Version History

## Critical API Changes (v1.0+)

Things that WILL break old code:

```python
# OLD (pre-1.0)              ->  NEW (v1.0+)
modal.Stub("name")           ->  modal.App("name")  # Stub raises AttributeError
concurrency_limit=N           ->  max_containers=N
keep_warm=N                   ->  min_containers=N
container_idle_timeout=N      ->  scaledown_window=N
allow_concurrent_inputs=N     ->  @modal.concurrent(max_inputs=N)  # decorator
max_inputs=N                  ->  single_use_containers=True  # v1.3+, now boolean
Function.web_url              ->  Function.get_web_url()
modal.web_endpoint             ->  modal.fastapi_endpoint  # clarifies FastAPI dep
modal.Mount(...)              ->  REMOVED -- use Image.add_local_python_source()
mount= parameter              ->  REMOVED everywhere
app.run(show_progress=True)   ->  REMOVED
modal.gpu.H100() objects      ->  gpu="H100" strings (case-insensitive)
@modal.build decorator        ->  Image.run_function() or Volumes
Image.copy_local_dir/file     ->  Image.add_local_dir/file (default: runtime mount, copy=True for layer)
.lookup()                     ->  .from_name() + .hydrate() for metadata
Custom __init__ on @app.cls   ->  modal.parameter() annotations (str/int/bool/bytes only)
.resolve()                    ->  REMOVED from Modal objects
Function.spawn (generators)   ->  REMOVED -- spawn no longer supports generators
FunctionCall.get_gen           ->  REMOVED
grpclib.GRPCError              ->  modal.Error subtypes (v1.3+)
environment_name= (Sandbox)   ->  DEPRECATED -- use environment=
namespace= (.from_name)       ->  DEPRECATED
```

**Automounting disabled (v1.0+)** -- local packages no longer auto-included. Must explicitly add:
```python
image = modal.Image.debian_slim().add_local_python_source("my_module")
# Or sync entire project:
image = modal.Image.debian_slim().uv_sync()
```

**CLI flag ordering** -- flags go BEFORE the script path:
```bash
# CORRECT:
uv run modal run --detach scripts/modal_foo.py::run_analysis
# WRONG (silently fails or errors):
uv run modal run scripts/modal_foo.py --detach
```

**Lifecycle hooks** -- use decorators, not `__init__`:
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

### v1.4.3 (2026-05-18)

**Regional input routing (Public Beta).** Route Function inputs through `us-west`, `eu-west`, or `ap-south` instead of the default `us-east` for latency or data residency:

```python
@app.function(routing_region="eu-west")
def handler(x): ...

@app.cls(routing_region="ap-south")
class Worker: ...
```

Constraints while in Beta:
- `routing_region=` can only be set on **initial** deployment — not changed in a later redeploy.
- Functions routed outside `us-east` can only be invoked via `.remote()` and `.map()` (no `.spawn`, no web endpoints).

**`modal.Environment` object + RBAC CLI.** Programmatic Environment management plus expanded `modal environment` CLI for role-based access control configuration.

**Dynamic Function configuration.** Override decorator settings at call site without redefining the Function:

```python
fn = modal.Function.from_name("app", "handler")
fn.with_options(gpu="H100", timeout=3600).remote(x)
fn.with_concurrency(max_inputs=8).remote(x)
fn.with_batching(max_batch_size=32, wait_ms=50).remote(x)
```

**`Volume.with_mount_options()`** — per-mount read-only or sub-path scoping (more composable than `vol.read_only()`):

```python
vol = modal.Volume.from_name("shared")
@app.function(volumes={
    "/data": vol.with_mount_options(read_only=True, sub_path="/tenant_a"),
})
def reader(): ...
```

**Custom ephemeral App names.** `modal run --name my-run script.py`, `modal serve --name dev script.py`, or `App.run(name="...")`. Useful for distinguishing concurrent ephemeral apps in `modal app list`.

**Sandbox filesystem additions** (see also `references/sandboxes.md`):
- `sb.filesystem.list_files(path)` — replaces the alpha `Sandbox.ls`. Returns entries with metadata.
- `sb.filesystem.stat(path)` — metadata for a single file/dir/symlink.

**Sandbox network ACLs.**
```python
sb = modal.Sandbox.create(
    app=app,
    inbound_cidr_allowlist=["10.0.0.0/8", "192.168.1.0/24"],
    outbound_cidr_allowlist=["0.0.0.0/0"],   # new
)
```
`cidr_allowlist=` is **deprecated** — its scope was ambiguous. Use `inbound_cidr_allowlist=` explicitly.

**Sandbox `tags=` at creation** — previously only available via `sandbox.set_tags()` after create.

```python
sb = modal.Sandbox.create(app=app, tags={"env": "dev", "owner": "alice"})
```

**Sandbox snapshot improvements.**
- `sandbox.snapshot_filesystem()` is more reliable for large snapshots; supports `timeout=` longer than the old 55s ceiling.
- The Image returned by `sandbox.snapshot_directory()` can now be passed as the root filesystem of a new Sandbox: `modal.Sandbox.create(image=snap, ...)`.

**`Image.pipe()`** — compose reusable Image-builder steps without breaking the fluent chain:

```python
def with_cuda_toolchain(img: modal.Image) -> modal.Image:
    return img.apt_install("build-essential").pip_install("torch")

image = (
    modal.Image.debian_slim()
    .pipe(with_cuda_toolchain)
    .add_local_python_source("my_pkg")
)
```

**`Image.from_dockerfile(..., chmod=..., chown=...)`** flags now honored on `COPY` instructions inside the Dockerfile.

**`modal shell` / `modal container exec`** — improved reliability and lower latency on connect.

### v1.4.2 (2026-04-16)

**`modal app rollover`** — trigger redeployment of an App without changing code/config. Replaces running containers with fresh ones using the same deployment strategies as `modal deploy`:

```bash
modal app rollover my-app                       # --strategy=rolling (default)
modal app rollover my-app --strategy=recreate   # terminate all old containers first
```

Use when: config-via-env-Secret rotated, base image rebuilt, you want to force a clean container set without touching the script.

**`modal bootstrap`** — fetches deployable starter code for common AI apps (text generation, text-to-image, speech-to-text). Experimental.

**Confirmation prompts on stop commands.** `modal app stop` and `modal container stop` now prompt before stopping. Pass `--yes` to skip — required for scripted/automated callers.

```bash
modal app stop my-app --yes
modal container stop ct-abc123 --yes
```

**Stopped-App name resolution.** Several `modal app` subcommands (e.g. `modal app logs`) now map a name argument to a recently-stopped App that used that name. Lets you fetch logs from an App after it has been stopped without having to look up the ap-id.

**Sandbox filesystem: `make_directory` / `remove`** — replace deprecated `Sandbox.mkdir` / `Sandbox.rm`.

```python
sb.filesystem.make_directory("/work/results")
sb.filesystem.remove("/work/old_artifact")   # file or directory

# DEPRECATED — do not use in new code:
sb.mkdir("/work/results")
sb.rm("/work/old_artifact")
```

**Sandbox `unmount_image(path)`** — removes a previously mounted Image from a path and reveals the underlying Sandbox filesystem there again. Pairs with `sb.mount_image(image, path)`.

```python
sb.mount_image(extra, "/opt/extra")
# ... use ...
sb.unmount_image("/opt/extra")               # underlying fs reappears at /opt/extra
```

**`Image.dockerfile_commands(build_args=...)`** — pass build args (equivalent to Docker `--build-arg`) to inline Dockerfile commands.

```python
image = modal.Image.debian_slim().dockerfile_commands(
    ["ARG VERSION", "RUN echo $VERSION > /etc/app-version"],
    build_args={"VERSION": "1.2.3"},
)
```

### CLI Log Overhaul (v1.4.0 -- BREAKING DEFAULT CHANGE)

**`modal app logs` and `modal container logs` no longer follow (stream) by default.** They now show the most recent 100 entries and exit. You MUST pass `--follow` for the old streaming behavior.

```bash
# Historical logs (new default -- shows last 100)
modal app logs my-app
modal container logs ct-abc123

# Stream logs (old default -- now requires --follow)
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

### Sandbox Filesystem API (v1.4.0 beta -- replaces Sandbox.open)

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
# Rolling (default) -- prioritizes uptime, old containers continue briefly
modal deploy script.py

# Recreate -- immediately terminates old containers on deploy
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
# modal deploy -m project.app        <-- CORRECT
# modal deploy project.app           <-- ERROR in v1.4+

# Old autoscaler config removed (keep_warm, concurrency_limit, etc.)
# Use: max_containers, min_containers, scaledown_window

# Function.from_name can't look up Cls methods anymore
# OLD: modal.Function.from_name("app", "MyClass.method")
# NEW: modal.Cls.from_name("app", "MyClass")

# Removed unused namespace parameters from various APIs
```

## New Features (v1.1-v1.3)

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

### Async Warnings (v1.3+ -- enabled by default)
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

### Function Stats (v1.3.5+)
```python
stats = fn.get_current_stats()
print(stats.num_running_inputs)
```
