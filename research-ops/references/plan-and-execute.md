<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Plan and Execute

## Phase 4: Plan structure

```markdown
# Audit Findings — Fix & Refactor Plan

**Session:** YYYY-MM-DD | **Project:** <name>

## Context
<1-2 sentences on what audits found, what was verified>

## Phase N: <Category> (<impact level>, <scope estimate>)

### NA. <Specific fix>
**Files:** `path/to/file.py:lines`
- What to change
- Why (cite the verified finding)
- How (brief implementation note if non-obvious)

## Execution Order
<Phases ordered by: bugs first, then drift, then structural, then cleanup>

## Verification
<How to confirm fixes worked — specific commands>
```

## Plan principles

1. **Group by impact** — bugs before drift before hygiene
2. **Cite the verified finding** for each fix — traceability from audit -> plan -> commit
3. **Include verification commands** — how to confirm each fix worked
4. **Estimate scope honestly** — "~10 min" not "trivial"
5. **Flag deferred items** — things found but not worth fixing now (with reason per item, not a batch cutoff)
6. **Phase boundaries** — commit after each phase, not one giant commit
7. **Fix ALL verified findings** — don't self-select "top N" and implicitly drop the rest. Every confirmed finding gets a plan entry. If something must be deferred, give it an explicit disposition with a reason.

## Plan approval

Present the plan to the user. Wait for approval before executing. If the plan has 3+ phases, offer to execute phase-by-phase with checkpoints.

## Phase 5: Execution principles

1. **Read before editing** — always read the target file before modifying
2. **One logical change per commit** — granular semantic commits
3. **Commit after each phase** — not one big commit at the end
4. **Run tests after code changes** — `uv run pytest tests/` or equivalent
5. **Verify each fix** against the plan's verification commands
6. **Fix the neighborhood when it unblocks progress** — incidental cleanup (lint markers, related bugs, broken adjacent code) is part of the work. The only thresholds: split when >100 lines or when the cleanup touches a public API/contract.
7. **Parallel where possible** — use Agent tool for independent file edits
8. **Verify paths before fixing paths** — when fixing a wrong file path, run `find` for actual location + `head -5` to check structure before editing. Don't guess from directory names (3-iteration failure observed)
9. **Run the script after each fix** — don't batch all fixes then test. Optional fields with explicit `None` values, wrong JSON structures, etc. only surface at runtime

## Multi-agent commit safety

If `OTHER ACTIVE AGENTS` was reported at session start, other agents may `git add` your uncommitted edits under wrong commit messages. Mitigations:
- **Commit after each fix**, not batched at the end of a phase
- Or use `isolation: worktree` for the entire dispatch-research session
- Never leave edited files uncommitted while background agents are running

## Commit message format

Reference the audit finding:
```
[scope] Verb thing — why (from audit)
```

## Post-execution

- Verify no uncommitted changes remain
- Run full test suite
- Summarize: N findings addressed, M commits, any deferred items

## MAINTAIN.md Integration

If `MAINTAIN.md` exists in the project root (project uses `/maintain`), **you must** also:
- Append to `## Log`: `YYYY-MM-DD | dispatch-research | N findings, M applied, D deferred | [commit range]`
- Append deferred findings to `## Queue` with IDs continuing the M00N sequence
- Append applied fixes to `## Fixed`
- Never write placeholder commit refs such as `uncommitted`. If code commits are likely in the same session, defer the `MAINTAIN.md` update until the real commit hash or range exists, then write the final entries in one pass.

This feeds results into the SWE quality lane so `/maintain` can track them.
