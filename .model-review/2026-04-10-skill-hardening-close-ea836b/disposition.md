# Review Findings — 2026-04-10

**10 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** review_coverage_v1 contract mismatch
   Category: logic | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   In shared/skill_manifest.py, ARTIFACT_SCHEMAS['review_coverage_v1'] requires keys like schema, topic, mode, and axes, but review/scripts/model-review.py:write_coverage_artifact() writes schema_version, review_dir, and artifacts. This manifest-contract drift means downstream readers cannot trust the metadata.
   File: shared/skill_manifest.py
   Fix: Update either ARTIFACT_SCHEMAS or write_coverage_artifact so the declared required fields match the emitted payload.

---

2. **[HIGH]** Artifact schema identifiers drift between manifest definitions and emitted payloads
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review claims a contract mismatch across files: `shared/skill_manifest.py` defines schema IDs like `review_coverage_v1`, `observe_signal_v1`, and `observe_candidate_v1`, while `review/scripts/model-review.py` emits `review-coverage.v1` and `observe/scripts/session-shape.py` emits `observe.signal.v1`. The reviewer argues this `_` vs `-` vs `.` drift will break any pipeline that tries to map runtime payload `schema` values back to `ARTIFACT_SCHEMAS` definitions.
   File: 
   Fix: Standardize schema identifiers so manifest keys exactly match emitted payload values, or add a single documented normalization layer and validate against that normalized form.

---

3. **[HIGH]** `full` preset may crash because it references undefined `alternatives` axis
   Category: bug | Confidence: 0.7 | Source: Gemini (architecture/patterns)
   The review points to `review/scripts/model-review.py` line 199, where `"full": ["arch", "formal", "domain", "mechanical", "alternatives"]` is defined. It claims that if `alternatives` is not present in `AXES`, then `--axes full` will fail at line 246 with `ValueError(f"unknown axis '{unknown_axes[0]}'")`.
   File: review/scripts/model-review.py
   Fix: Either add an `alternatives` entry to `AXES` or remove `alternatives` from the `full` preset.

---

4. **[MEDIUM]** Deprecated `simple` axis can still be invoked via comma-separated presets
   Category: logic | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review notes that `review/scripts/model-review.py` added a guard `if axes_text == "simple": raise ValueError(...)`, but left `"simple"` in both the `PRESETS` and `AXES` dictionaries. As a result, inputs like `--axes simple,arch` bypass the exact-match guard and still execute the deprecated simple prompt.
   File: review/scripts/model-review.py
   Fix: Remove `simple` from both `AXES` and `PRESETS`, keeping the explicit guard only for a user-friendly error if needed.

---

5. **[MEDIUM]** Wrapper re-exports pollute the module namespace with imported modules and internals
   Category: architecture | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review flags `observe/scripts/session_shape.py` for copying every attribute from `_IMPL` into `globals()` via `for _name in dir(_IMPL): globals()[_name] = getattr(...)`. This reportedly re-exports unrelated names such as `sys`, `json`, `os`, and `argparse`, causing downstream import/autocomplete pollution.
   File: observe/scripts/session_shape.py
   Fix: Export only intended public symbols, e.g. via an explicit `__all__` or by filtering to non-private callables and excluding modules before assigning into `globals()`.

---

6. **[MEDIUM]** Implicit and non-idempotent observe artifact mutation
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   session-shape.py claims artifact emission is optional in docs, but the implementation always resolves default paths and appends to signals.jsonl and candidates.jsonl. Because IDs are deterministic but the write is a blind append, repeated runs result in 100% duplicate logical records.
   File: observe/scripts/session_shape.py
   Fix: Require an explicit --emit-artifacts flag or make writes idempotent by checking existing IDs before appending.

---

7. **[MEDIUM]** Invalid SQL predicate using SELECT alias
   Category: bug | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The query in session-shape.py selects project_slug AS project but the filter adds AND project = ?. In SQLite, using a SELECT alias in a WHERE clause is non-portable and often causes OperationalError: no such column.
   File: observe/scripts/session_shape.py
   Fix: Change the filter predicate to use the source column: AND project_slug = ?.

---

8. **[LOW]** Manifest validation lacks type safety for list members
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   validate_manifest() checks membership of dispatch_profiles, packet_builders, and artifact_schemas items without ensuring they are strings. A malformed manifest with objects/lists in these fields will cause a TypeError crash rather than returning a validation issue.
   File: shared/skill_manifest.py
   Fix: Add type assertions to ensure each list member is a string before performing membership checks.

---

9. **[LOW]** `session-shape.py` still hardcodes artifact path logic instead of using shared path conventions
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review cites `observe/scripts/session-shape.py` lines 31-33, where `_CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", ...))` and `DB_PATH = _CLAUDE_DIR / "runlogs.db"` are set directly. It argues this bypasses the newer centralized observe path handling such as `observe_artifacts.py` or `project_root()` conventions used elsewhere.
   File: observe/scripts/session-shape.py
   Fix: Refactor the script to resolve paths through the centralized observe artifact/path utilities instead of maintaining its own hardcoded `CLAUDE_DIR`/`runlogs.db` logic.

---

10. **[LOW]** Brittle module import wrapper
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The script observe/scripts/session_shape.py uses module_from_spec and exec_module without registering the module in sys.modules. This is fragile in fresh import contexts and can fail when sibling imports like from observe_artifacts import ... are used.
   File: observe/scripts/session_shape.py
   Fix: Move the implementation into a standard importable module and use a thin 3-line CLI shim to invoke the main function.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

