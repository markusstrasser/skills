Here is the domain-specific verification of the claims and implementations in the Plan-Close packet. 

### 1. Python Path Bootstrapping for `llmx`
* **Claim:** The new `llm-dispatch.py` wrapper successfully loads the `llmx` module.
* **Verdict:** UNVERIFIABLE
* **If UNVERIFIABLE:** What would you need to check? `llmx` is installed globally as a `uv tool`, meaning its `site-packages` live in an isolated `.local/share/uv/tools/llmx/` virtual environment. The old shell scripts manually injected this path via `sys.path.insert(0, glob.glob(...))`. The excerpts for `scripts/llm-dispatch.py` and `shared/llm_dispatch.py` do not show this dynamic discovery logic. If it is not present in the truncated portions of `shared/__init__.py` or `shared/llm_dispatch.py`, **every call to `uv run python3 scripts/llm-dispatch.py` will hard-crash** with `ImportError: No module named llmx`.

### 2. `model-review.py` Migration Compliance
* **Claim:** `review/scripts/model-review.py` migrated to use the shared dispatch profile system as mandated.
* **Verdict:** WRONG (Profile Governance Issue)
* **If WRONG:** While the script imports `shared.llm_dispatch as dispatch_core`, it actively bypasses the `DispatchProfile` abstraction. It maintains its own hardcoded `AXES` dict with raw model names (`gemini-3.1-pro-preview`) and API kwargs, and its tests (`test_model_review.py`) prove it is patching the private `_LLMX_CHAT` function rather than calling the top-level `dispatch(profile=...)`. This creates a secondary, undocumented routing path that defeats the purpose of centralizing profiles for the agents.

### 3. Agent LLMx Debugging Workflow
* **Claim:** The `llmx-guide` skill correctly teaches agents how to debug transport issues.
* **Verdict:** WRONG (Agent Workflow Breakage)
* **If WRONG:** `llmx-guide/SKILL.md` explicitly instructs agents to use raw CLI commands for low-level transport debugging (e.g., `llmx chat -m gpt-5.4 --debug ...`). However, the `pretool-llmx-guard.sh` matches `echo "$CMD" | grep -qE 'llmx\s+chat'` and forces an unconditional `exit 2` block. Any agent following the `llmx-guide` to diagnose failures will be trapped in a blocked-tool loop. The guard must either allow `--debug` or the guide must be rewritten.

### 4. `pretool-llmx-guard.sh` Downstream Rules
* **Claim:** The `pretool-llmx-guard.sh` script applies downstream warning checks (like missing `-o`, or piped stdin dropping) to all llmx calls.
* **Verdict:** WRONG (Dead Code / Silent Logic Failure)
* **If WRONG:** Because `llmx chat` is now a hard block that triggers `exit 2` at line 108, the process terminates immediately. Any subsequent rules in the script that check for `llmx chat` (like `# 6. Stdin pipe + prompt arg... && echo "$CMD" | grep -qE 'llmx\s+chat\s'`) are now dead code and will never evaluate.

### 5. `run-cycle.sh` Error File Checking
* **Claim:** `run-cycle.sh` correctly reads the error payload if the dispatch helper fails.
* **Verdict:** WRONG (Silent Failure Path)
* **If WRONG:** The script creates the error file using `cycle_error=$(mktemp ...)`. During the failure evaluation, it checks `if [ -f "$cycle_error" ]; then cat "$cycle_error" >&2`. Because `mktemp` guarantees the file is created, `-f` will *always* be true. If `llm-dispatch.py` crashes early without writing JSON to that file, `run-cycle.sh` will blindly cat an empty file to stderr instead of falling back to reading `cycle_meta`, completely hiding the failure context from the agent. This must use `[ -s "$cycle_error" ]` (file size > 0).

### 6. Legacy `OVERVIEW_MODEL` Migration Seam
* **Claim:** `hooks/generate-overview.sh` preserves compatibility with sibling repos using the old `OVERVIEW_MODEL` config while shifting the backend to the Python dispatcher.
* **Verdict:** CORRECT
* **Context:** The `resolve_overview_profile` safely maps the old string keys to the new profile keys (e.g., `gemini-3-flash-preview` -> `fast_extract`), prioritizes `OVERVIEW_PROFILE` if present, and the shell code gracefully parses `resolved_model` out of the new `$dispatch_meta` file with a safe `|| echo "unknown"` fallback so the header timestamps do not break.

### 7. File Writing in `improve/SKILL.md`
* **Claim:** `improve/SKILL.md` correctly delegates file persistence to the shared wrapper.
* **Verdict:** CORRECT
* **Context:** The previous version of the skill relied on returning an object and calling `Path(...).write_text(response.content)`. The updated python snippet passes `output_path=Path(...)` directly to the `dispatch()` function. This is safe, atomic, and removes a boilerplate failure path for the agent.