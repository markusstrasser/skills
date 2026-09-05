<!-- Close-mode workflow. Load only after selecting non-trivial plan closeout. -->

# Plan Close Review

Use after implementing a plan to check new behavior, migration completion, and the design. Skip this workflow for trivial plans (<30 lines, one function, obvious correctness), research/analysis that produces no code, and config/data-only changes with no logic changes. The historical rationale is in [History](../references/history.md).

## Phase 0: Establish the exact closeout scope

Separate code closure from data readiness: run the project's `validate-code` for code/architecture closure and `validate-data` separately when the project has a data plane. Do not combine them into one verdict.

If the change touches generated docs, count-bearing surfaces, or files covered by `check-claude-md`, run the project's `just sync-generated-docs`. If it claims migration completion, prove the caller migration and enumerate any retained live compatibility boundaries with their reasons and removal conditions.

Build a packet from the actual diff and touched files rather than a prose summary:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" \
  --output .model-review/plan-close-context.md
```

For a clean worktree or earlier committed changes, select an explicit range. `--since` includes the named first commit through HEAD:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" --since <first-session-commit> \
  --output .model-review/plan-close-context.md

# Equivalent explicit range selection when both refs are known:
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" --base <old-ref> --head <new-ref> \
  --output .model-review/plan-close-context.md
```

Repeated `--file` may select concrete review files. Inspect the packet and its sidecar before dispatch: non-empty content, correct commit/file scope, and `review_targets.diff_target` for code-review versus `design_target` for critique. Use one packet per independently reviewed subpart; the parent merges all subparts. Do not let ambient peer changes define the scope.

## Phase 1: Check the new logic

Identify new behavior from the plan commits and check its contracts. Use existing tests when they establish the behavior; add meaningful tests for uncovered new logic, boundary cases, error paths, and invariants. Run them and fix failures before model review. The target is a trusted check of the contract, not a coverage percentage or tests mirroring the implementation.

For a concrete bug found later, prove that its regression test fails on the pre-fix code and passes after the fix. Use an isolated worktree or saved pre-fix file snapshot; never bare `git stash` in a shared checkout.

## Phase 2: Review each layer once

**Diff layer:** run `/code-review high` over the plan's commits. Composer is that skill's default provider. Do not also run a critique `composer` axis on the diff; `--all-providers` recall mode belongs only to the diff scope. Verify scout findings against the code before applying them, and finish disposition before the closeout commit.

Include an execution-grounded instruction to run the changed code paths where the reviewer has tools, or run them locally and provide the evidence. Record what actually ran; packet-only judgment is not execution.

**Design layer:** use deterministic triage in `model` mode for the initial review. `close` mode is the final readiness gate and requires an existing verified disposition, so it cannot bootstrap the first review.

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py triage \
  --repo "$(pwd)" --packet .model-review/plan-close-context.md --mode model

uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --dispatch-manifest .model-review/dispatch.json \
  --context .model-review/plan-close-context.md \
  --topic "$TOPIC" --project "$(pwd)" \
  --question "Review plan closeout's design and migration premises only; the diff layer is reviewed separately."
```

Stop on blockers. Use the manifest produced for this packet; explicit CLI flags override its fields. Triage supplies `extract` and `verify`. [Dispatch](../references/dispatch.md) contains the precise manifest, `repo|packet` scope, subscription, timeout, and cross-repo-root contracts.

Read every axis output. Fact-check and disposition every finding using [Verification](verification.md). Inspect `coverage.json` for packet drops, axis coverage and extraction/verification totals. Automated anchor verification is not a semantic verdict.

### Rank, resolve inconclusive findings, and escalate when indicated

After extraction/verification:

```bash
REVIEW_DIR=.model-review/<topic-hash>  # exact directory from model-review output
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py rank --review-dir "$REVIEW_DIR"
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py inconclusive \
  --review-dir "$REVIEW_DIR" --repo "$(pwd)"
