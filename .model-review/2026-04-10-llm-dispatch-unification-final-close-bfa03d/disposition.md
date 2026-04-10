# Review Findings — 2026-04-10

**13 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[CRITICAL]** BSD `mktemp` template in `generate-overview.sh` will fail on macOS
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review flags `generate-overview.sh` line 179: `temp_prompt=$(mktemp /tmp/overview-prompt-$$-${type}-XXXXXX.txt)`. On standard BSD `mktemp` (the default on macOS), the template must end exactly with `XXXXXX`; adding `.txt` after the placeholder causes an immediate `mktemp: too few X's in template` failure.
   File: generate-overview.sh
   Fix: Remove the suffix from the template, e.g. `mktemp /tmp/overview-prompt-$$-${type}-XXXXXX`, and do not rely on a file extension for downstream parsing.

---

2. **[CRITICAL]** BSD `mktemp` templates in `run-cycle.sh` are incompatible with macOS
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review identifies `run-cycle.sh` lines 39-42 as using suffixed `mktemp` templates such as `cycle_context=$(mktemp /tmp/cycle-dispatch-context-XXXXXX.md)` and similar output/meta/error variants. The reviewer states these crash on macOS because BSD `mktemp` requires the template to end exactly with `XXXXXX`.
   File: run-cycle.sh
   Fix: Drop extensions from all `mktemp` templates in `run-cycle.sh`, e.g. use `mktemp /tmp/cycle-dispatch-context-XXXXXX` and similarly for output/meta/error temp files.

---

3. **[CRITICAL]** Double-wait logic in generate-overview.sh --auto causes spurious failures
   Category: bug | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The script uses a throttling loop to wait on a PID when MAX_CONCURRENT is reached, then waits on the same PID again in the final cleanup loop. In Bash, 'wait' on an already-reaped child process returns a non-zero exit code, leading the script to incorrectly report successful tasks as failures.
   File: hooks/generate-overview.sh
   Fix: Track reaped PIDs to ensure each child is waited on only once, or check process state before calling wait in the final loop.

---

4. **[HIGH]** llmx guard applies chat-only validation to non-chat subcommands
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The llmx guard blocks diagnostic commands like 'llmx --version' because it treats any flag matching '-*' as forbidden chat-style automation. Additionally, it applies a flag allowlist derived strictly from 'llmx chat' to all llmx subcommands, causing false blocks on valid non-chat workflows.
   File: hooks/pretool-llmx-guard.sh
   Fix: Modify the script to parse the subcommand and apply validation logic selectively; specifically, allow diagnostic flags like --version and only apply flag allowlists to chat/default subcommands.

---

5. **[HIGH]** Rate-limited research cycle routing allows invalid phase selection
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The run-cycle.sh script delegates phase selection to the LLM via a generic prompt. This allows the model to select phases like 'execute', 'verify', or 'review' which the script is not equipped to perform in rate-limited mode, resulting in corrupted CYCLE.md logs and missing required actions.
   File: research-ops/scripts/run-cycle.sh
   Fix: Implement a deterministic priority ladder in the shell/Python logic to select the phase before the LLM call, ensuring only allowed phases (discover/gap-analyze/plan) are dispatched to the model.

---

6. **[HIGH]** Missing workflow-level regression tests for hooks and cycle routing
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   There is a lack of integration tests covering the interaction between shell hooks, shared Python helpers, and repo-level scripts. This absence makes the system vulnerable to integration failures in overview concurrency, guard false-positives, and research cycle routing.
   File: 
   Fix: Add a test harness or CI suite that exercises the integration paths, specifically testing concurrency throttling in overviews and subcommand-aware validation in guards.

---

