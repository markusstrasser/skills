<!-- Reference file for modal skill. Loaded on demand. -->

# Modal Volumes

## Overview

Modal Volumes provide high-performance distributed file systems for Modal applications. Designed for write-once, read-many workloads like ML model weights and distributed data processing.

## Creating Volumes

### Via CLI

```bash
modal volume create my-volume
```

For Volumes v2 (beta):
```bash
modal volume create --version=2 my-volume
```

### From Code

```python
vol = modal.Volume.from_name("my-volume", create_if_missing=True)

# For v2
vol = modal.Volume.from_name("my-volume", create_if_missing=True, version=2)
```

## Using Volumes

Attach to functions via mount points:

```python
vol = modal.Volume.from_name("my-volume")

@app.function(volumes={"/data": vol})
def run():
    with open("/data/xyz.txt", "w") as f:
        f.write("hello")
    vol.commit()  # Persist changes
```

## Commits and Reloads

### Commits

Persist changes to Volume:

```python
@app.function(volumes={"/data": vol})
def write_data():
    with open("/data/file.txt", "w") as f:
        f.write("data")
    vol.commit()  # Make changes visible to other containers
```

**Background commits**: Modal automatically commits Volume changes every few seconds and on *graceful* container shutdown (normal return or handled exception). They do NOT fire on a SIGKILL — workspace budget-kill, OOM, or hard preemption lose everything written since the last explicit `vol.commit()`. See SKILL.md → "Budget kills".

### Reloads

Fetch latest changes from other containers:

```python
@app.function(volumes={"/data": vol})
def read_data():
    vol.reload()  # Fetch latest changes
    with open("/data/file.txt", "r") as f:
        content = f.read()
```

At container creation, latest Volume state is mounted. Reload needed to see subsequent commits from other containers.

## Uploading Files

### Batch Upload (Efficient)

```python
vol = modal.Volume.from_name("my-volume")

with vol.batch_upload() as batch:
    batch.put_file("local-path.txt", "/remote-path.txt")
    batch.put_directory("/local/directory/", "/remote/directory")
    batch.put_file(io.BytesIO(b"some data"), "/foobar")
```

### Via Image

```python
image = modal.Image.debian_slim().add_local_dir(
    local_path="/home/user/my_dir",
    remote_path="/app"
)

@app.function(image=image)
def process():
    # Files available at /app
    ...
```

## Downloading Files

### Via CLI

```bash
modal volume get my-volume remote.txt local.txt
```

Max file size via CLI: No limit
Max file size via dashboard: 16 MB

**Gotcha: `modal volume get` does NOT overwrite existing local files by default.**
If `local.txt` exists, the CLI prompts for confirmation; in detached or
non-TTY contexts the prompt fires and the command exits without writing,
leaving the stale local copy in place. Agents reading a "downloaded" file
after that get last-run data. Fix: `rm -f local.txt` before the `get`, or
use a fresh timestamped local path per fetch.

Evidence: 2026-04-15 post-compute audit on genomics/prs_percentile — old
12-row output was served instead of new 39-row because /tmp/prs_percentiles.json
already existed from the morning run and the overwrite prompt didn't resolve.

### Via Python SDK

```python
vol = modal.Volume.from_name("my-volume")

for data in vol.read_file("path.txt"):
    print(data)
```

## Volume Performance

### Volumes v1

Best for:
- <50,000 files (recommended)
- <500,000 files (hard limit)
- Sequential access patterns
- <5 concurrent writers

