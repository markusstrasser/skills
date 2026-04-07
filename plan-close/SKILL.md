---
name: plan-close
description: Close out a completed plan with tests, cross-model review, and coverage hardening. Use this after finishing implementation of a plan from `.claude/plans/` — when commits are done but before marking the plan as DONE. Also use when the user says "close the plan", "plan is done", "finish up the plan", "review and close", or references completing a multi-phase implementation. The skill ensures new code is tested, reviewed, and that review findings feed back into test coverage.
---

# Plan Close

After a plan's implementation is committed, there's a gap between "code works" and "code is correct." Regression tests (canaries, IR invariants) verify existing behavior doesn't change — but they're blind to bugs in new code paths. This skill closes that gap.

## Why This Exists

Three independent lines of evidence:

1. **Empirical (suspense accounts, 2026-04-07):** GPT-5.4 found 6 confirmed bugs in freshly committed code. All 74 canary tests and 11 IR invariants passed. The bugs were in new functions with zero test coverage: env var validation, dedup logic, enum bucketing, diagnostic messages.

2. **Failure Mode 15 — Silent Semantic Failures** (MAS-FIRE, arXiv:2602.19843): Reasoning drift, wrong buckets, misleading diagnostics propagate without runtime exceptions. No crash, no test failure, wrong output. "Mitigation requires output validation or multi-model cross-check."

3. **Failure Mode 16 — Reward Hacking** (TRACE, arXiv:2601.20103): Agents evaluated by test passage may hack the test rather than solve the task. "Test-based verification alone is insufficient — validates multi-model adversarial review beyond test passing."

All existing model reviews in the knowledge base are pre-implementation (reviewing plans). This is the first post-implementation pattern: review the code that was actually written, not the plan for writing it.

## The Workflow

### Phase 1: Write Tests for New Code

Before asking another model to find your bugs, try to find them yourself.

1. **Identify new functions/logic** from the plan's commits:
   ```bash
   git log --oneline --since="<plan start>" -- <affected files>
   git diff <first-commit>^..<last-commit> --stat
   ```

2. **For each new function**, write unit tests that cover:
   - Happy path (expected input → expected output)
   - Edge cases (empty input, None, boundary values)
   - Error paths (what should raise, what should warn)
   - The invariant the function is supposed to enforce

3. **Run the tests.** Fix failures. Commit.

The goal isn't 100% coverage — it's testing the *contract* of each new function. If `assert_trial_balance()` is supposed to raise on imbalance, there should be a test that creates an imbalanced audit and verifies it raises.

### Phase 2: Cross-Model Review

Now that you've written what you think the tests should be, get a second opinion on what you missed.

1. **Run `/model-review`** on the plan's diff. Focus the review on:
   - Correctness of new logic
   - Silent failures and edge cases
   - Semantic/architectural issues
   - Things that pass tests but are still wrong

2. **Fact-check every finding** against actual code. Models hallucinate file paths, function names, and "missing" features that already exist.

3. **Disposition each finding:** CONFIRMED / REJECTED / DEFERRED with reason.

4. **Fix confirmed findings.** Commit.

### Phase 3: The Caught-Red-Handed Loop

This is the payoff. For each confirmed finding from the model review:

**Ask:** Would any of my Phase 1 tests have caught this?

- **If yes** → the test exists but the bug slipped through. The test has a gap. Fix the test.
- **If no** → you didn't test this path at all. Write a test that would have caught it.

This is not punitive — it's calibration. Every bug the model catches that your tests didn't is a signal about what your testing instincts miss. The new tests make the gap smaller next time.

After writing the new tests, run them against the *pre-fix* code (stash the fixes, run tests, verify they fail, unstash). This confirms the tests actually detect the bug — not just that they pass on correct code.

```bash
# Verify new test catches the bug
git stash
pytest tests/test_<new>.py -x  # should FAIL
git stash pop
pytest tests/test_<new>.py -x  # should PASS
```

### Phase 4: Close the Plan

1. Commit the new tests.
2. Update the plan's Implementation Status table — all items marked DONE with commit hashes.
3. Run the project's validation gate (`just validate` or equivalent).
4. Summarize what the review found and what tests were added.

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

The difference: the bad test verifies the system runs. The good test verifies the system enforces its contract. The model review finds bugs in contracts; tests should too.

## Typical Bug Classes the Review Catches

From calibration data (suspense accounts + prior reviews):

| Bug class | Example | Test pattern |
|-----------|---------|-------------|
| Silent env var bypass | Typo in config value disables gate | Test with invalid config values |
| Dedup key too coarse | Different-severity items collapsed | Test with items sharing key but differing in another field |
| Wrong categorical bucket | Enum member routed to wrong category | Test each enum value maps correctly |
| Misleading diagnostic | Error message says "under" when it's "over" | Test error message content, not just presence |
| Gate bypass on missing input | No manifest → gate skipped entirely | Test with None/missing inputs in enforce mode |
| Silent fallback on unknown enum | New enum value falls to default | Test with a mock unknown value |

## When NOT to Use This Skill

- **Trivial plans** (< 30 lines of changes, single function, obvious correctness). Just commit and move on.
- **Research/analysis plans** that don't produce code. Nothing to test.
- **Plans that only modify config/data** with no logic changes.

## Interaction with Other Skills

- **`/model-review`** — called in Phase 2. Plan-close orchestrates when and how to call it.
- **`/verify-findings`** — optionally called after model review to fact-check file-specific claims.
- **`/retro`** — complementary. Retro reflects on the session; plan-close hardens the code.
