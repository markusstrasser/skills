## 1. Logical Inconsistencies

| ID | Scenario | Expected from stated contract | Actual code path | Formal issue | Operator impact |
|---|---|---|---|---|---|
| L1 | `control_plane_status in {"failed","manual","dataset_blocked"}` and no runtime signal, no local bridge | **Not** `incomplete_attempt`, because the skill defines `incomplete_attempt` as “control plane expects active work” | `_reconcile_stage_rows()` assigns `incomplete_attempt` | Category error: the predicate for the class is false | Mis-triage: operator is told to look for missing live work when the control plane is explicitly non-running |
| L2 | Same statuses as L1, but local bridge exists | Not necessarily `local_stale`; skill defines `local_stale` as “newer run active or latest attempt failed” | `_reconcile_stage_rows()` assigns `local_stale` | Invalid inference from “non-completed control plane” → “local stale” | False stale warnings; can hide real blocked/manual semantics |
| L3 | Same repo state, SDK probe succeeds vs helper fallback path runs | Same reconciliation result; “truth surfaces” should not depend on implementation path | `_probe_volume_sdk_impl()` caps to 20 stage dirs and filters logs to “interesting” scripts; `_probe_volume_impl()` does neither | Caller drift: same command has non-equivalent semantics | Silent dashboard divergence depending on internal failure mode |
| L4 | More than 20 stage dirs exist; active stage dir is older than top-20 by directory mtime | Active runtime should still appear | SDK path scans only `recent_stage_entries[:20]`, chosen by **stage directory mtime**, then extracts both receipts and runtime progress only from that subset | Invalid liveness proxy: file-content updates do not reliably update parent directory mtime | High-probability false negatives for live stages in a 167-stage repo |
| L5 | Control plane terminal state disagrees with worker terminal state (e.g. cp=`failed`, receipt=`success`, local ready) | Some mismatch should surface; Constitution says “Fail loud on drift” | `_reconcile_stage_rows()` can emit nothing | Silent contradiction between two truth surfaces | Operator may trust wrong authority without seeing disagreement |
| L6 | Local bridge exists but is from an older run/attempt | Should be distinguishable from “ready” local usability | `_local_bridge_state_for_stage()` treats file existence as readiness; no run_id/attempt/manifest linkage | Unstated assumption: existence ⇒ freshness/usability | False “ready” state after rerun; bridge drift goes undetected |

### Verified code-level evidence

1. **Mismatch-class bug**  
   In `_reconcile_stage_rows()`:
   ```python
   elif control_plane_status in {"failed", "manual", "dataset_blocked"}:
       mismatch_class = "local_stale" if local_state.get("available") else "incomplete_attempt"
   ```
   This contradicts the skill definition of `incomplete_attempt`.

2. **SDK/helper non-equivalence**
   - SDK path:
     - `_SDK_RECEIPT_STAGE_LIMIT = 20`
     - scans only `recent_stage_entries`
     - logs filtered by `interesting_scripts`
   - Helper path:
     - no 20-stage cap
     - scans all stage dirs
     - logs/current read broadly

3. **Directory-mtime selection is not a valid liveness basis**
   - Sorting key is `stage_entry.mtime`
   - Receipt and progress files live under nested paths; content updates to nested files need not update the parent stage dir mtime.
   - Therefore: `argmax(stage_dir.mtime)` is not equivalent to `argmax(receipt/progress/log freshness)`.

### Missing validation matrix

Current tests cover:
- `bridge_failed`
- `incomplete_attempt` for `cp=running`
- `local_stale` when runtime is active

Missing tests for the highest-risk branches:
- `cp in {failed, manual, dataset_blocked}` classification
- SDK/helper parity
- >20 stage dirs
- terminal cp/receipt disagreement
- local bridge freshness vs mere existence

---

## 2. Cost-Benefit Analysis