**Metadata RPCs are rate-limited — high concurrency storms a v1 volume.** A v1
volume is sequential-access tuned. A job that fans out hundreds of
`VolumeListFiles` / `VolumeGetFile` RPCs at high concurrency (building a
full-tree file ledger, a recursive listdir prefill, a per-file sync) drains the
workspace rate-limit bucket and gets stuck in sustained 429 backoff for *tens of
minutes*. Empirically: 128-way concurrency → 442 backoffs/60s (never converges);
6-16 way → a couple backoffs, builds steadily. **The lever is concurrency, not
waiting** — cap the parallelism of any volume-metadata sweep and don't burst
several heavy sweeps back-to-back. Two corollaries: (1) a read that 429s
mid-sweep can return `None` and be misread as "file absent" → a silent false
"nothing has run"; make metadata reads **retry-or-raise, never silently
degrade**. (2) For control-plane *state* (run/stage status), prefer a
rate-limit-immune DB (Postgres) over re-deriving it from volume file listings.

### Volumes v2 (Beta)

Improved for:
- Unlimited files
- Hundreds of concurrent writers
- Random access patterns
- Large files (up to 1 TiB)

Current v2 limits:
- Max file size: 1 TiB
- Max files per directory: 32,768
- Unlimited directory depth

## Model Storage

### Saving Model Weights

```python
volume = modal.Volume.from_name("model-weights", create_if_missing=True)
MODEL_DIR = "/models"

@app.function(volumes={MODEL_DIR: volume})
def train():
    model = train_model()
    save_model(f"{MODEL_DIR}/my_model.pt", model)
    volume.commit()
```

### Loading Model Weights

```python
@app.function(volumes={MODEL_DIR: volume})
def inference(model_id: str):
    try:
        model = load_model(f"{MODEL_DIR}/{model_id}")
    except NotFound:
        volume.reload()  # Fetch latest models
        model = load_model(f"{MODEL_DIR}/{model_id}")
    return model.run(request)
```

## Model Checkpointing

Save checkpoints during long training jobs:

```python
from pathlib import Path

volume = modal.Volume.from_name("checkpoints")
VOL_PATH = Path("/vol")   # Path, not str — VOL_PATH / "model" below needs it

@app.function(
    gpu="A10G",
    timeout=2*60*60,  # 2 hours
    volumes={str(VOL_PATH): volume},   # mount keys are strings
)
def finetune():
    from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(VOL_PATH / "model"),  # Checkpoints saved to Volume
        save_steps=100,
        # ... more args
    )

    trainer = Seq2SeqTrainer(model=model, args=training_args, ...)
    trainer.train()
```

Background commits persist checkpoints across *graceful* interruptions (normal stop, code exception) — but they do NOT fire on a SIGKILL. Workspace budget-kill, OOM, and ungraceful preemption lose everything since the last commit, so `save_steps` alone is not durable against a hard kill; pair it with explicit `vol.commit()` at step boundaries (see "Commit-and-Checkpoint Pattern" below).

## Commit-and-Checkpoint Pattern for Long Jobs

For any job running >10 min, commit intermediate results so progress
survives crashes, preemption, or workspace budget-kill. The pattern:

```python
for i, chunk in enumerate(chunks):
    process(chunk, output_path)        # write to /data/...
    if i % 10 == 0:
        vol.commit()                   # flush to volume
        print(f"[{i}/{len(chunks)}] checkpoint committed", flush=True)

# final commit at function exit (or use @modal.exit() / background commit)
vol.commit()
```

Rules:

1. Commit after every logical step, not every iteration. Volume commits
   have non-trivial latency — too frequent hurts throughput.
2. During a single long subprocess (>30 min), copy its in-progress artifact
   to the volume during a heartbeat loop + commit once the first full
   artifact appears. Guard with a once-only flag to avoid repeated copies.
3. Use `_atomic_write(path, content)` (temp-file + fsync + rename) for any
   artifact >100 MB to avoid partial-write corruption if the container
   SIGKILLs mid-write.
4. When resuming, verify on-volume checkpoints before trusting them —
   compare size + SHA256 against an expected value. Missing or truncated
   files → re-run from scratch, don't silently resume on garbage.

## Ephemeral vs Volume Paths

Ephemeral disk (`/tmp`, `/root/...`) is **gone** on container shutdown.
Everything written there is lost on:
- Normal shutdown after function return
- Preemption
- OOM kill
- Workspace budget-kill
- Any SIGKILL

