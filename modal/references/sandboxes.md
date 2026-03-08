# Modal Sandboxes

## Overview

Sandboxes provide isolated containers for running untrusted code or interactive development. They support exec, file I/O, networking, and persistent naming.

## Creating Sandboxes

```python
import modal

app = modal.App.lookup("my-app", create_if_missing=True)

sandbox = modal.Sandbox.create(
    "python3", "-c", "print('hello')",
    app=app,
    image=modal.Image.debian_slim(),
    timeout=300,
    cpu=2.0,
    memory=4096,
)
```

### Named Sandboxes (v1.1.1+)

```python
sb = modal.Sandbox.create(
    "python3", "-m", "http.server",
    name="dev-server",
    app=app,
    image=image,
)

# Retrieve later
sb = modal.Sandbox.from_name("dev-server")
```

## Executing Commands

```python
process = sandbox.exec("ls", "-la", "/data")
print(process.stdout.read())
print(process.stderr.read())
exit_code = process.returncode

# PTY support (v1.2+)
process = sandbox.exec("bash", pty=True)
```

### Stdin Writes (8x faster in v1.3.4+)

```python
process = sandbox.exec("cat")
process.stdin.write("hello\n")
process.stdin.write_eof()
output = process.stdout.read()
```

## Directory Snapshots (v1.3.4 beta)

Capture and restore directory state:

```python
snapshot = sandbox.snapshot_directory("/work")

# Mount snapshot in another sandbox
sb2 = modal.Sandbox.create(app=app)
sb2.mount_image(snapshot)
```

## Lifecycle

```python
# Detach client (v1.3.4+)
sandbox.detach()

# Terminate with wait (v1.3.4+)
sandbox.terminate(wait=True)

# Idle timeout
sb = modal.Sandbox.create(..., idle_timeout=300)  # v1.1.4+
```

## Volumes in Sandboxes

```python
vol = modal.Volume.from_name("my-vol")
sandbox = modal.Sandbox.create(
    "python3", "process.py",
    app=app,
    volumes={"/data": vol},
)

# Reload volumes (v1.1+)
sandbox.reload_volumes()
```

## Networking

```python
# HTTP/2 support (v1.2.4+)
sb = modal.Sandbox.create(..., h2_ports=[8080])

# Block network access
sb = modal.Sandbox.create(..., block_network=True)

# Custom domain (v1.3.1+, requires Modal setup)
sb = modal.Sandbox.create(..., custom_domain="dev.example.com")
```

## Authentication Tokens (v1.2+)

```python
token = sandbox.create_connect_token()
# Use for HTTP/WebSocket authentication to sandbox
```

## Container Logs

```bash
modal container logs <sandbox-id>
```

## Tags

```python
sandbox.set_tags({"env": "dev", "user": "alice"})
tags = sandbox.get_tags()
```
