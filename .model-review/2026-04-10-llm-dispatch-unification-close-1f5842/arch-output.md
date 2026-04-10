## 1. Assessment of Strengths and Weaknesses

**Strengths:**
*   **Atomic file operations:** `generate-overview.sh` correctly uses `mktemp` and atomic `mv` to prevent truncated `.claude/overviews/` files from polluting context if the API fails mid-generation.
*   **Fingerprinted profiles:** `shared/llm_dispatch.py` hashes the `DispatchProfile` payload. This establishes a highly robust mechanism for tracking exact execution configurations against agent outcomes.
*   **Structured error states:** Moving from raw bash pipe exit codes to deterministic JSON files (`error_path`, `meta_path`) with explicitly mapped `STATUS_EXIT_CODES` gives agents the observability they need to debug loops without hallucinating the cause.

**Weaknesses & Bugs:**
*   **Syntax Trap (Argparse Error):** In `research-ops/SKILL.md`, the shared dispatch bash snippet is missing the `--prompt` argument. `scripts/llm-dispatch.py` enforces `if not prompt: parser.error(...)`. If rate-limited, the research cycle will reliably crash on line 1 with an argparse error.
*   **`ModuleNotFoundError` (Pathing):** In `improve/SKILL.md`, the Python snippet instructs the agent to run `from shared.llm_dispatch import dispatch`. Agents executing this in `~/Projects/meta` (or anywhere besides the `skills` root) will fail because `~/Projects/skills` is not in `PYTHONPATH`. The previous raw `llmx` code explicitly injected `sys.path` for the uv tools directory, but the new code drops `sys.path` injection entirely.
*   **Security/Guard Bypass:** `pretool-llmx-guard.sh` relies on `grep -qE 'llmx\s+chat'` to block automation from using the CLI. Because `chat` is the default subcommand for `llmx`, any agent invoking `llmx -m gemini-3.1-pro-preview "task"` will trivially bypass this guard.
*   **Guard Contradiction:** `llmx-guide/SKILL.md` instructs agents to use raw `llmx chat` for debugging shared dispatch failures. However, `pretool-llmx-guard.sh` blindly intercepts and blocks `llmx chat` with `exit 2`, physically preventing the agent from following the guide's debugging instructions.
*   **Hardcoded Context Window limit:** `generate-overview.sh` explicitly validates token counts against `900000` (line 210). If the resolved profile maps to `gpt_general` (GPT-5.4, max context ~128k), passing 800k tokens bypasses the bash check and blows up at the OpenAI API layer.

## 2. What Was Missed

*   **Migration Lie in `model-review.py`:** The scope specifies the migration target is to "stop composing raw `llmx chat` calls and route through the shared dispatch helper". While `review/scripts/model-review.py` imports `shared.llm_dispatch as dispatch_core`, it completely bypasses `DispatchProfile` routing. It maintains its own hardcoded `AXES` mapping (re-defining `provider="google"`, `model="gemini-3.1-pro-preview"`, and API kwargs), defeating the purpose of centralized profile governance. 
*   **Orphaned `response.content` assumptions:** In `improve/SKILL.md`, the Python signature migrated from `llmx_chat(...)` to `dispatch(...)`. `llmx_chat` returns an object with `.content`, whereas `dispatch()` returns a `DispatchResult` that writes output to disk but does not possess a `.content` attribute. If agents extrapolate from previous workflows and try to log or print `response.content`, it will throw an `AttributeError`.
*   **Duplicate prompt injections in `generate-overview.sh`:** The script passes `temp_prompt` (which contains repomix output + the actual instruction prompt from `OVERVIEW_PROMPT_DIR`) to `--context`, and additionally passes `--prompt "Write the requested codebase overview in markdown."`. This pushes dual, conflicting instructions to the model (one highly specific in context, one generic in the prompt field).

## 3. Better Approaches

