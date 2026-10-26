# Modal references index

<!-- moved-from modal/SKILL.md L189-213 2026-10-26 -->
## Reference Docs (original SKILL.md list) (moved verbatim from SKILL.md)

> Moved verbatim from modal/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

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
- `status-reconciliation.md` -- question -> truth surface -> mismatch class
- `attribution.md` -- question/source/status/spend reporting pattern
- `sandboxes.md` -- creation, exec, snapshots, named sandboxes
- `examples.md` -- end-to-end code examples
- `checkpointing.md` -- read when writing `@modal.exit`, `.SUCCESS` sentinels, mid-step checkpoints
- `preemption.md` -- read when sizing retries/chunks, considering `nonpreemptible`, or a stage won't schedule
- `budget-and-spend.md` -- read when querying spend, writing a budget watchdog, or after a budget kill
- `gotchas.md` -- read when debugging any odd platform behavior (durable gotchas, C1–C11, deploy zombies)
- `changelog.md` -- read when bumping Modal, checking a dated platform note, or adopting a 1.5.x feature
- `known-issues.md` -- read when a failure matches a dated incident (memento helper appends here)
- `marker-pdf-extraction.md` -- read when running Marker PDF→Markdown on Modal
