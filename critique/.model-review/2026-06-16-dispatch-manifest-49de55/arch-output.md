## 1. Strengths and Weaknesses (structure + correctness)

### Strengths
*   **Separation of Policy and Execution**: Moving execution variables (`premise_scout`, `context_scope`, `budget_seconds`) from ephemeral CLI flags in the session agent into a serialized, declarative manifest is structurally sound. It provides a clear audit trail and replayability of the execution topology.
*   **Preventative Budget Gating**: Calculating remaining wall-clock time against resolved axis timeouts *before* executing an axis prevents wasteful mid-axis execution truncation. This protects LLM API call token spend by avoiding truncated, non-functional critique outputs.

### Weaknesses & Bugs
*   **Silent Execution Omission (No State Sync)**: If `model-review.py` drops or skips a formal axis because the remaining budget is too small, it does not write this state back to the manifest. Downstream consumers parsing the manifest or the build pipeline will observe a successful execution status, leading to silent passes on untested code.
*   **Dual-Ownership of Blocker Exit Logic**: The design states that `model-review.py` exits `1` if the manifest `blockers` array is non-empty. This introduces structural coupling. If `review_gate.py` identifies critical blockages during triage, it should fail immediately rather than writing a poisoned manifest and delegating the exit responsibility to `model-review.py`. 
*   **Race Conditions in Parallel Budget Resolution**: If `model-review.py` processes axes in parallel (e.g., concurrent async calls to different model endpoints), a simple sequential remaining-time check will fail. Multiple parallel tasks will read the same "remaining budget" value simultaneously, over-commit the actual available time, and run into hard timeout truncations.
*   **Fragile Heuristics for Context Scope**: Deducing `context_scope` (`repo` vs. `packet`) via simple regex for "path refs" in `review_gate.py` is highly error-prone. Paths in packets may be formatted as escaped JSON strings, markdown links, or partial relative paths. A false negative disables `premise_scout`, starving the model of repository context; a false positive forces slow, unnecessary repository indexing.

---

## 2. Better Approaches

### Reject Regex-Based Scope Inference; Adopt Explicit Schema Registry
Instead of brittle regex scanning of packet payloads, the packet generator must explicitly emit a structured `manifest_metadata` block defining the targeted paths. If metadata is missing, the system must default to a safe-mode "strict repo" scan rather than guessing and risking context starvation.

### Enforce "Immutable Manifest, Mutable State File" Separation
Do not allow `model-review.py` to parse complex logic of CLI overrides alongside manifest values. 

Instead, implement a unified orchestration flow:
1. `review_gate.py` generates `dispatch_manifest.json` containing the finalized execution plan. All overrides must be resolved at this stage.
2. `model-review.py` acts as a pure, deterministic execution engine. It reads the manifest, executes it, and outputs an `execution_receipt.json` containing the exact execution outcome (e.g., `completed`, `skipped_budget`, `failed`) for each axis.

```
[Packet] ➔ [review_gate.py (Heuristics + Overrides)] ➔ [dispatch_manifest.json] ➔ [model-review.py] ➔ [execution_receipt.json]
```

---

## 3. Top 5 Priorities

1. **Define Unified Manifest & State Schema**: Create strict Pydantic definitions for `DispatchManifest` and `ExecutionReceipt` to prevent manual dictionary key mismatch between `review_gate.py` and `model-review.py`.
2. **Implement Execution Receipt Output**: Ensure that when `model-review.py` skips an axis due to budget constraints, this is recorded as `skipped_budget` in a structured output file, failing the pipeline if critical axes were omitted.
3. **Move Blocker Exits to Triage Gate**: Change `review_gate.py` to exit non-zero immediately upon discovering non-empty blockers instead of writing a manifest and waiting for `model-review.py` to fail.
4. **Implement Deterministic Path Parser**: Replace the regex scanning heuristic with a standard path resolution library (e.g., Python's `pathlib`) matched against a strict repository file map.
5. **Add Thread-Safe Budget Coordinator**: Implement a synchronized budget manager in `model-review.py` that subtracts estimated axis execution time from the shared remaining budget pool *before* dispatching asynchronous API calls.

---

## 4. Goals & Principles Alignment

### Internal Consistency
*   **Determinism vs. Dynamic Overrides**: The primary goal of the design is to move policy into a "deterministic triage output." However, by allowing `model-review.py` to take `--dispatch-manifest` alongside dynamic CLI overrides, the design re-introduces non-determinism at the execution boundary. This violates the core design principle.
*   **Zero-Maintenance/Low-Blast-Radius Priority**: The design distributes timeout and configuration parsing across both scripts. If a timeout format changes, both files must be updated. This high structural coupling increases the maintenance burden and blast radius for future updates.

---

## 5. Blind Spots In My Own Analysis

*   **Stateful CI/CD Execution Environments**: If this runs in a stateless CI/CD environment (e.g., GitHub Actions), writing back execution receipts to disk requires explicit artifact upload configurations. If the pipeline runner does not capture the generated receipt, down-stream validation steps cannot verify if axes were skipped.
*   **Multi-Repository Projects**: The `context_scope` heuristic assumes a single root repository. If the packet contains paths pointing to external submodules or multi-repo workspaces, standard path parsing and scout sweeps will fail silently.
*   **Caching of Scout Indexes**: Toggling `premise_scout` dynamically via heuristics will cause performance inconsistency. If the scout is off for one run and on for the next, cache invalidation strategies for vector databases or indexing layers must be defined to prevent stale context retrieval.

---

## 6. Coverage & assumptions checklist

*   **Cross-file drift**: Verified risk. `review_targets.design_target.*` and `layers.design.axes` must map to identical enum values in both files. No validation layer is proposed to enforce this mapping.
*   **Join keys**: The connection between a "path reference" in the packet and the repository scope relies on path matchers. If the repository root is nested (e.g., a subdirectory deployment), path matching will fail to resolve.
*   **Runner Environment Requirements**: The budget-gate relies on system clock time (`remaining wall clock`). If the execution environment experiences CPU throttling or network latency spikes (common in CI agents), axes will be skipped unpredictably based on runtime environmental variance.

---

## 7. Contracts & interfaces (structure view)

```typescript
// Proposed Unified Contract Schemas

interface DispatchPolicy {
  premise_scout: boolean;
  context_scope: "repo" | "packet";
  budget_seconds: number | null;
}

interface DispatchManifest {
  schema_version: "2026-06-16";
  dispatch_policy: DispatchPolicy;
  review_targets: {
    axes: string[];
    preset?: string;
  };
  blockers: string[]; // Must cause review_gate.py to fail immediately
}

interface AxisResult {
  axis: string;
  status: "success" | "failed" | "skipped_budget";
  execution_time_seconds: number;
  error_message?: string;
}

interface ExecutionReceipt {
  manifest_hash: string;
  overall_status: "passed" | "failed" | "incomplete";
  results: AxisResult[];
}
```

---

## 8. Structural assumptions

- `review_gate.py` and `model-review.py` are executed in the same file system context where manifest files are persistently writable.
- No network partition or token-limit exhaustion occurs midway through an axis execution that would bypass the budget calculation logic.
- The execution orchestrator executes `review_gate.py` first, captures its exit status, and halts immediately if an error or blocker is detected before invoking `model-review.py`.
- The repository structure has a single, unambiguous root directory matching the execution directory of `model-review.py`.
- Axis timeout profiles are statically defined and accessible to both scripts without network roundtrips.