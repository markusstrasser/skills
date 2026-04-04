---
name: modal
description: "Modal serverless Python cloud compute. Use when writing or debugging Modal scripts, deploying to Modal, or choosing GPU/resource configs. Covers v1.0-v1.4.x API (current as of March 2026)."
effort: low
---

# Modal (v1.4.x, March 2026)

## Critical Breaking Changes (v1.0+)

```python
modal.Stub("name")           ->  modal.App("name")
modal.Mount(...)              ->  REMOVED -- use Image.add_local_python_source()
mount= parameter              ->  REMOVED everywhere
modal.gpu.H100() objects      ->  gpu="H100" strings
@modal.build decorator        ->  Image.run_function() or Volumes
modal.web_endpoint             ->  modal.fastapi_endpoint
.lookup()                     ->  .from_name() + .hydrate()
allow_concurrent_inputs=N     ->  @modal.concurrent(max_inputs=N)
concurrency_limit/keep_warm   ->  max_containers/min_containers/scaledown_window
```

**Automounting disabled** -- local packages NOT auto-included. Use `Image.add_local_python_source("mod")` or `Image.uv_sync()`.

**CLI flags go BEFORE the script path:** `modal run --detach script.py` (not `modal run script.py --detach`).

**Lifecycle hooks** -- use `@modal.enter()` / `@modal.exit()` decorators, not `__init__`.

**v1.4 breaking:** `modal app logs` no longer streams -- add `--follow`. `-m` required for module paths. `.map()` exceptions no longer wrapped in `UserCodeException`.

See `references/migration.md` for full migration table, v1.1-v1.3 features, and v1.4 details.

## GPU Decision Tree

| GPU | VRAM | $/hr | Use when |
|-----|------|------|----------|
| T4 | 16GB | ~$0.59 | Model fits <16GB |
| L4 | 24GB | ~$0.73 | Model fits <24GB. **Never A10G** (same VRAM, 50% more) |
| L40S | 48GB | ~$1.65 | Best cost/perf. 24-48GB models |
| A100-80GB | 80GB | ~$3.73 | Need >48GB or SM80 flash-attn |
| H100 | 80GB | ~$3.95 | High-perf training |
| H200 | 141GB | ~$4.54 | Memory-bound workloads |
| B200 | 192GB | ~$6.25 | Flagship, sparse FP4 |

Multi-GPU: `gpu="H100:8"`. Fallback: `gpu=["H100", "A100-80GB"]`.

**Rules:** Inference -> prefer L4/L40S. Use `gpu=["L4", "A10G"]` for availability fallback only. See `references/gpu.md` for full specs.

## Common Gotchas

