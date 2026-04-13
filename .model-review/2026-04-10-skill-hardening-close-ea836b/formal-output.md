## 1. Logical Inconsistencies

| Finding | Why it is a real contradiction |
|---|---|
| **`review_coverage_v1` contract does not match the artifact actually written** | In `shared/skill_manifest.py`, `ARTIFACT_SCHEMAS["review_coverage_v1"]` requires `schema, topic, mode, axes, claims, verification, packet`. But `review/scripts/model-review.py:write_coverage_artifact()` writes `schema_version, review_dir, artifacts, context_packet, dispatch, extraction, verification`. That is manifest-contract drift, not just naming drift. A manifest-first system cannot claim one schema and emit another. |
| **`session-shape.py` says artifact emission is optional, but it always mutates canonical artifacts** | The docstring/help says output *can* be written via `--signals-out` / `--candidates-out`, but `main()` always resolves defaults via `artifact_path("signals.jsonl")` / `artifact_path("candidates.jsonl")` and always appends. This is a read-vs-write contract violation. |
| **`session-shape.py` uses deterministic IDs but non-idempotent appends** | `build_signal_record()` / `build_candidate_record()` generate stable IDs, but the script blindly `append_jsonl()`s on every run. Same session + same threshold + same project => same logical record written multiple times. Stable identity without dedupe creates false recurrence and artifact inflation. |
| **`--project` filtering in `session-shape.py` is likely invalid SQL** | Query selects `project_slug AS project` but the filter adds `AND project = ?`. In SQLite, relying on a SELECT alias in `WHERE` is at best non-portable and often invalid; the source column is `project_slug`. This is an unstated assumption in a touched path. |
| **The new import wrapper `observe/scripts/session_shape.py` is not equivalent to a real module** | It uses `module_from_spec(...); exec_module(...)` without registering the module in `sys.modules`, and the implementation contains a `@dataclass` plus sibling imports (`from observe_artifacts import ...`). In fresh import contexts, that pattern is brittle and commonly fails. The wrapper claims “stable module name,” but the loading mechanism does not guarantee import stability. |
| **Manifest validation is not total over arbitrary JSON** | `validate_manifest()` checks membership of `dispatch_profiles`, `packet_builders`, and `artifact_schemas` items without first ensuring each item is a string. A malformed manifest containing an object/list can raise `TypeError` instead of returning `ManifestIssue`. A validator that crashes on malformed input is a contract hole. |

## 2. Cost-Benefit Analysis

| Change to make | Expected impact | Maintenance burden | Composability | Risk if not fixed | Value rank |
|---|---:|---:|---:|---:|---:|
| **Align `review_coverage_v1` with the actual `coverage.json` payload** | High: removes manifest/schema falsehood across the review skill | Low | High | High: downstream readers will trust bad metadata | **1** |
| **Make observe artifact emission explicit or idempotent** | High: prevents duplicate signals/candidates and accidental backlog mutation | Low-Medium | High | High: repeated runs pollute staging data | **2** |
| **Replace the wrapper/impl split with a canonical importable module + thin CLI shim** | High: removes fragile import behavior for tests and future code | Low | High | Medium-High: import-time breakage blocks reuse | **3** |
| **Fix `project_slug` filtering and add DB-backed test coverage** | Medium: restores correctness for scoped analysis | Low | Medium | Medium: users get errors or silent misfiltering | **4** |
| **Make manifest linting type-safe for list members** | Medium: converts crash paths into actionable validation issues | Low | High | Medium: CI/lint can fail hard on malformed manifests | **5** |

Creation effort is irrelevant here; all five are cheap in ongoing complexity and high in contract quality.

## 3. Testable Predictions

1. **Coverage contract mismatch is observable now**
   - Prediction: generate a review run with extraction enabled, then compare `coverage.json` keys against `ARTIFACT_SCHEMAS["review_coverage_v1"]["required_fields"]`.
   - Expected result: at least `schema`, `topic`, `mode`, `axes`, `claims`, and `packet` are missing from the emitted artifact.

2. **`session-shape.py` duplicates artifacts on rerun**
   - Prediction: run the script twice against the same DB and same time window with a temp artifact root.
   - Expected result: `signals.jsonl` line count doubles; `candidate_id`/`signal_id` values repeat byte-for-byte.

3. **`--project` filtering is broken or non-portable**
   - Prediction: invoke `session-shape.py --project foo` against a fixture DB.
   - Expected result: either `sqlite3.OperationalError` (`no such column: project`) or incorrect filtering behavior.
   - Even if SQLite happens to accept it, it remains a portability smell and should be normalized to `project_slug`.

