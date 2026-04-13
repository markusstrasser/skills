# Review Findings — 2026-04-10

**15 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[CRITICAL]** ThreadPoolExecutor timeout still blocks forever on shutdown
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review claims the parallel axis runner in `model-review.py` lines 382-393 is fatally flawed: after `as_completed(..., timeout=720)` times out and the loop breaks, exiting the `with ThreadPoolExecutor(...)` block implicitly calls `shutdown(wait=True)`. If an `llmx` worker thread is hung indefinitely, the process then waits forever for that thread, defeating the intended timeout and hanging the pipeline.
   File: model-review.py
   Fix: Do not rely on the executor context manager when enforcing hard timeouts. Manage the pool manually and in `finally` call `shutdown(wait=False, cancel_futures=True)` so hung workers do not block process exit.

---

2. **[CRITICAL]** Extraction thread pool uses map with no timeout
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review identifies a second hang risk in `model-review.py` line 553: the extraction loop uses `ThreadPoolExecutor.map` without any timeout. If a GPT/Flash extraction request blocks, the entire pipeline can hang indefinitely because there is no timeout path for the mapped tasks.
   File: model-review.py
   Fix: Replace `map` with submitted futures plus explicit timeouts, and shut down the executor with `wait=False, cancel_futures=True` when a timeout occurs.

---

3. **[HIGH]** verify_claims() cannot verify the disposition format that extract_claims() generates
   Category: logic | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   In review/scripts/model-review.py, extract_claims() produces findings as multi-line blocks with 'File:' metadata on separate lines. However, verify_claims() uses a regex re.match(r"^(\d+)\.\s+(.+)") that only captures the single numbered title line, causing file references in the blocks to be ignored and claims to be marked UNVERIFIABLE.
   File: review/scripts/model-review.py
   Fix: Modify verify_claims() to parse the full multi-line finding blocks to correctly identify file references.

---

4. **[HIGH]** Deduplication falsely marks same-model duplicates as cross-model agreement
   Category: logic | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review says findings from all axes are flattened before Jaccard deduplication in `model-review.py` line 600. If one model emits two similar variants of the same issue, they can match each other, set `cross_model = True`, and receive an unjustified confidence boost even though no second model agreed.
   File: model-review.py
   Fix: Track distinct source models for each merged finding and only set `cross_model` when the overlap comes from a different `source_label` or model identity.

---

5. **[HIGH]** Concurrent JSONL appends can corrupt telemetry files
   Category: bug | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review states that `observe_artifacts.py` line 55 appends JSONL records using plain `open(..., "a")` with no file locking. Because LLM output records can exceed typical atomic append sizes, concurrent writers may interleave bytes and permanently corrupt `signals.jsonl`.
   File: observe_artifacts.py
   Fix: Add cross-platform file locking around JSONL appends, such as `fcntl.flock` on POSIX and `msvcrt` on Windows, before writing each record.

---

6. **[HIGH]** Verification verdict labels overstate what is actually checked
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The CONFIRMED status in verify_claims() only validates that referenced files exist and are readable, not the actual substance or symbols of the claim. This leads to a reported hallucination rate that is merely a file-reference existence rate, potentially giving false confidence in incorrect claims.
   File: review/scripts/model-review.py
   Fix: Rename verdicts to labels like FILE_REF_CONFIRMED or implement stronger semantic verification of the claim content.

---

7. **[MEDIUM]** The test suite does not exercise the real extract-to-verify contract
   Category: missing | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   The tests in test_model_review.py use a custom disposition format where file refs are on the numbered line, which does not match the actual multi-line output produced by extract_claims() in production. This allows pipeline contract regressions to go undetected.
   File: review/scripts/test_model_review.py
   Fix: Add an end-to-end integration test that uses the actual output from extract_claims() as input for verify_claims().

---