| Rank | Proposed change | Expected impact | Ongoing maintenance burden | Composability | Risk | Value / drag |
|---|---|---:|---:|---:|---:|---:|
| 1 | Remove 20-stage SDK truncation; scan all stage dirs or cap only display, not evidence collection | **Very high**: eliminates systematic false negatives in a 167-stage system; restores parity with fallback | Low | High | Low | **Very high** |
| 2 | Fix mismatch taxonomy for `failed/manual/dataset_blocked`; add explicit class for control-plane non-running mismatch | High: removes formally wrong operator advice | Low | High | Low | **High** |
| 3 | Add SDK-vs-helper parity tests on the same synthetic volume tree | High: prevents future caller drift | Low-moderate | High | Low | **High** |
| 4 | Add explicit terminal-disagreement detection (`cp_terminal != receipt_terminal`) | High: surfaces silent drift between orchestrator and worker truths | Moderate | High | Low-moderate | **High** |
| 5 | Add local bridge freshness validation keyed by run_id/attempt_id/manifest hash | Medium-high: fixes false “ready” states after reruns | Moderate | Medium-high | Moderate | **Medium-high** |

### Notes

- **Creation effort is irrelevant here**; the relevant cost is future supervision.
- Change 1 has the best ratio because the current cap is both large-blast-radius and low-complexity to remove.
- Change 5 is valuable but depends on whether local bridge metadata already exists elsewhere; its maintenance cost is the highest of the five.

---

## 3. Testable Predictions

| Claim | Prediction | Success criterion | Failure signal |
|---|---|---|---|
| The 20-stage SDK cap causes false negatives | Build a fake volume with 25 stage dirs where the active stage is not in the top 20 by dir mtime | SDK and helper both report the active stage in `_runtime_progress` and/or `_worker_receipts` after the fix | Pre-fix: helper sees it, SDK misses it |
| `failed/manual/dataset_blocked -> incomplete_attempt` is wrong | Add tests for each of those statuses with no runtime signal | No branch returns `incomplete_attempt` unless `cp=running` | Any test still emits `incomplete_attempt` for non-running cp states |
| SDK/helper are semantically drifted | Run both probe implementations on identical synthetic trees with receipts, progress, and current logs | Normalized outputs are equal for worker receipts, runtime progress, and active logs | Any diff in surfaced stages/classes without an explicit waiver |
| Terminal cp/receipt disagreement is currently silent | Fixture with `cp=failed`, `receipt=success`, `local ready` | Reconciliation emits a dedicated drift row | No row emitted |
| Local existence is an unsound proxy for usability | Fixture where local files exist from old run, receipt is newer success | Reconciliation marks local stale / bridge drift, not ready | Stage treated as clean/ready |

If a change proposal cannot produce one of the above binary outcomes, it is not yet specific enough.

---

## 4. Constitutional Alignment (Quantified)

| Principle | Score | Evidence of coverage | Specific gap | Suggested fix |
|---|---:|---|---|---|
| 1. Semantic output, not downstream inference | 85% | Status work stays operator-facing | None material in this diff | Keep scope limited to runtime/operator semantics |
| 2. One path owns meaning | 45% | Control-plane status included | Two probe implementations are not equivalent | Add parity tests; unify semantics |
| 3. Operator surfaces are in scope | 80% | Reconciliation, active runtime, logs all added | Some surfaces can silently disagree or disappear | Surface drift explicitly |
| 4. Fail loud on drift | 35% | Some mismatch classes exist | Terminal cp/receipt disagreement can be silent; 20-stage truncation hides evidence | Add explicit drift rows and parity tests |
| 5. Architectural enforcement beats reminders | 60% | New tests exist | High-risk branches untested; no SDK/helper equivalence guard | Add matrix tests + parity tests |
| 6. Action default for implementation | 90% | Concrete implementation shipped | N/A | Maintain |
| 7. Do not stop at partial correctness | 50% | Migration moved forward | Reconciliation taxonomy still incomplete | Finish mismatch matrix before declaring close |
| 8. High-signal expansion allowed; speculative churn not | 85% | This is targeted status work | None material | Maintain |
| 9. Delete superseded paths after migration | 40% | New repo-local reconciliation exists | Helper fallback remains semantically different; effectively two live meanings | Either unify or explicitly degrade fallback output |
| 10. Review where silent semantic failure is likely | 55% | Review packet exists; tests added | Missing tests on highest-silent-failure branches | Add branch-complete reconciliation tests |

