# Review Findings — 2026-04-10

**14 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** Evidence truncation and unreliable liveness proxy in SDK probe
   Category: logic | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   The SDK probe path caps scanning to 20 stages based on directory mtime. In large repositories, this risks excluding active work. Furthermore, parent directory mtime is an unreliable proxy for liveness as it does not necessarily update when nested receipt or log files are modified.
   File: 
   Fix: Remove the 20-stage cap from the collection phase and base selection on the freshness of actual receipt or log files.

---

2. **[HIGH]** Missing validation for high-risk reconciliation branches
   Category: missing | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   Automated tests are missing for critical scenarios including large stage counts (>20), terminal state disagreements, and explicit SDK/helper implementation parity.
   File: 
   Fix: Add a comprehensive test matrix covering all permutations of control plane, worker, and local states.

---

3. **[HIGH]** Skipped stages are incorrectly flagged as bridge failures when no local outputs are expected
   Category: logic | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review points to `_reconcile_stage_rows` line 911, where `receipt_status in {"success", "completed", "skipped"}` can trigger a `bridge_failed` mismatch when `local_state` is missing. This creates a false positive for skipped stages such as those skipped for `applicability_blocked`, because those stages inherently may not produce local outputs. The reviewer notes this generates fatal operator noise rather than real drift.
   File: 
   Fix: Handle `skipped` separately from successful terminal states. Only require local outputs for skipped stages when the skip reason implies outputs should already exist (for example `output_exists`), and bypass bridge checks for skip reasons like `applicability_blocked`.

---

4. **[HIGH]** Semantic divergence between SDK and helper probe implementations
   Category: architecture | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The system maintains two separate implementations for volume probing (SDK vs helper) which have inconsistent behaviors regarding stage limits and log filtering, creating architectural drift and non-equivalent 'truth' surfaces.
   File: 
   Fix: Unify the probing semantics or enforce equivalence through normalized parity tests on synthetic volume trees.

---

5. **[HIGH]** Stages with no declared outputs are permanently treated as bridge_failed
   Category: logic | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review cites `_local_bridge_state_for_stage` line 850, where `if not stage.outputs` returns `available: False`. For stages that intentionally have no file outputs, such as DB-only or API-only stages, this means a successful receipt will still reconcile as `bridge_failed`. The reviewer explicitly calls this a permanent false positive for output-less stages.
   File: 
   Fix: When the stage exists but `stage.outputs` is empty, return a positive bridge state such as `{"available": true, "detail": "no outputs expected"}` instead of `available: False`.

---

6. **[HIGH]** Reconciliation misses orphan-runtime detection because it ignores control-plane status
   Category: missing | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review separately notes that the `running_signal` logic only checks whether a runtime source exists and does not use `control_plane_status`. That means it fails to detect orphan executions where Modal is still actively consuming compute even though the control plane thinks the run is dead, cancelled, or otherwise not running.
   File: 
   Fix: In the runtime-signal branch, compare runtime activity against `control_plane_status` and emit a distinct mismatch such as `orphan_runtime` when runtime is active but the control plane is not `running`.

---

7. **[MEDIUM]** `incomplete_attempt` is overloaded for terminal failed and blocked control-plane states
   Category: logic | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review says `SKILL.md` defines `incomplete_attempt` as meaning the control plane expects active work but there is no matching runtime signal. However, `_reconcile_stage_rows` line 916 reportedly maps `failed`, `manual`, and `dataset_blocked` to `incomplete_attempt`. That violates the documented meaning because manual intervention and blocked datasets do not imply expected active work.
   File: SKILL.md
   Fix: Introduce distinct mismatch classes for terminal failure and blocked/manual states, such as `failed_cp` and `blocked_cp` or similar, and update both the reconciliation code and `SKILL.md` to keep the contract aligned.

---

8. **[MEDIUM]** Tests do not cover skipped, manual, dataset-blocked, or orphan-runtime reconciliation paths
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review says `test_runtime_state.py` lacks validation for `SKIPPED`, `MANUAL`, and `DATASET_BLOCKED` reconciliation rows, and that `test_reconcile_stage_rows_flags_bridge_failed_when_receipt_is_terminal` only asserts the `SUCCESS` path. It also recommends adding explicit coverage for ignored blocked skips and orphan runtime detection.
   File: test_runtime_state.py
   Fix: Add reconciler tests for blocked skip behavior, manual and dataset-blocked states, and orphan runtime detection, including cases where healthy running stages should not appear in reconciliation.

---

9. **[MEDIUM]** Incorrect 'incomplete_attempt' classification for non-running control plane
   Category: bug | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   _reconcile_stage_rows() assigns 'incomplete_attempt' when the control plane is in 'failed', 'manual', or 'dataset_blocked' states, which contradicts the skill definition requiring an active work expectation.
   File: 
   Fix: Restrict 'incomplete_attempt' assignment to cases where control_plane_status is 'running'.

---

10. **[MEDIUM]** Silent drift between control plane and worker terminal states
   Category: missing | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   Current reconciliation logic fails to surface cases where the control plane and worker have reached conflicting terminal states (e.g., CP 'failed' but worker 'success'), violating the 'Fail loud on drift' principle.
   File: 
   Fix: Add explicit drift detection and reporting when cp_terminal does not match receipt_terminal.

---

11. **[MEDIUM]** Healthy running stages are emitted as reconciliation mismatches via `running_signal`
   Category: logic | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review cites the branch around line 895 where a present `runtime_source` plus missing `local_state` assigns `mismatch_class = "running_signal"`. The reviewer argues this is the normal happy path when `control_plane_status` is also `running`, not a mismatch. Including those rows in reconciliation adds visual noise and can bury true drift.
   File: 
   Fix: Only emit a runtime-related mismatch when the control plane is not `running`. If both runtime and control plane show an active run, suppress the reconciliation entry unless another true inconsistency exists.

---

12. **[MEDIUM]** Unsound readiness proxy for local bridge
   Category: logic | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   _local_bridge_state_for_stage relies on file existence rather than verifying linkage to the current run_id or manifest, leading to false 'ready' signals for stale local artifacts after reruns.
   File: 
   Fix: Validate local bridge freshness by verifying run_id, attempt_id, or manifest hashes.

---

13. **[LOW]** Invalid inference of 'local_stale' for non-running statuses
   Category: bug | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   _reconcile_stage_rows() triages local bridge existence as 'local_stale' when the control plane is in terminal or blocked states, which fails to distinguish between actual staleness and operational blocking.
   File: 
   Fix: Implement specific mismatch classes that align with the defined taxonomy for manual or blocked states.

---

14. **[LOW]** `local_stale` does not distinguish historical outputs from genuinely polluted local data
   Category: architecture | Confidence: 0.7 | Source: Gemini (architecture/patterns)
   The review notes that `local_stale` is triggered when local data exists but the current run failed or is blocked, which is broadly correct, but it does not distinguish between outputs left over from a previous successful run versus outputs polluted by the current failed attempt. This weakens triage precision.
   File: 
   Fix: Refine stale-data classification to differentiate historical artifacts from suspect current-run pollution, for example by correlating outputs with run identifiers, timestamps, or receipt provenance.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

