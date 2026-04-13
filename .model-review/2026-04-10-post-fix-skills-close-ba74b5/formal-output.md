## 1. Logical Inconsistencies

| ID | Finding | Evidence | Consequence |
|---|---|---|---|
| LI-1 | **`verify_claims()` cannot verify the disposition format that `extract_claims()` generates** | In `review/scripts/model-review.py`, `extract_claims()` renders each finding as a multi-line block: numbered title line, then later `File: ...`. But `verify_claims()` only captures the **single numbered line** via `re.match(r"^(\d+)\.\s+(.+)")` and searches file refs only inside that stored title text. | For the normal extract→verify path, file references emitted on `File:` lines are ignored. Result: claims that should be checkable are marked `UNVERIFIABLE`. This is a concrete regression in the advertised `--verify` flow. |
| LI-2 | **Verification verdict labels overstate what is actually checked** | `verify_claims()` sets `CONFIRMED` when referenced files exist and optional line numbers are readable. It does **not** verify the claim’s substance or symbols, despite doc/help text saying “verify cited files/symbols exist” and the output summary saying `X CONFIRMED`. | The reported hallucination rate is not a claim-level hallucination rate; it is closer to a **file-reference existence rate**. False confirmations can reach 100% for incorrect claims that cite real files. This is contract drift. |
| LI-3 | **Coverage axis order is nondeterministic** | `dispatch()` records axis entries as futures finish (`as_completed`). `write_coverage_artifact()` reconstructs `requested_axes` by iterating over `dispatch_result.items()`, not by using `dispatch_result["axes"]`. | Same input can produce different `coverage.json` ordering across runs. That creates flaky diffs and can break consumers that assume stable order. |
| LI-4 | **File verification is ambiguous when duplicate basenames exist** | `verify_claims()` resolves refs with `list(project_dir.rglob(filepath))` and then uses `candidates[0]`. | If multiple files match, verification may confirm the wrong file arbitrarily. That makes verdicts non-reproducible across directory layouts. |
| LI-5 | **The test suite does not exercise the real extract→verify contract** | `review/scripts/test_model_review.py` tests `verify_claims()` with a custom disposition where file refs are on the numbered line. It does not verify a disposition produced by `extract_claims()`. | The main production bug in LI-1 can pass all tests. This is why the regression is likely to persist unnoticed. |

### Severity assessment
- **High:** LI-1, LI-2
- **Medium:** LI-3, LI-4
- **Medium (test gap enabling regression):** LI-5

---

## 2. Cost-Benefit Analysis

| Rank | Proposed change | Expected impact | Maintenance burden | Composability | Risk | Value-adjusted conclusion |
|---|---|---:|---:|---:|---:|---|
| 1 | **Make `verify_claims()` parse full finding blocks, not just title lines** | Very high. Likely moves verify coverage from near-0% on generated findings with `File:` lines to near the share of findings that actually have non-empty file refs. | Low | High | Low | **Best ROI.** Fixes an actual broken pipeline contract. |
| 2 | **Rename verdicts/metrics or strengthen verification semantics** | Very high. Eliminates false “CONFIRMED” claims and makes hallucination-rate reporting meaningful. | Low-to-medium | High | Low | **High value.** Either relabel to `FILE_REF_CONFIRMED` or add real symbol/claim checks. |
| 3 | **Use `dispatch_result["axes"]` as the source of truth for coverage ordering** | Medium. Removes nondeterminism from artifacts and tests. | Very low | High | Very low | **Cheap and worthwhile.** Pure correctness/determinism fix. |
| 4 | **Make file resolution exact-first and ambiguity-aware** | Medium. Prevents silent misconfirmation in repos with duplicate filenames. | Low | Medium | Low | **Worth doing.** Prefer exact relative-path match; if multiple candidates remain, mark ambiguous. |
| 5 | **Add an end-to-end test: dispatch/extract format → verify → coverage metrics** | Medium-to-high. Prevents recurrence of LI-1/LI-2. | Low | High | Very low | **Strong preventive value.** Especially important because this project is AI-authored and supervision cost matters. |

### Quantified ongoing-cost view
- LI-1 and LI-2 create **supervision drag**: humans reading `verified-disposition.md` may trust bad labels.
- LI-3 creates **artifact churn**: spurious diffs and flaky downstream assertions.
- LI-4 creates **layout-sensitive false confidence**.
- LI-5 raises **regression probability** substantially because the broken path is the default user-facing path.

---

## 3. Testable Predictions

