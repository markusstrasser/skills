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
