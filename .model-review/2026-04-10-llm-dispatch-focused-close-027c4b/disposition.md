# Review Findings — 2026-04-10

**10 findings** from 2 axes (1 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** `pretool-llmx-guard.sh` can be bypassed with absolute or relative `llmx` paths **[CROSS-MODEL: also GPT-5.4 (quantitative/formal)]**
   Category: security | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review claims the guard regex only catches bare `llmx` tokens using `(^|[;&|[:space:]])llmx`, so commands like `/Users/alien/.local/bin/llmx chat` or `./llmx chat` are not matched because `/` is not an allowed boundary. This would let prohibited automation sequences evade the guard.
   File: hooks/pretool-llmx-guard.sh
   Fix: Broaden the match to allow optional path prefixes, e.g. `grep -qE '(^|[;&|[:space:]])(.*/)?llmx([[:space:]]+|$)'`, and test both absolute and relative path invocations.

---

2. **[CRITICAL]** Shell scripts invoke a non-existent dispatcher path
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review says the Python helper was created as `shared/llm_dispatch.py`, but all updated shell entrypoints were changed to call `scripts/llm-dispatch.py`. Cited evidence: `hooks/generate-overview.sh` line 238 uses `"$SCRIPT_DIR/../scripts/llm-dispatch.py"`, `research-ops/scripts/run-cycle.sh` line 73 uses `"$SKILL_DIR/../scripts/llm-dispatch.py"`, and `hooks/pretool-llmx-guard.sh` lines 106 and 117 use `~/Projects/skills/scripts/llm-dispatch.py`. The reviewer states this causes immediate `No such file or directory` failures for overview generation and research cycles.
   File: 
   Fix: Replace every `scripts/llm-dispatch.py` reference with the actual helper path `shared/llm_dispatch.py` and keep naming/location consistent across all callers.

---

3. **[HIGH]** Unsound and non-portable concurrency logic in generate-overview.sh
   Category: bug | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The throttling logic uses negative array indices (pids[-$MAX_CONCURRENT]), which is a syntax error in Bash 3.2 (macOS default). Additionally, the script performs a double-wait on child PIDs; once a child is reaped, a subsequent wait returns nonzero, causing successful jobs to be misreported as failures.
   File: hooks/generate-overview.sh
   Fix: Replace negative index logic with a portable worker queue/map and ensure each PID is waited upon exactly once.

---

4. **[HIGH]** Shared dispatch environment instability via unpinned uv run
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   In hooks/generate-overview.sh and research-ops/scripts/run-cycle.sh, uv run resolves the Python environment from the current working directory. Since these are called from sibling repos, the helper runs under different repo environments, contradicting the goal of a single shared dispatch path with predictable behavior.
   File: hooks/generate-overview.sh
   Fix: Pin uv run to the source project using --project "$SKILLS_ROOT" or equivalent absolute path referencing the shared environment.

---

5. **[MEDIUM]** Guard test does not validate the emitted command path
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review says `test_pretool_llmx_guard.py` only checks that stderr contains the phrase `shared dispatch helper`, and does not assert the actual shell command emitted by the guard. Because of that, the test still passes even when the guard suggests the broken `scripts/llm-dispatch.py` path.
   File: test_pretool_llmx_guard.py
   Fix: Tighten the test to assert the exact emitted `uv run python3 ...` command string, including the correct dispatcher path, rather than only checking for a generic message fragment.

---

6. **[MEDIUM]** Silent failure in run-cycle.sh automation
   Category: logic | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The script prints diagnostics on dispatch failure but exits with code 0. This 'fails open' behavior prevents automated supervisors from detecting that the rate-limit fallback failed, treating errors as successful no-ops.
   File: research-ops/scripts/run-cycle.sh
   Fix: Ensure the script returns a nonzero exit status when the fallback dispatch execution fails.

---

7. **[MEDIUM]** Duplicated profile and model mapping in shell logic
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   generate-overview.sh maintains its own OVERVIEW_MODEL to profile mapping and token limits. This duplicates logic already present in shared/llm_dispatch.py, creating a maintenance hazard where profiles can desynchronize between the shell wrappers and the core dispatch system.
   File: hooks/generate-overview.sh
   Fix: Expose profile resolution and token budget metadata via the llm-dispatch.py CLI or a shared metadata file so the shell script can query the source of truth.

---

8. **[MEDIUM]** Gemini profile may send unsupported `reasoning_effort` parameter
   Category: logic | Confidence: 0.7 | Source: Gemini (architecture/patterns)
   The review flags that `shared/llm_dispatch.py` sets `reasoning_effort="high"` for the `deep_review` profile targeting `gemini-3.1-pro-preview`. The reviewer warns that some LiteLLM/Vertex or Google API paths may reject this OpenAI-style parameter with HTTP 400 unless it is explicitly removed or translated.
   File: shared/llm_dispatch.py
   Fix: Conditionally omit or translate `reasoning_effort` for Gemini/Google model families, or add provider-specific sanitization before dispatch.

---

9. **[MEDIUM]** Dispatcher CLI may be missing the `--error-output` argument expected by shell callers
   Category: missing | Confidence: 0.6 | Source: Gemini (architecture/patterns)
   The review notes that the shell scripts pass `--error-output "$cycle_error"` and recommends verifying that `shared/llm_dispatch.py`'s `argparse` block accepts that exact flag name. If the parser instead exposes something like `--error-path` or `--error`, invocations will fail with `unrecognized arguments`. The reviewer explicitly says they could not see the argparse block, so this is a suspected integration gap rather than a confirmed defect.
   File: shared/llm_dispatch.py
   Fix: Ensure the CLI defines `--error-output` and maps it to the intended internal `error_path` field, or update all shell callers to use the actual accepted flag consistently.

---

10. **[LOW]** Fragile coupling to private shared helpers in model-review.py
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   model-review.py imports private internal functions (_add_additional_properties, _strip_additional_properties) from dispatch_core. Internal refactoring of the shared dispatch module will break the review script even if public contracts remain stable.
   File: scripts/model-review.py
   Fix: Refactor model-review.py to use public API methods or move the required logic into a shared public utility module.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

