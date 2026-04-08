<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Deferred Re-Triage (`--deferred`)

Second pass on deferred items from a prior project-upgrade run. No model scan -- starts from the existing deferred list in CYCLE.md (or equivalent task queue). Skips Phases 1-3 entirely.

## Why This Exists

Deferred items from model reviews have a ~40-50% noise rate because:
- Models hallucinate missing features (the feature was already implemented)
- Models propose registries/abstractions for 3-item collections (overengineering)
- Models flag "drift" in code with no incident history
- Scope estimates assume per-file changes when a single injection point exists
- Deferrals made under context pressure use vague triggers ("when X causes a bug")

Fresh exploration against actual code state resolves these.

## Workflow

**6a. Load deferred items.** Read the deferred section from CYCLE.md or the prior run's triage file. Each item has an ID, description, category, and trigger condition.

**6b. Explore each item.** For each deferred item, dispatch Explore agents to check:
- Does the problem actually exist in the current codebase?
- Has it already been fixed since the deferral?
- Is the trigger condition met?
- What is the real scope? (Find the injection point -- often smaller than the description implies.)

Parallelize exploration across items. This is read-only -- no code changes yet.

**6c. Re-triage with three dispositions:**

| Disposition | Criteria | Action |
|-------------|----------|--------|
| **KILL** | Problem doesn't exist, feature already implemented, overengineering for current scale, blocked on another killed item | Remove from queue. Document why -- prevents re-proposal. |
| **EXECUTE** | Problem is real, trigger is met, scope is tractable | Plan and execute in this session. |
| **KEEP-DEFERRED** | Problem is real but has a concrete blocker (missing data, architectural dependency, needs human decision) | Leave in queue with updated trigger. "Large scope" alone is NOT a valid blocker -- agents handle scope. |

**Evidence requirements:**
- **KILL** must cite what was checked (grep output, file read, feature location)
- **EXECUTE** must have verified the problem exists in current code
- **KEEP-DEFERRED** must name a specific blocker, not "needs more design"

**6d. Present disposition table to user.** Same approval gate as Phase 4.

**6e. Execute all EXECUTE items.** Same per-finding loop as Phase 5: read -> fix -> verify -> commit. Order by impact (bugs before cleanup).

**6f. Update queue.** Remove KILL and EXECUTE items from deferred section. Update KEEP-DEFERRED items with refined triggers. Log the session.

## Key Practices

1. **Explore before disposition.** Never re-triage from the description alone. Read the actual code. Descriptions from model reviews are hypotheses, not facts.

2. **Kill is the most valuable disposition.** Every killed item is a future agent session not wasted on a phantom problem. The anti-entropy value of removing noise from a task queue is high.

3. **Find the injection point.** "Metadata envelope for 96 scripts" is a 3-line change if there's a shared `finalize()` function. "Consolidate definitions across 15 files" is a mechanical migration. Scope estimates from model reviews assume per-file surgery -- check for centralized injection points first.

4. **Bug-first ordering.** If exploration reveals an actual bug among the deferred items (not just cleanup), execute it first. It's the highest-impact item regardless of its original priority label.

5. **No scope-based deferrals when agents execute.** In agent-developed codebases, the only valid KEEP-DEFERRED reasons are: (a) missing external data, (b) needs human decision on semantics, (c) blocked by another item that isn't ready. "Too many files to touch" is not a blocker -- it's a parallelizable task.

6. **Mechanical migrations -> worktree agents.** When an EXECUTE item is "replace X with Y in N files" (e.g., consequence set consolidation), dispatch a worktree agent. The parent focuses on items requiring judgment.

## Expected Yield

From observed runs:
- ~40% of deferred items are KILL (noise)
- ~50% are EXECUTE (trigger met, scope tractable)
- ~10% are genuine KEEP-DEFERRED (real blocker)
- Bug discovery rate: ~1 real bug per 10 deferred items (hidden among cleanup)