7. **[HIGH]** `model-review.py` bypasses the shared dispatch abstraction
   Category: architecture | Confidence: 0.7 | Source: Gemini (architecture/patterns)
   The review says `model-review.py` imports `shared.llm_dispatch as dispatch_core`, but tests such as `test_call_llmx_passes_schema_for_openai` show it still has its own `_call_llmx` path that invokes `_LLMX_CHAT` directly. The reviewer argues this bypasses `dispatch_core.dispatch()`, so it loses standardized `.meta.json`/`.error.json` output, centralized retry/error handling, and consistent exit-code mapping.
   File: review/scripts/model-review.py
   Fix: Remove or stop using `_call_llmx`, and route review requests through `dispatch_core.dispatch(...)`, including from any thread pool used for concurrent axis reviews.

---

8. **[HIGH]** `shared.llm_dispatch.dispatch()` lacks centralized schema normalization for provider quirks
   Category: missing | Confidence: 0.6 | Source: Gemini (architecture/patterns)
   The review says `shared.llm_dispatch.dispatch` accepts `schema: dict | None` but 'does not appear' to normalize provider incompatibilities, specifically Google rejecting `additionalProperties` while OpenAI strict mode requires it. The reviewer warns that without this in the core wrapper, each upstream caller using `dispatch(schema=...)` will reimplement the same schema-mangling logic.
   File: shared/llm_dispatch.py
   Fix: Normalize schemas inside `shared.llm_dispatch.py` during payload assembly, e.g. recursively strip `additionalProperties` for Google while preserving the form needed for OpenAI strict mode.

---

9. **[MEDIUM]** Duplicated model-to-profile mapping creates migration drift risk
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The mapping between models and profiles is duplicated in shared/llm_dispatch.py and hooks/generate-overview.sh. This redundancy creates a synchronization risk during the current migration, where changes to the Python authority will not automatically propagate to the shell-based overview generation.
   File: hooks/generate-overview.sh
   Fix: Centralize the mapping in the Python dispatch utility and expose it to the shell script via a command-line flag or a lightweight helper tool.

---

10. **[MEDIUM]** Provider-specific schema mutation is duplicated in `model-review.py`
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review claims `model-review.py` manually injects or strips `additionalProperties` depending on the provider (OpenAI vs Google). It characterizes this as framework-level behavior that should not live in an individual caller, because it duplicates protocol logic and encourages other scripts to reinvent provider-specific schema handling.
   File: review/scripts/model-review.py
   Fix: Move provider-specific schema normalization out of `model-review.py` and into the shared dispatch layer so callers pass plain schema dicts without mutating them per provider.

---

11. **[MEDIUM]** Shared dispatch layer lacks a parallel or bulk invocation API
   Category: missing | Confidence: 0.6 | Source: Gemini (architecture/patterns)
   The review suggests `model-review.py` may have bypassed `dispatch_core.dispatch()` because it needs to run four queries concurrently and the core helper appears synchronous-only. It identifies the absence of a clear threaded/bulk dispatch path in the shared wrapper as a gap that pushes consumers to build their own concurrency loops and bypass the abstraction.
   File: shared/llm_dispatch.py
   Fix: Add a supported parallel or bulk dispatch interface, or document a safe pattern for calling `dispatch()` concurrently from `ThreadPoolExecutor` so clients do not need custom wrappers.

---

12. **[LOW]** `run-cycle.sh` mixes prompt text into a temporary context file instead of using dispatch inputs separately
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review disagrees with `run-cycle.sh` assembling the prompt via `cat > $cycle_context`, arguing this conflates operational instructions with the context document. It notes the dispatch CLI already supports `--context` and `--prompt`, and says using those separately would better match the intended prompt/context separation.
   File: run-cycle.sh
   Fix: Pass `CYCLE.md` through `--context` and provide the execution instructions via `--prompt` rather than concatenating both into a single temporary context file.

---

13. **[LOW]** Inconsistency between guard implementation and documented manual debugging contract
   Category: constitutional | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The llmx-guide/SKILL.md suggests raw CLI usage is valid for maintainers, yet the implemented guard blocks non-chat diagnostics from the agent's Bash path. This represents a contract mismatch between the documented 'manual' usage and the actual hook enforcement.
   File: llmx-guide/SKILL.md
   Fix: Align the documentation with the enforcement rules or adjust the hook to permit diagnostic/manual override flags when invoked from the Bash path.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