8. **[MEDIUM]** JSON extraction only handles fenced output at the start of the response
   Category: bug | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review flags `model-review.py` line 543 for brittle parsing: it checks `raw.startswith("```")` before stripping code fences. If the LLM prepends filler such as `Here is the extracted JSON:` before the fenced block, the fence-stripping logic is skipped and `json.loads()` fails, causing the extraction payload to be lost.
   File: model-review.py
   Fix: Search for fenced JSON anywhere in the response with a regex, then fall back to parsing the raw string if no fence is found.

---

9. **[MEDIUM]** File-path regex misses dotfiles and absolute paths
   Category: bug | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review says the file reference regex in `model-review.py` line 683 requires the path to start with a letter or underscore, so valid references like `.env`, `.github/workflows/build.yml`, or `/etc/config.json` are ignored and can be marked `UNVERIFIABLE` even when they are real files.
   File: model-review.py
   Fix: Broaden the regex to allow leading `.` and `/` while adding boundaries or a negative lookbehind so it does not match inside unrelated strings such as URLs.

---

10. **[MEDIUM]** Coverage axis order is nondeterministic
   Category: bug | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   In write_coverage_artifact(), requested_axes are reconstructed by iterating over dispatch_result.items(), which is populated via concurrent futures in the order they complete (as_completed). This causes unstable ordering in coverage.json across different runs.
   File: review/scripts/model-review.py
   Fix: Use dispatch_result["axes"] as the source of truth for axis ordering to ensure deterministic artifacts.

---

11. **[MEDIUM]** File verification is ambiguous when duplicate basenames exist
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   verify_claims() resolves file references using project_dir.rglob(filepath) and arbitrarily selects the first candidate found (candidates[0]). This makes verification results non-reproducible in projects where multiple files share the same basename.
   File: review/scripts/model-review.py
   Fix: Implement exact relative-path resolution as a priority and report ambiguity if multiple candidates are found.

---

12. **[MEDIUM]** Gemini Flash fallback drops original timeout or override settings
   Category: bug | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review claims the fallback path `rerun_axis_with_flash` in `model-review.py` line 307, invoked from line 366, forwards `**api_kwargs` but loses higher-level `timeout` or `overrides` that were passed to the original `_call_llmx`. That can make fallback behavior inconsistent with the initial request configuration.
   File: model-review.py
   Fix: Thread the original timeout and override parameters through the Flash fallback call so the rerun preserves the same operational settings.

---

13. **[MEDIUM]** Coverage artifact does not distinguish missing context metadata from zero-budget context
   Category: missing | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review notes that in `write_coverage_artifact` around line 430, missing or failed context-packet writes are silently tolerated because `_load_json` returns `{}`. Downstream readers of `coverage.json` then see empty context metadata without any explicit flag indicating whether context was absent due to I/O failure, bypassed writing, or legitimate zero-budget behavior.
   File: model-review.py
   Fix: Emit an explicit status field in `coverage.json` describing whether context metadata is present, intentionally omitted, or missing due to an error.

---

14. **[MEDIUM]** Runtime-enriched findings drift from the declared finding schema
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review points out an internal consistency problem: `model-review.py` defines a rigid `FINDING_SCHEMA` around line 47, but later deduplication adds fields such as `source_axis`, `source_model`, `cross_model`, and `also_found_by`. If findings are ever revalidated, these injected keys no longer match the declared schema.
   File: model-review.py
   Fix: Either extend the schema to include the enrichment fields or keep internal enriched finding objects separate from schema-validated export objects.

---

15. **[LOW]** Uncalibrated-threshold marker can break markdown rendering
   Category: bug | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review flags `_flag_uncalibrated_thresholds` in `model-review.py` line 507 for appending `[UNCALIBRATED]` directly to the end of a line. If the line ends with a markdown link or HTML tag, the suffix may alter or break rendering in the disposition document.
   File: model-review.py
   Fix: Insert the marker with safe spacing or structured formatting instead of blindly concatenating it to the line ending.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