```

`orchestrator-top.json` gives the top eight in reading order, cross-model findings first. It is not a cap: fix every confirmed/corrected finding within scope and give a specific reason for any deferral. Rows with `resolved_deterministic: true` can be deprioritized as already resolved, not silently lost.

If `escalation-recommendation.json` requests cross4 on the same packet, follow the evidence-backed escalation; rank has already identified the trigger. Optional cross2/cross4 `--cross-talk` is described in [Dispatch](../references/dispatch.md). Do not rerun a review merely to obtain another opinion after the required checks pass.

## Phase 3: Close the verification gaps

For each confirmed bug, determine why the earlier checks missed it. Repair the test gap or add a regression test, then verify it against pre-fix and fixed code in isolation. The bug-class table below gives examples; it is not a mandatory new test suite for unrelated changes.

Before the closeout commit, run the readiness gate against the verified review directory:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py triage \
  --repo "$(pwd)" --packet .model-review/plan-close-context.md \
  --mode close --review-dir "$REVIEW_DIR"
```

Stop on blockers, including missing verification evidence, dead closeout references, oversize packets, or the forbidden Composer design axis. The matching packet's existing model review satisfies the design pass; passing the readiness gate does not require dispatching it again.

Then run the deterministic integration audit to check that the diff did not implement findings marked HALLUCINATED:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/integration_audit.py \
  --review-dir "$REVIEW_DIR" --repo "$(pwd)" \
  --plan .claude/plans/<plan>.md
```

Exit 1: stop before committing. Inspect warnings manually. This joins review artifacts to the git diff; it does not replace behavioral verification.

## Phase 4: Commit and record the outcome

Commit verified fixes and tests with the project's shared-checkout discipline. Update the plan's implementation status with actual commit hashes. Run the required code validation, and report data validation separately when applicable.

After fix commits, link confirmed findings to them:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/outcome_link.py \
  --repo "$(pwd)" --review-dir "$REVIEW_DIR" --since HEAD~30
```

Inspect `outcome-link.json`: `linked_anchor` is evidence-grade; `linked_file` is only a weak candidate. Summarize what the review found, how the behavior was checked, validation results, unresolved findings and any retained live compatibility boundaries. Do not claim full migration while a live boundary remains unnamed.

## Bug Class Table

From calibration data (suspense accounts + prior reviews):

| Bug class | Example | Test pattern |
|-----------|---------|-------------|
| Silent env var bypass | Typo in config value disables gate | Test with invalid config values |
| Dedup key too coarse | Different-severity items collapsed | Test with items sharing key but differing in another field |
| Wrong categorical bucket | Enum member routed to wrong category | Test each enum value maps correctly |
| Misleading diagnostic | Error message says "under" when it's "over" | Test error message content, not just presence |
| Gate bypass on missing input | No manifest -> gate skipped entirely | Test with None/missing inputs in enforce mode |
| Silent fallback on unknown enum | New enum value falls to default | Test with a mock unknown value |

## Migration Completion Checklist

Only claim a migration is complete if all of these are true:

Default target: zero remaining compatibility boundaries. Any exception needs a
named live dependency and removal condition.

1. **Active callers migrated** — every live caller in scope uses the new contract.
2. **Dead wrappers removed** — not just bypassed.
3. **Remaining compatibility boundaries named** — file + purpose + removal condition.
4. **Tests updated intentionally** — compatibility tests were rewritten or deleted on purpose, not left failing by accident.
5. **No closure overclaim** — if any live compatibility boundary remains, state "active-path migration complete" or equivalent, not "repo fully migrated."

## What Makes a Good "New Code" Test

Bad test (regression-style):
```python
def test_bundle_builds():
    """Verify bundle builds without error."""
    bundle = build_case_bundle(...)
    assert bundle is not None  # passes with any bug
```

Good test (contract-style):
```python
def test_trial_balance_rejects_imbalanced():
    """assert_trial_balance raises when counts don't sum."""
    audit = BundleAudit(
        sample_id="test",
        triage_count=100,
        trial_balance=TrialBalance(
            total_obligated=100,
            reported=10, suppressed=20, qc_discard=5,
            benign_common=10, out_of_scope=0, not_assessed=0,
        ),  # sums to 45, not 100
    )
    os.environ["TRIAL_BALANCE_GATE"] = "enforce"
    with pytest.raises(TrialBalanceError):
        assert_trial_balance(audit)
```

The difference: the bad test verifies the system runs. The good test verifies the system enforces its contract.
