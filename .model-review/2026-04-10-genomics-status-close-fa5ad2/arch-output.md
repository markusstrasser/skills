## 1. Assessment of Strengths and Weaknesses

**Strengths:**
*   **Single-Shot Architectural Probe:** `_probe_volume_impl` and `_probe_volume_sdk_impl` correctly collapse N network calls into a single batch query across the Modal volume. This directly serves the constitutional directive: *Architectural enforcement beats reminders* by structurally bypassing Modal's SDK timeout vulnerabilities on highly partitioned directories.
*   **Progress Coercion Contract:** `coerce_snapshot` and `_format_progress_suffix` elegantly handle both v1 (legacy dict) and v2 (`ProgressSnapshot`) runtime contracts without breaking.
*   **Active Runtime Preferencing:** `_prefer_runtime_row` accurately handles clock skew and prioritizes high-signal log payloads over blank worker receipts, giving the operator an honest view of the runtime edge.

**Weaknesses (Mismatch Logic Regressions):**
*   **False Positive on `SKIPPED` Stages:** In `_reconcile_stage_rows` (line 911), `receipt_status in {"success", "completed", "skipped"}` triggers a `bridge_failed` mismatch if `local_state` is missing. A stage skipped due to `applicability_blocked` inherently has no local outputs. Treating it as a failed bridge generates fatal noise.
*   **False Positive on Stages Without Outputs:** In `_local_bridge_state_for_stage` (line 850), if `not stage.outputs` evaluates to true, it returns `available: False`. This forces any DB-only or API-only stage to permanently display as `bridge_failed` upon success.
*   **SKILL Contract Violation for `incomplete_attempt`:** `SKILL.md` defines `incomplete_attempt` as: *"control plane expects active work, but there is no matching runtime signal."* However, line 916 maps `failed`, `manual`, and `dataset_blocked` to `incomplete_attempt`. A manual intervention or blocked dataset is explicitly *not* expecting active work.
*   **Conflation of Healthy Runs and Mismatches:** If `runtime_source` is active and `local_state` is missing (line 895), `mismatch_class` is assigned `"running_signal"`. If the control plane also says `"running"`, this isn't a mismatch; it's the nominal happy path for a running stage. Placing this in the reconciliation list creates visual noise that buries actual drift.

## 2. What Was Missed

*   **Test Coverage for Terminal Non-Success States:** `test_runtime_state.py` misses validation for `SKIPPED`, `MANUAL`, and `DATASET_BLOCKED` reconciliation rows. The test `test_reconcile_stage_rows_flags_bridge_failed_when_receipt_is_terminal` only asserts `"SUCCESS"`.
*   **Orphan Execution Detection:** The `running_signal` branch checks if a runtime source exists but completely ignores `control_plane_status`. It misses the opportunity to detect *orphan runs* (where Modal is actively burning compute, but the control plane thinks the run is dead/cancelled).
*   **Stale Local Data vs. Expected Missing:** The `local_stale` class triggers if `local_state.get("available")` is true but the run failed or is blocked. This is correct, but it misses the distinction between "local data exists from a *previous* successful run" versus "local data is polluted." 

## 3. Better Approaches

| Issue | Approach | Refinement |
| :--- | :--- | :--- |
| **Skipped Stages Flagged as `bridge_failed`** | **Agree** (with fix) | Separate `skipped`. If a stage is skipped due to `output_exists`, local data should be verified. If skipped due to `applicability_blocked` (or similar), it should bypass local output checks entirely. |
| **Output-less Stages Flagged as `bridge_failed`** | **Upgrade** | Do not return `available: False` if a stage intentionally lacks outputs. Return `available: True, detail: "no outputs expected"`. This satisfies the bridge check. |
| **`manual/failed` mapped to `incomplete_attempt`** | **Disagree** (with current implementation) | Introduce `blocked_state` or `terminal_failure` as explicit mismatch classes. Do not overload `incomplete_attempt`. Update `SKILL.md` to reflect these distinct triage categories. |
| **Healthy `running` flagged as `running_signal` mismatch** | **Upgrade** | Wrap the `runtime_source` check: `if control_plane_status != "running": mismatch_class = "orphan_runtime"`. If `cp == "running"`, do not assign a `mismatch_class` unless local data implies a collision (`local_stale`). |