1. **`volume.commit()` required** -- forgetting = silent data loss.
2. **No relative paths** -- container cwd is `/root`. Always use absolute paths to volume mount.
3. **No SQLite on volumes** -- NFS-based, POSIX locking fails silently. Use per-file JSON with `os.replace()` or `modal.Dict`.
4. **Image caching** -- layers cached per method call. Slow/stable deps first, fast/changing last. `force_build=True` or `MODAL_FORCE_BUILD=1` to bust.
5. **`--detach` + `.spawn()`** -- `modal run --detach` keeps only the LAST function alive. Run each individually.
6. **Lazy imports** -- guard `import modal` with `if TYPE_CHECKING` for modules running both locally and on Modal.
7. **Volume inode limit (v1)** -- 500K files hard limit. Upgrade to v2, or archive small files.
8. **Exit code 144** -- Modal API timeout. Often from volume ops or slow API calls.
9. **ASGI scope state leak** -- fixed in v1.3.3. Upgrade if on older versions.
10. **Large datasets (>100 GiB)** -- use `CloudBucketMount` (R2 preferred). Download to `/tmp/` first if tools don't support FUSE. Budget `ephemeral_disk` for decompression.
11. **`ephemeral_disk` range** -- valid: 524,288-3,145,728 MiB (~500 GiB-3 TiB). Omit for default.
12. **Volume FUSE partial write leak** -- partially-written files visible to other containers even without `commit()`. Use atomic `os.replace()` on a completion marker.
13. **`modal volume rm`** -- fails if volume mounted by running function/sandbox. Stop consumers first.
14. **`Image.from_registry` Python conflicts** -- some Docker images bundle incompatible Python. Use `Image.micromamba()` instead.
15. **C++ build deps** -- install BOTH `gcc` AND `g++`. Some Makefiles use `$(CXX)`.
16. **`subprocess` + `capture_output=True`** -- hides output from `modal app logs`. Write subprocess output to volume file instead.
17. **GPU contention across ephemeral apps** -- `.starmap()` holds all containers. Workspace-wide GPU limits block ALL new GPU apps. Can't `update_autoscaler()` on ephemeral apps.
18. **Stale volume results after `app stop`** -- old results persist. Add run ID/timestamp to results JSON.
19. **Empty files not persisted** -- 0-byte files may not persist after `commit()`. Write a sentinel value.
20. **Subprocess logs invisible until `vol.commit()`** -- if subprocess hangs, zero visibility. Flush + commit periodically from background thread.
21. **`.map()` kills all on first failure** -- default `return_exceptions=False`. Use `return_exceptions=True` when partial success is useful.
22. **Validate downloads by integrity, not size** -- 9 GB vs expected 30 GB passes a `> 100MB` check. Use checksums or end-to-end read. Debian slim's `bcftools` is v1.13 -- missing modern subcommands.
23. **Avoid intermediate concat files** -- check if downstream tool accepts multiple inputs natively. `tool --help` before designing pipeline.
24. **`.starmap()` cost trap** -- one container per input if `max_containers` unset. Always set explicitly. `cost = max_containers * wall_time * gpu_price`.
25. **Set `timeout` conservatively** -- 2h job -> `timeout=10800` (3h), not 12h. Timeout is your cost circuit breaker.
26. **Micromamba/bioconda breaks pip** -- installing bioconda packages can silently downgrade Python, removing pip. Use `.uv_pip_install()` instead of `.pip_install()` after micromamba.
27. **`git` required for `git+https://`** -- debian_slim/micromamba don't include git. `apt_install("git")` first.
28. **Rolling deploy default** -- old containers may serve for minutes after deploy. Use `--strategy recreate` for immediate cutover.
29. **`modal app logs` no longer streams** -- add `--follow` or you get last 100 entries and exit. #1 v1.4 behavior change.
30. **`uv_pip_install` breaks CUDA base images** -- resolves latest torch regardless of base CUDA version. Use `pip_install` for CUDA base images with C extension compilation. `uv_pip_install` is safe on `debian_slim` (torch bundles own CUDA).
31. **`cpu` = physical cores, NOT vCPUs.** `cpu=8` = 16 vCPUs. Soft limit = request + 16 cores.
32. **Never `subprocess.run(timeout=N)` on `modal run --detach`** -- image builds take 2-5 min on first deploy. Timeout kills the local process but Modal continues building server-side, creating orphan apps with no tracked app ID. `modal run --detach` always returns after image build. No timeout needed. (Evidence: 63 orphan apps, 4 "fix" attempts increasing timeout before finding root cause.)

## MANDATORY: Cost Awareness

**Real-world lesson: $400 in 2 days, 60% wasted.** #1 cause: unbounded `.starmap()`.

Before ANY GPU launch, state: `containers * hours * $/hr = $expected`

**Checklist:**
1. `max_containers` set -- never unbounded GPU auto-scaling
2. `timeout` = 1.5x expected -- cost circuit breaker
3. Cost stated -- if >$20, get user confirmation
4. Log visibility -- jobs >30min need periodic `vol.commit()` (every 5min)
5. For `.starmap()`: `max_containers=min(len(tasks), budget / (hours * price))`
6. Early stopping -- check eval metrics at intervals, stop if plateaued
7. Intermediate snapshots -- any job >1h must save intermediate results
8. Never download large data to `/tmp/` -- write to volume, `commit()` after each file, skip existing on restart

## MANDATORY: Test Before Deploying

1. **Local syntax check**: `python -c "import ast; ast.parse(open('script.py').read())"`
2. **Image probe**: `image.build(app)` -- catches all build failures, no GPU cost
3. **Smoke test**: Small data subset (< 5 min)
4. **Interactive debug**: `modal shell script.py` or Sandbox-as-REPL (see `references/debugging.md`)
5. **Full run**: Only after 1-3 pass

## Reference Docs

Detailed docs in `references/`:
- `migration.md` -- v1.0 breaking changes, v1.1-v1.3 features, v1.4 features/breaking changes
- `debugging.md` -- CLI commands, Sandbox-as-REPL, image probing, output control
- `images.md` -- base images, deps, build caching, eStargz
- `functions.md` -- definition, calling, deployment, parallel execution
- `gpu.md` -- GPU types, multi-GPU, fallbacks
- `volumes.md` -- creation, commits, concurrent access, v1 vs v2, uploads
- `scaling.md` -- autoscaling, .map/.starmap, concurrency, limits
- `secrets.md` -- creation, usage, patterns
- `web-endpoints.md` -- FastAPI, ASGI/WSGI, streaming, auth, custom domains
- `scheduled-jobs.md` -- Period, Cron, timezone, deployment
- `resources.md` -- CPU, memory, disk, billing
- `sandboxes.md` -- creation, exec, snapshots, named sandboxes
- `examples.md` -- end-to-end code examples
