<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Phase 3: Research (~25% of effort)

Dispatch parallel research workers on explore ideas. This is where F1, F2, and
F3 hit hardest, with F4/F5 as common secondary failures.

## Pre-dispatch Checklist (Mandatory)

For each idea being researched:

- `F1 gate`: grep the repo for the concept first
- `F1 gate`: check the existing concept list
- `F4 gate`: check the duplicate-ID ban list
- give the worker a specific output file path
- require incremental, file-first writes
- keep scope narrow enough for the budgeted search count

## Tool Schema Guardrails (F5)

- `mcp__scite__search_literature`:
  - `title` is a scalar string per call
  - pass multiple titles as repeated calls, not one array payload
- Brave search tools:
  - keep the query focused, then open/crawl selected URLs
- Perplexity:
  - set `search_context_size` explicitly
  - use recency filters only when they matter

## Research Dispatch Patterns

Prefer stable worker surfaces over raw model command recipes:

- tool/paper evaluation:
  - use a shared research helper or a file-first research worker
  - output goes directly to the target memo file
- codebase analysis:
  - use a dedicated researcher/explore worker
  - keep one idea per worker

Do not teach prompt-only file creation or raw ad hoc model shell blocks here.
If a reusable research dispatch helper is missing, add it once to the shared
stack instead of copying a new local recipe into `upgrade`.

## Parallel Dispatch Strategy

- up to 3 researcher workers in parallel
- up to 2 GPT-backed shared research/review calls in parallel
- each worker covers one idea, not the whole frontier

## Post-Research Verification

After workers complete:

1. Check output file sizes.
2. Recover any suspiciously tiny output from the worker transcript or artifact log.
3. Discard “discoveries” that already existed in the concept list.

## Survivor Calibration (F6)

Do not target a fixed survivor count.

- default expectation for mature frontiers: `0-2` survivors
- `1` strong survivor is a good pass
- `0` survivors is acceptable and should be logged explicitly
- `3+` survivors should be treated as unusual and justified

If the search only produces reframings, caveats with no caller, or operator
duplicates, stop and log a no-survivor pass instead of padding.