| Prediction | Current expected result | Success criterion after fix |
|---|---|---|
| P-1 | Generate a disposition through `extract_claims()` with a finding whose `file` is `module.py`. Run `verify_claims()` on that disposition. | Current code will usually mark it `UNVERIFIABLE`, because the file ref is on the `File:` line, not the numbered line. | At least 1 such claim is classified as checkable (`CONFIRMED` or `HALLUCINATED`, depending on file existence). |
| P-2 | Feed `verify_claims()` a false claim that cites a real file, e.g. ``1. `module.py:1` contains SQL injection``. | Current code marks it `CONFIRMED` if the file exists and line is readable. | After relabeling/semantic fix, it is **not** reported as claim-level `CONFIRMED` without stronger evidence. |
| P-3 | Run `dispatch()` 20 times with mocked staggered latencies, then write `coverage.json`. | `coverage["dispatch"]["requested_axes"]` ordering will vary across runs. | Ordering is identical across all runs and matches the user-requested axis order. |
| P-4 | In a project with `a/module.py` and `b/module.py`, verify a claim referencing `module.py:1`. | Current result depends on whichever `rglob()` candidate appears first. | Output is deterministic and either resolves exact path or reports ambiguity. |
| P-5 | Add an end-to-end unit test that uses `extract_claims()` output as `verify_claims()` input. | Current code should fail that test for findings whose file ref is only on the `File:` line. | Test passes and coverage metrics reflect actual file-reference verification. |

### Untestable claim to flag
- Any current claim that `verified-disposition.md` measures true hallucination rate is **not testable as written**, because the implementation does not validate claim semantics.

---

## 4. Constitutional Alignment (Quantified)

No constitution was provided, so this is an internal-consistency scorecard.

| Dimension | Score | Rationale |
|---|---:|---|
| Producer/consumer contract consistency | **25%** | `extract_claims()` produces a format `verify_claims()` does not consume correctly. |
| Metric naming honesty | **30%** | `CONFIRMED` and `hallucination_rate` overclaim semantic verification. |
| Determinism | **60%** | Main logic is mostly deterministic, but coverage ordering and duplicate-file resolution are not. |
| Test alignment with shipped path | **35%** | Tests cover isolated helpers but miss the user-facing extract→verify flow. |
| Overall internal logical consistency | **38%** | The main regression is a direct contract mismatch between adjacent pipeline stages. |

---

## 5. My Top 5 Recommendations (different from the originals)

1. **What:** Parse disposition entries as multi-line records in `verify_claims()`.  
   **Why:** This directly fixes the broken extract→verify contract. Given the current emitted format, the verifier’s recall for file-backed findings is effectively near zero unless the title itself contains a path.  
   **Verify:** Add a test that runs `extract_claims()` to produce `disposition.md`, then `verify_claims()`, and assert `confirmed_count + hallucinated_count > 0` for findings with non-empty `file`.

2. **What:** Split verification verdicts into file-level vs claim-level, or rename current verdicts to something like `FILE_REF_CONFIRMED`, `FILE_REF_MISSING`, `NO_FILE_REF`.  
   **Why:** Current labels misstate evidence strength. This reduces false trust and makes the hallucination metric interpretable.  
   **Verify:** A deliberately false claim on a real file must no longer appear as claim-level `CONFIRMED`. Metric names in `verified-disposition.md` and `coverage.json` should match implementation semantics exactly.

3. **What:** Make `write_coverage_artifact()` use `dispatch_result["axes"]` for `requested_axes` and emit axis records in that same order.  
   **Why:** Eliminates run-to-run nondeterminism caused by `as_completed`. This reduces artifact churn and flaky tests to ~0 for ordering-related diffs.  
   **Verify:** Re-run mocked dispatch 20 times with different completion orders; produced `coverage.json` axis order remains identical.

4. **What:** Replace basename-first `rglob()` verification with exact relative-path resolution first, then ambiguity detection.  
   **Why:** Prevents silent confirmation of the wrong file in multi-module repos. This is a correctness fix, not a style tweak.  
   **Verify:** In a fixture repo with duplicate basenames, ambiguous refs must be reported as ambiguous, not silently confirmed.

5. **What:** Add one end-to-end regression test for the default CLI path with `--extract --verify`.  
   **Why:** The current test suite proves helper behavior, not pipeline correctness. One E2E test will catch the highest-impact contract drift with low maintenance cost.  
   **Verify:** Test should assert: (a) `disposition.md` exists, (b) `verified-disposition.md` exists, (c) at least one generated file-backed finding is actually checked, and (d) coverage verification counts are consistent.

---

## 6. Where I'm Likely Wrong

- I may be **underestimating external behavior in `shared.llm_dispatch`**; some schema-path concerns may already be handled there, so I avoided making them primary findings.
- I am assuming the intended meaning of `CONFIRMED` is claim-level confirmation because that is how the artifact reads. If the team intentionally meant only “file ref exists,” then LI-2 is primarily a **naming/contract drift** issue rather than a logic bug.
- I may be slightly overstating the practical frequency of LI-4 if most claims use full relative paths rather than duplicate basenames.
- I am confident about **LI-1**: it is a direct structural mismatch between how `extract_claims()` writes findings and how `verify_claims()` parses them. That is the strongest concrete bug in the packet.