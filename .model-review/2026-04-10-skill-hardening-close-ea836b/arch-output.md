## 1. Assessment of Strengths and Weaknesses

**Strengths:**
*   **Centralized Manifest Validation (`skill_manifest.py`)**: Strong structural enforcement of `skill.json`. Validating schema keys, execution modes, and physical file presence (`repo_root / entrypoint.path`) removes runtime surprises.
*   **Deterministic Signal Staging (`session-shape.py`)**: Migrating anomaly detection to zero-LLM heuristics (via `sqlite3` + mathematical features) correctly isolates the high-cost LLM layer from backlog staging. 
*   **Comprehensive Test Coverage (`test_model_review.py`)**: Testing behavior on rate-limit fallback (503), zero-byte output failures, and non-GPT axes rejection significantly hardens the cross-model extraction logic.

**Weaknesses / Regressions:**
*   **Dead Code & Leaky Guards (`model-review.py`)**: You added a guard: `if axes_text == "simple": raise ValueError(...)` but left `"simple"` in both the `PRESETS` and `AXES` dictionaries. This means passing `--axes simple,arch` bypasses the exact-match guard and executes the deprecated simple prompt anyway.
*   **Namespace Pollution in Wrappers (`observe/scripts/session_shape.py`)**: The `for _name in dir(_IMPL): globals()[_name] = getattr(...)` loop copies *everything* from the script into the module namespace, including `sys`, `json`, `os`, and `argparse`. This creates massive autocomplete/import pollution for downstream callers.

## 2. What Was Missed

*   **Schema Name Drift between Manifests and Payloads:**
    *   `shared/skill_manifest.py` defines schema identities using underscores: `"review_coverage_v1"`, `"observe_signal_v1"`, `"observe_candidate_v1"`.
    *   `review/scripts/model-review.py` emits: `COVERAGE_SCHEMA_VERSION = "review-coverage.v1"` (hyphen and dot).
    *   `observe/scripts/session-shape.py` emits: `"schema": "observe.signal.v1"` (dots).
    *   *Impact*: If a pipeline ever tries to dynamically map a runtime artifact's `"schema"` field back to the `ARTIFACT_SCHEMAS` manifest definition, it will fail due to the `_` vs `.` vs `-` discrepancy.
*   **Broken `full` Preset in `model-review.py`**:
    *   Line 199: `"full": ["arch", "formal", "domain", "mechanical", "alternatives"]`.
    *   If `"alternatives"` is not defined in the `AXES` dictionary, executing `model-review.py --axes full` will immediately crash at Line 246 (`raise ValueError(f"unknown axis '{unknown_axes[0]}'")`).
*   **Missing Hardcoded Path Cleanup (`observe/scripts/session-shape.py`)**:
    *   Lines 31-33: `_CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", ...))` and `DB_PATH = _CLAUDE_DIR / "runlogs.db"`. While acceptable for local use, it ignores the newly centralized `observe_artifacts.py` paths or `project_root()` conventions standardized in the other observe scripts.

## 3. Better Approaches

*   **Deprecate `simple` Axis Safely (Upgrade)**: Delete `"simple"` entirely from the `PRESETS` and `AXES` dictionaries. The explicit `if axes_text == "simple":` guard can stay for user-friendly error messages, but removing the underlying data guarantees the axis cannot be invoked via comma-separated bypasses.
*   **Strict `__all__` Export for Wrappers (Agree with Refinements)**: In `session_shape.py` (the wrapper), don't inject arbitrary imports into globals. Only map functions or define `__all__ = [name for name in dir(_IMPL) if not name.startswith('_') and callable(getattr(_IMPL, name))]`.
*   **Literal Schema Identity (Upgrade)**: In `ARTIFACT_SCHEMAS` (`skill_manifest.py`), change the dict keys to exactly match the payload emitted by the tools: `"review-coverage.v1"`, `"observe.signal.v1"`, and `"observe.candidate.v1"`. Never enforce snake_case in validation if the runtime contract uses dots.

## 4. What I'd Prioritize Differently

1.  **Fix the `full` Preset Crash**: Either add the `"alternatives"` axis definition to `AXES` in `model-review.py` or remove it from the `full` preset array. *Verification: `uv run python3 review/scripts/model-review.py --axes full --context plan.md` parses without throwing an unknown axis error.*
2.  **Harmonize Artifact Schema Strings**: Update `skill_manifest.py` keys to literally match `session-shape.py` and `model-review.py` output values. *Verification: `grep "review_coverage_v1" shared/skill_manifest.py` returns 0 results.*
3.  **Purge `simple` from Configuration Data**: Delete the `"simple"` key from `AXES` and `PRESETS` in `model-review.py`. *Verification: `uv run python3 review/scripts/model-review.py --axes arch,simple` throws the "unknown axis" exception.*
4.  **Fix Wrapper Globals Leak**: Modify `session_shape.py` to filter out imported modules (`type(val).__name__ != 'module'`) before assigning to `globals()`. *Verification: `python3 -c "import session_shape; assert not hasattr(session_shape, 'json')"` succeeds.*

## 5. Constitutional Alignment

The PR introduces subtle maintenance drag, violating the directive to prioritize robustness and minimize supervision cost over creation effort. The drift between `skill_manifest.py` schema naming and physical output payloads creates "false confidence" in the contract system—the manifest says one thing, the tool does another, but the system passes linting. The leaky deprecation of the `simple` preset is a hacky approach that creates future edge cases.

## 6. Blind Spots In My Own Analysis

*   **`alternatives` Axis Existence**: I am assuming `"alternatives"` is missing from `AXES` because it was not visible in the provided `unified diff` excerpts for `model-review.py`. If it exists further down in the file, that specific finding is a false positive.
*   **Module Wrapper Convention**: The dynamic `globals()` injection in `session_shape.py` might be a pervasive, accepted anti-pattern in this specific codebase for mapping hyphenated script names to Python modules. If so, fixing it here creates an inconsistency with other wrappers.
*   **Dot-to-Underscore Translation**: There may be an undocumented normalization step (e.g., in a packet builder not included in the context) that natively translates `observe.signal.v1` to `observe_signal_v1` when cross-referencing manifests. If true, the schema naming difference is intentional, not drift.