Only files under a mounted volume path survive. For multi-step pipelines,
land intermediate artifacts on the volume even if the next step will
immediately read them — future-you will be glad when step 3 crashes and
step 2's 21 GB output wasn't rebuildable.

## CLI Commands

```bash
# List files
modal volume ls my-volume

# Upload
modal volume put my-volume local.txt remote.txt

# Download
modal volume get my-volume remote.txt local.txt

# Copy within Volume
modal volume cp my-volume src.txt dst.txt

# Delete
modal volume rm my-volume file.txt

# List all volumes
modal volume list

# Delete volume
modal volume delete my-volume
```

## Ephemeral Volumes

Create temporary volumes that are garbage collected:

```python
with modal.Volume.ephemeral() as vol:
    sb = modal.Sandbox.create(
        volumes={"/cache": vol},
        app=my_app,
    )
    # Use volume
    # Automatically cleaned up when context exits
```

## Concurrent Access

### Concurrent Reads

Multiple containers can read simultaneously without issues.

### Concurrent Writes

Supported but:
- Avoid modifying same files concurrently
- Last write wins (data loss possible)
- v1: Limit to ~5 concurrent writers
- v2: Hundreds of concurrent writers supported

#### `.SUCCESS` sentinels do NOT prevent duplicate execution when `retries>0`

A common fanout pattern: `.map()` workers write `chunk_N.out` + `chunk_N.SUCCESS`
and skip-on-resume via `verify_checkpoint(require_success_sentinel=True)`. The
trap: a `vol.reload()` that raises `ConflictError` (a sibling worker has files
open) is often swallowed as a "benign cache miss" — but then the reloading
worker's volume view is **stale**, it doesn't see the freshly-written `.SUCCESS`,
and it re-runs an already-completed chunk. If the output path is the same file,
it opens it for write and **truncates a complete artifact to 0**, corrupting it
mid-stream for any concurrent reader (and permanently, if the re-run is itself
preempted, while the OLD `.SUCCESS` still claims completion).

Defenses, cheapest first:
1. On the consistency-critical reload (the one checking for a `.SUCCESS`), let
   `ConflictError` **raise** — don't swallow it.
2. Open the output with `O_EXCL` / a file lock so the second writer crashes
   loudly instead of silently overwriting.
3. **Atomic rename:** write `chunk_N.out.tmp`, then `os.rename()` to
   `chunk_N.out` only after the write + quickcheck pass. The rename is atomic;
   concurrent writers race for the tmp file but never expose a half-written
   final. Validate downstream by record-count, not file presence.

Evidence: 2026-05-27 — worker A finished a chunk at 13:41 (18.6GB + SUCCESS);
worker B started 30s later on a stale reload, truncated it, and began
overwriting. The chunk had to be redone.

## Volume Errors

### "Volume Busy"

Cannot reload when files are open:

```python
# WRONG
f = open("/vol/data.txt", "r")
volume.reload()  # ERROR: volume busy
```

```python
# CORRECT
with open("/vol/data.txt", "r") as f:
    data = f.read()
# File closed before reload
volume.reload()
```

### "File Not Found"

Remember to use mount point:

```python
# WRONG - file saved to local disk
with open("/xyz.txt", "w") as f:
    f.write("data")

# CORRECT - file saved to Volume
with open("/data/xyz.txt", "w") as f:
    f.write("data")
```

## Upgrading from v1 to v2

No automated migration currently. Manual steps:

1. Create new v2 Volume
2. Copy data using `cp` or `rsync`
3. Update app to use new Volume

```bash
modal volume create --version=2 my-volume-v2
modal shell --volume my-volume --volume my-volume-v2

# In shell:
cp -rp /mnt/my-volume/. /mnt/my-volume-v2/.
sync /mnt/my-volume-v2
```

Warning: Deployed apps reference Volumes by ID. Re-deploy after creating new Volume.