### Aggregate
- **Average coverage:** 62.5%
- **Main constitutional deficit:** Principle 4 (“Fail loud on drift”)

---

## 5. My Top 5 Recommendations (different from the originals)

### 1) Remove evidence truncation from the SDK probe
- **What:** Eliminate `_SDK_RECEIPT_STAGE_LIMIT` from evidence gathering, or at minimum apply limits only to display rendering after full collection.
- **Why:** In a repo with **167 stages**, a hard cap of **20** means up to **88%** of stage dirs are excluded from receipt/progress inspection on the normal code path. Because selection is by **stage dir mtime**, not actual receipt/progress freshness, the omission is not even biased toward true recency.
- **How to verify:** Add a 25-stage fake volume test where the active stage is outside top-20 dir mtimes. Metric: SDK/helper parity on `_worker_receipts`, `_runtime_progress`, `_pipeline_logs` = 100%.

### 2) Make mismatch classes predicate-correct
- **What:** Refactor `_reconcile_stage_rows()` so:
  - `incomplete_attempt` only occurs when `cp=running` and runtime signal is absent.
  - `local_stale` only occurs when a newer run is active or latest attempt failed.
  - `failed/manual/dataset_blocked` get their own explicit mismatch/drift class if needed.
- **Why:** Current branch logic violates the shared skill definitions. This is a correctness bug, not naming style.
- **How to verify:** Truth-table tests over `(cp_status, receipt_status, runtime_present, local_present)`. Metric: zero cases where class predicate is false by definition.

### 3) Add explicit terminal disagreement reporting
- **What:** Emit a reconciliation row when control-plane and worker terminal states disagree, even if local files exist.
- **Why:** Today `cp=failed` + `receipt=success` + `local ready` can disappear entirely. That is precisely the kind of silent ambiguity the Constitution forbids.
- **How to verify:** Add tests for:
  - `cp failed / receipt success`
  - `cp completed / receipt failed`
  - `cp manual / receipt success`
  Success metric: each yields one deterministic drift row.

### 4) Add SDK-vs-helper equivalence tests as an enforcement boundary
- **What:** Build a normalized comparison harness for `_probe_volume_sdk_impl()` and `_probe_volume_impl()` on the same synthetic filesystem model.
- **Why:** There are currently two live meanings of “status,” selected by internal failure mode. That is architectural drift.
- **How to verify:** CI test compares normalized outputs for receipts, runtime progress, and current logs. Metric: zero unexpected diffs.

### 5) Replace “local files exist” with “local bridge matches latest attempt”
- **What:** Tie local readiness to `run_id`, `attempt_id`, or `manifest_hash` rather than bare file existence.
- **Why:** Current logic can produce false-ready states after reruns. In operator terms, “can I use this result locally?” is not answered by `len(files) > 0`.
- **How to verify:** Fixture with local files from old run and newer success receipt. Metric: classification changes from clean/ready to stale/bridge-drift until local bridge is refreshed.

---

## 6. Where I'm Likely Wrong

1. **I may be over-interpreting control-plane statuses.**  
   If `manual` or `dataset_blocked` are intentionally treated operationally as “actionable incomplete work,” then my objection is specifically to the **class name semantics**, not necessarily the need to surface them.

2. **I may be overstating the directory-mtime problem if Modal volume metadata behaves differently than POSIX expectations.**  
   My critique assumes parent dir mtimes do not reliably track nested file content updates. That is true in standard filesystems; if Modal’s list metadata is synthetic and propagates descendant freshness upward, the severity drops. The parity test I recommended would settle this.

3. **I may be underestimating an external constraint behind the 20-stage cap.**  
   If full SDK traversal is materially expensive or flaky, a capped display may be justified. But then the helper fallback and SDK path still need declared, tested equivalence on the subset they claim to show.

4. **I may be too strict about local bridge freshness for a personal-operator workflow.**  
   If the operator only wants “any local artifact exists,” then existence-only may be intentional. But that conflicts with the stated `local usability` surface, which sounds freshness-sensitive.

5. **I am biased toward fail-loud operator semantics.**  
   Given the project constitution, that bias is mostly aligned here, but it can make me prefer explicit drift classes over simpler summaries in a personal project.