| Issue | Disagree / Upgrade | Recommendation |
| :--- | :--- | :--- |
| **`research-ops/SKILL.md` argparse crash** | Upgrade | Append `--prompt "Run the phase based on context"` to the `uv run python3` snippet. |
| **Python API Import Failure** | Upgrade | Prepend `import sys, os; sys.path.insert(0, os.path.expanduser("~/Projects/skills"))` before `from shared.llm_dispatch import dispatch` in `improve/SKILL.md`. |
| **`pretool-llmx-guard.sh` bypass** | Upgrade | Modify the regex to match `llmx` invocations not explicitly hitting other subcommands: `grep -qE 'llmx(\s+chat|\s+-|\s+["'\''])'`. |
| **`pretool-llmx-guard.sh` debug block** | Agree (with refines) | The guard should enforce automation rules but allow explicit manual intervention. Add a bypass: `if echo "$CMD" | grep -qE -- '--debug'; then exit 0; fi`. |
| **`model-review.py` bypassing profiles** | Disagree | Remove the `AXES` model hardcoding. Refactor to `dispatch(profile="deep_review", ...)` and `dispatch(profile="formal_review", ...)` to consume governed timeouts and context windows. |
| **Hardcoded 900k token limit** | Upgrade | Extract max tokens from the resolved profile dynamically, or set conservative fallback: `[[ "$dispatch_profile" == "gpt_general" ]] && limit=120000 || limit=900000`. |

## 4. What I'd Prioritize Differently

1.  **Fix the Argparse Error in `research-ops/SKILL.md`:** 
    *   *Priority:* Critical. 
    *   *Verification:* Run `uv run python3 scripts/llm-dispatch.py --profile cheap_tick --context /dev/null`. Verify it fails with `parser.error`. Fix the markdown text to include `--prompt`.
2.  **Fix Python `sys.path` in `improve/SKILL.md`:** 
    *   *Priority:* Critical.
    *   *Verification:* Run a mock `python3 -c "from shared.llm_dispatch import dispatch"` from `~/Projects/meta`. Verify `ModuleNotFoundError`. Add the `sys.path.insert` logic to the skill text.
3.  **Patch the `llmx chat` Guard Bypass:** 
    *   *Priority:* High.
    *   *Verification:* Assert `echo 'llmx -m gemini-3.1-pro-preview "hello"' | ./hooks/pretool-llmx-guard.sh` correctly exits 2.
4.  **Allow `--debug` passthrough in `llmx-guard`:** 
    *   *Priority:* Medium. 
    *   *Verification:* Assert `echo 'llmx chat --debug ...' | ./hooks/pretool-llmx-guard.sh` exits 0.
5.  **Refactor `model-review.py` to true profile consumption:** 
    *   *Priority:* Medium (Maintenance burden).
    *   *Verification:* Remove `provider` and `model` from `AXES`, verify it correctly builds and runs relying on `dispatch_core.PROFILES["deep_review"]`.

## 5. Constitutional Alignment

The prompt explicitly states: *"NEVER recommend trading stability, composability, or robustness for dev time savings."*

The current state of `review/scripts/model-review.py` violates this constraint. By importing `shared.llm_dispatch` but circumventing `DispatchProfile` to manually invoke `_call_llmx` (as demonstrated in `test_model_review.py`), the author traded proper architectural composition for migration speed. This introduces parallel execution paths that will silently drift from rate limit and telemetry definitions managed in `llm_dispatch.py`. This technical debt must be paid down before closing the plan.

## 6. Blind Spots In My Own Analysis

*   I cannot see the full implementation of `shared.llm_dispatch.py` (specifically how `dispatch()` parses kwargs to the final `llmx.api.chat` call), so I am assuming it successfully concatenates `--context` and `--prompt` into a single string. If it drops one or the other, `generate-overview.sh` will fail functionally despite exiting 0.
*   In `improve/SKILL.md`, the code snippet cuts off at the `dispatch(...)` execution. I am flagging the missing `.content` attribute as a risk based on the old behavior, but I cannot verify if the remainder of the omitted text gracefully handles `output_path` reading.
*   I assumed `generate-overview.sh`'s redundant token limit check (900k) will break for GPT-5.4, but if `OVERVIEW_EXCLUDE` drastically prunes contexts down to <100k intrinsically, this bug may remain functionally dormant.