4. **The import wrapper is likely unstable in a clean process**
   - Prediction: import `observe/scripts/session_shape.py` from a test runner that does not pre-seed `sys.path` with `observe/scripts`.
   - Expected result: import fails with either module resolution issues (`observe_artifacts`) or loader/dataclass-related instability.
   - Fast falsifier: add a one-line import smoke test in CI.

5. **Malformed manifest members can crash lint**
   - Prediction: validate a manifest where `uses.dispatch_profiles` contains `{}` instead of `"formal_review"`.
   - Expected result today: uncaught `TypeError` during membership check, rather than a clean `ManifestIssue`.

## 4. Constitutional Alignment (Quantified)

No constitution was provided, so this is an internal-consistency scorecard.

- **Manifest-first hardening goal:** partially met.
- **Contract surfaces touched:** 3 important ones in this packet:
  1. skill manifest schema registry,
  2. review coverage artifact,
  3. observe signal/candidate emission.
- **Clear contract drifts still present:** 2/3.
  - `review_coverage_v1` metadata vs emitted payload: drifted.
  - observe CLI docs vs write behavior: drifted.
- **Validator totality:** still incomplete.
- **Net assessment:** the migration improves structure, but still creates **false confidence** because metadata and runtime behavior are not yet fully aligned.

## 5. My Top 5 Recommendations (different from the originals)

1. **Make the coverage artifact contract authoritative**
   - **What:** Update either `ARTIFACT_SCHEMAS["review_coverage_v1"]` or `write_coverage_artifact()` so they describe the same payload.
   - **Why:** Right now the declared contract and emitted artifact disagree on most required fields. That is near-maximum contract drift for a manifest-first migration.
   - **How to verify:** Add a unit test that emits `coverage.json` and asserts every declared required field exists. Metric: **0 missing required fields**.

2. **Stop implicit observe artifact mutation**
   - **What:** Require an explicit `--emit-artifacts` flag, or make writes idempotent by key (`signal_id`, `candidate_id`) instead of append-only.
   - **Why:** Current behavior makes every diagnostic run mutate the canonical backlog. Re-running the same scan can produce **100% duplicate logical records**.
   - **How to verify:** Run identical scan twice. Metric: **unique `signal_id` count == line count** after rerun, or **no artifact files created** unless emission is explicitly requested.

3. **Invert the module structure for `session-shape`**
   - **What:** Move implementation into `session_shape.py` and make `session-shape.py` a 3-line CLI shim that imports `main`.
   - **Why:** That is the durable pattern for Python importability. It removes loader edge cases, improves testability, and avoids spec/sys.modules brittleness.
   - **How to verify:** Add `python -c "import observe.scripts.session_shape"`-style smoke test or equivalent path-based import test. Metric: **import succeeds in a clean interpreter**.

4. **Fix the SQL predicate to the source column and test it**
   - **What:** Change `AND project = ?` to `AND project_slug = ?` in `session-shape.py`.
   - **Why:** Alias-in-`WHERE` is the wrong dependency to lean on. This is a correctness issue, not style.
   - **How to verify:** Add fixture DB test with two projects. Metric: **returned rows all match requested project_slug** and **no SQL errors**.

5. **Make manifest validation total over arbitrary JSON**
   - **What:** For `dispatch_profiles`, `packet_builders`, and `artifact_schemas`, first assert each member is a non-empty string; only then do membership checks.
   - **Why:** Validators should degrade to issues, not exceptions. This reduces supervision cost and CI flakiness.
   - **How to verify:** Fuzz a few malformed manifests. Metric: **0 uncaught exceptions**, **1+ deterministic `ManifestIssue`s** per malformed field.

## 6. Where I'm Likely Wrong

- **SQLite alias behavior:** SQLite can be permissive in odd places; the `project` alias may work in some builds. But even if it does, it is still the wrong dependency for a hardened contract.
- **Wrapper failure mode:** The `session_shape.py` wrapper may happen to work in your current test harness if `sys.path` is already favorable. My claim is that it is brittle in fresh/import-by-path contexts, not that it must fail in every environment.
- **Coverage schema intent:** If `ARTIFACT_SCHEMAS` is only advisory and not used by any consumer yet, the immediate blast radius is smaller. But in a manifest-first migration, stale advisory metadata is still harmful because it invites downstream misuse.