---
name: tick
description: "Run one orchestrator tick — process next pending task and show queue status. Designed for /loop usage: `/loop 5m /tick`."
user-invocable: true
context: fork
allowed-tools:
  - Bash
  - Read
effort: low
---

# Orchestrator Tick

Run one orchestrator tick and report status. Designed for `/loop 5m /tick`.

## Execute

```bash
uv run python3 ~/Projects/meta/scripts/orchestrator.py tick 2>&1
```

## Status

```bash
uv run python3 ~/Projects/meta/scripts/orchestrator.py status 2>&1 | head -30
```

## Report

One paragraph: what ran (if anything), what's next in queue, any failures. If nothing pending, say so and stop.

$ARGUMENTS