## 4. What I'd Prioritize Differently

These are the top 5 most impactful fixes to restore operator trust in the reconciliation surface:

1.  **Fix Orphan Run Detection (Stop `running_signal` False Positives):**
    *   *Change:* Update `_reconcile_stage_rows` line 893 to only flag `running_signal` (or better, `orphan_run`) if `control_plane_status != "running"`.
    *   *Verification:* A stage running happily in both CP and runtime should not appear in the RECONCILIATION output block at all.
2.  **Fix `SKIPPED` Stage False Positives:**
    *   *Change:* Remove `"skipped"` from the condition at line 911. Handle `"skipped"` separately: if `local_state` is missing, do not flag as `bridge_failed` unless `skip_reason` explicitly implies files should exist.
    *   *Verification:* A run with `chip_screening` skipping due to `applicability_blocked` stays green and out of the reconciliation list.
3.  **Fix the `incomplete_attempt` SKILL Violation:**
    *   *Change:* Modify line 916. If CP is `failed`, use `mismatch_class = "failed_cp"`. If CP is `manual`/`dataset_blocked`, use `mismatch_class = "blocked_cp"`.
    *   *Verification:* `SKILL.md` definitions align precisely with the Python output.
4.  **Fix Output-less Stage Bridge Failures:**
    *   *Change:* In `_local_bridge_state_for_stage`, change `if stage is None or not stage.outputs:` to return `{"available": True, "detail": "no outputs defined"}` if `stage.outputs` is empty but `stage` exists.
    *   *Verification:* Pure-DB stages don't throw `bridge_failed` upon success.
5.  **Expand `test_runtime_state.py` Reconciler Tests:**
    *   *Change:* Add `test_reconcile_stage_rows_ignores_blocked_skips` and `test_reconcile_stage_rows_flags_orphan_runtime`.
    *   *Verification:* `pytest tests/test_runtime_state.py` covers all paths through `_reconcile_stage_rows`.

## 5. Constitutional Alignment

*   **Principle 3 (Operator surfaces are in scope):** *Well-served.* Building a dedicated status/reconciliation tool to prevent "spelunking raw files and Modal logs" is directly aligned with the project goals.
*   **Principle 4 (Fail loud on drift):** *Violated.* By surfacing false positives for `skipped` stages, `manual` states, and healthy `running` states, the script creates alert fatigue. "Fail loud" requires high precision; otherwise, operators learn to ignore the alarm, allowing true drift to hide.
*   **Principle 5 (Architectural enforcement beats reminders):** *Well-served.* Bypassing `modal volume ls` in favor of a batched `probe_volume.remote()` function structurally solves the operator timeout problem.
*   **Principle 2 (One path owns meaning):** *Well-served.* The status script explicitly delineates truth surfaces (`orchestrator truth`, `worker outcome`, `local usability`), respecting that stage artifacts are compute paths, not the final meaning.

## 6. Blind Spots In My Own Analysis

*   **The Intent of `running_signal`:** I am assuming the `RECONCILIATION` block is designed *strictly* for mismatches/errors because the variable is literally named `mismatch_class` and the other entries (`bridge_failed`, `stale_receipt`) are errors. If the user intentionally designed `running_signal` as a "positive confirmation" class to prove the active Modal app matches the DB, then my recommendation to suppress it is wrong (though the variable naming is still highly misleading).
*   **`STAGES` Output Requirements:** I noted that `not stage.outputs` will trigger `bridge_failed`. I am assuming there are stages in this pipeline that legitimately have no file outputs (e.g., API callers, DB writers). If the repo's architectural invariants *require* every stage to have at least one file output, then `not stage.outputs` is structurally impossible or implies a badly configured stage, making `bridge_failed` arguably correct.