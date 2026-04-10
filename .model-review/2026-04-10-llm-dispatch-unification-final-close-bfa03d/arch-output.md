## 1. Assessment of Strengths and Weaknesses

**Strengths:**
*   **Guard Regex Precision:** The `pretool-llmx-guard.sh` block correctly isolates raw `llmx` CLI automation without false-flagging the new wrapper (`s/.*(^|[;&|[:space:]])llmx[[:space:]]+([^[:space:]]+).*/\2/p`). This successfully maps `-*` and `chat` to the blocker while allowing `image`/`vision` subcommands. 
*   **Compatibility Boundary:** `generate-overview.sh` cleanly honors the migration constraint. Extracting the profile logic into `resolve_overview_profile` retains legacy `OVERVIEW_MODEL` config interoperability without polluting the Python API with legacy model names.
*   **Failure Isolation:** `run-cycle.sh` explicitly maps the shared dispatch execution errors (`$dispatch_exit -ne 0`) to specific STDERR outputs from `.meta.json` and `.error.json` before cleaning up.
*   **Atomic Write Guarantees:** Both the bash wrappers and `shared/llm_dispatch.py` enforce strict atomic moves (`mv "$tmp_final" "$output_file"` and `_atomic_write_json`). This prevents zero-byte file corruptions during agent interrupts.

**Weaknesses & Bugs:**
*   **Fatal macOS `mktemp` Syntax Bug:** Standard BSD `mktemp` (shipped on macOS) requires the template to end *exactly* with `XXXXXX`. The following lines will instantly crash with `mktemp: too few X's in template` when agents run this on local repos:
    *   `generate-overview.sh` line 179: `temp_prompt=$(mktemp /tmp/overview-prompt-$$-${type}-XXXXXX.txt)`
    *   `run-cycle.sh` lines 39-42: `cycle_context=$(mktemp /tmp/cycle-dispatch-context-XXXXXX.md)` (and output/meta/error variants).
*   **Abstraction Leak / Guard Bypass in `model-review.py`:** `model-review.py` imports `shared.llm_dispatch as dispatch_core`, but the tests (`test_call_llmx_passes_schema_for_openai`) reveal it implements its own `_call_llmx` function invoking `_LLMX_CHAT` directly. By bypassing `dispatch_core.dispatch()`, it drops all the new infrastructure benefits: it won't emit standardized `.meta.json`/`.error.json`, bypasses central retry heuristics, and fragments the error exit code mapping. 
*   **Duplicated Schema Mangling:** Because `model-review.py` uses its own `_call_llmx`, it manually injects or strips `additionalProperties` based on the provider (OpenAI vs Google). This is framework-level logic that should live entirely within `shared/llm_dispatch.py`.

## 2. What Was Missed

*   **Centralized Schema Normalization:** `shared.llm_dispatch.dispatch` accepts `schema: dict | None` but does not appear to normalize provider quirks (like Google rejecting `additionalProperties` vs OpenAI requiring it for strict mode). If the centralized wrapper doesn't do this, every upstream script calling `dispatch(schema=...)` will reinvent it.
*   **Threaded Dispatch Support in Core:** `model-review.py` likely bypassed `dispatch_core.dispatch()` because it needs to dispatch 4 queries concurrently (Arch, Formal, Domain, Mechanical) and assumed the core wrapper was synchronous-only. The core helper lacks a clear parallel/bulk invocation path, forcing consumers to roll their own concurrency loops.

## 3. Better Approaches

*   **Disagree** with appending extensions to `mktemp` calls.
    *   *Upgrade:* Drop the extensions. Use `temp_prompt=$(mktemp /tmp/overview-prompt-${$}-${type}-XXXXXX)`. The Python API (`Path.read_text()`) does not require a `.txt` or `.md` extension to parse the context correctly.
*   **Disagree** with `model-review.py` wrapping `_LLMX_CHAT` directly via `_call_llmx`.
    *   *Alternative:* Refactor `model-review.py` to execute `dispatch_core.dispatch(profile=AXES[axis]["profile"], ...)` inside a standard `ThreadPoolExecutor`. Have it read the resulting `DispatchResult` to populate its final markdown report.
*   **Agree** with passing JSON schemas as pure dicts to `dispatch()`.
    *   *Refinement:* Move the `additionalProperties` mutation from `model-review.py` into `shared.llm_dispatch.py`'s payload assembly phase. If `profile_def.provider == "google"`, recursively strip `additionalProperties` from the schema before sending.
*   **Disagree** with `run-cycle.sh` manual prompt assembly via `cat > $cycle_context`.
    *   *Alternative:* The `scripts/llm-dispatch.py` interface supports both `--context` and `--prompt`. Pass the `CYCLE.md` context via the `--context` file, and pass the explicit operational instructions inline via `--prompt "You are running one tick..."`. This avoids concatenating prompts into context files and aligns with the strict prompt/context separation defined in `llmx-guide/SKILL.md`.

## 4. What I'd Prioritize Differently

1.  **Fix BSD `mktemp` suffix crash (Critical):** Remove `.md` and `.txt` suffixes from all `XXXXXX` templates in `run-cycle.sh` and `generate-overview.sh`. This is a hard blocker for local execution on macOS.
2.  **Route `model-review.py` through `dispatch_core.dispatch` (High Maintenance Drag):** Delete `_call_llmx`. Update the thread pool in `model-review.py` to call `dispatch()`. This instantly cuts redundant error handling and standardizes output telemetry.
3.  **Centralize Schema Provider Quirks (High Composability Risk):** Move the schema manipulation tested in `test_call_llmx_passes_schema_for_openai` out of the review script and into `shared.llm_dispatch.py`.
4.  **Decouple `run-cycle.sh` prompt logic (Low):** Move the instructions string to the `--prompt` argument rather than injecting it at the bottom of the temporary context file.

## 5. Constitutional Alignment

No constitution provided — assess internal consistency only.

Internal consistency is generally exceptional (particularly in the bash telemetry and CLI guard rails), but severely undermined by `model-review.py` choosing not to consume the abstraction it helped justify.

## 6. Blind Spots In My Own Analysis

*   **`model-review.py` implementation limits:** The provided unified diff and file excerpts for `review/scripts/model-review.py` cut off before the main `dispatch()` loop. I am relying entirely on the `test_model_review.py` patching of `_call_llmx` to deduce that it bypasses `dispatch_core.dispatch()`. If `_call_llmx` is actually just dead legacy code and the real code *does* use `dispatch()`, my critique in section #1 and #3 is invalid (though the tests should still be cleaned up).
*   **Rate Limits on Shared Dispatch:** `run-cycle.sh` triggers the shared wrapper when `CLAUDE_PROCS >= 6`. However, if `llm-dispatch.py` calls Google's API, it might hit `429 Resource Exhausted` if executed too rapidly in parallel. I assume `llm_dispatch.py` handles exponential backoff internally, but if it relies on immediate exit (returning `11`), the `run-cycle.sh` script will quietly abort the tick.