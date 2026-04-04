<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Phase 6: Implement (~20% of effort)

Execute the amended plan. Key efficiency patterns:

## Parallel agent dispatch for independent scripts

If the plan has N independent new scripts, dispatch up to 5 agents in parallel:

```
Agent(name="script-a", mode="bypassPermissions", prompt="Write script at {path}. [full spec]...")
Agent(name="script-b", mode="bypassPermissions", prompt="Write script at {path}. [full spec]...")
```

Each agent prompt MUST include:
1. Full import pattern from the project (`from variant_evidence_core import ...`)
2. Output path convention (`data/wgs/analysis/{stage}/`)
3. JSON output structure
4. `validate()` function spec
5. "Do NOT commit — I will commit after review"

## Multi-agent commit safety

Check `OTHER ACTIVE AGENTS` in session context. If other sessions are running:
- Commit after EACH script (not in a batch) — parallel agents may sweep uncommitted edits
- Or use `isolation: "worktree"` on implementation agents to avoid conflicts
- Run `git status` before each commit to verify only your files are staged

(Source: dispatch-research skill update 2026-03-26 — parallel agent commit race condition)

## Post-agent cleanup

After agents complete:
1. `ruff check --select F821,F401,F841,E741` on all new files
2. Fix any Pyright errors (agents often miss type issues on `max()`, conditional imports)
3. Commit each script separately with semantic messages
4. Register stages in the stage registry
5. Run canary/regression gate

## Commit pattern

```
[scope] Wire {analysis name} — {what it does}

{1-3 line body: key design choice, smoke test result}
```

One commit per script. Final commit for stage registration + codebase map update.

## Execution status truthfulness

Do not collapse build state into a single word.

- `implemented`: files, wiring, and registrations exist locally
- `locally verified`: imports/tests/CLI checks passed on the local machine
- `runtime-pending`: detached Modal jobs, benchmarks, or full reruns have not completed

If any runtime-critical remote step is still pending, do not write `executed` or `completed`
in `CYCLE.md`, plans, or status summaries. Spell out what ran and what did not run yet.

## CYCLE.md Write-Back

If `CYCLE.md` exists in the project root, append completed items to `## Completed This Session` so `/research-cycle` doesn't re-discover them:
```
- **{name}** ({commit}) — {one-line description}
```
One line per implemented analysis. This coordinates the growth lane — novel-expansion is a deep batch run, research-cycle is incremental. Without write-back, research-cycle's discover phase may re-propose work that was just built.
If work is only implementation-complete, log it as implemented plus runtime-pending detail rather than as fully executed.
