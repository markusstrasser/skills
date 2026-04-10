Here is the domain-specific review of the Context Packet Integration Plan, evaluating the codebase mechanics, architectural claims, and potential migration breakages based on the provided source code.

### 1. The Abstraction Boundary Claim
**Claim:** "The thing that generalizes is: file blocks, diff blocks, text blocks, command/output blocks... The thing that does not generalize is: which files matter... what sections are semantically relevant. The correct abstraction boundary is: shared packet mechanics, task-specific builders/selectors."
**Verdict:** **CORRECT**
**Analysis:** This is a highly accurate domain abstraction. The duplication across `build_plan_close_context.py` (which manually concatenates git diffs and excerpts with `max_chars` logic) and `model-review.py` (which manually implements `parse_file_spec` and string-joins file ranges) proves the shared mechanical need. Keeping the *selection* of those files (e.g., git status vs. explicit axis targets) in task-specific builders correctly prevents the packet engine from becoming a monolithic god-object.

### 2. The Overview Generation Migration Claim
**Claim:** "hooks/generate-overview.sh... move prompt/context assembly into a shared Python overview packet builder. Keep shell orchestration only for process control if still needed."
**Verdict:** **WRONG** (Packet-engine overreach & hidden complexity lie)
**What's actually true:** `generate-overview.sh` does not assemble individual files the way the Python scripts do. It heavily relies on `repomix --stdout --include "$include_pattern"`, which handles its own complex domain logic: `.gitignore` parsing, recursive directory traversal, binary file exclusion, and XML-like formatting (`<codebase>`).
If the Python packet engine tries to natively replicate this via `FileBlock`s, it will lose `repomix`'s robust repository-packing logic and introduce severe regressions. If the plan intends for the Python builder to simply shell out to `repomix` and wrap the result in a single `TextBlock` or `CommandBlock`, the Python migration yields almost zero structural benefit for this specific script while adding an unnecessary cross-language boundary (shell -> Python -> shell out to repomix -> Python -> shell).
**Correction:** The plan must explicitly state that `repomix` remains the engine for overview codebase aggregation, and the Python builder must only wrap its output block, or defer the overview migration until the packet engine natively matches `repomix` capabilities.

### 3. The Batch Processing Support Claim
**Claim:** "Markdown + manifest JSON is enough for v1 [rendering]. generate-overview-batch.sh... eventually reuses the same overview packet builder as live generation."
**Verdict:** **WRONG** (Abstraction mismatch / breaks batch API workflows)
**What's actually true:** `generate-overview-batch.sh` does not just need Markdown. It natively constructs `JSONL` formatted requests mapped to a `MANIFEST` file (lines 140-160 in the batch script) for the llmx/Gemini Batch API. A packet engine that only outputs Markdown strings will break the batch submission pipeline unless the shell script continues to do the JSONL wrapping manually.
**Correction:** The `shared/context_renderers.py` layer must support an envelope renderer (e.g., `BatchJSONLRenderer`) or the target architecture must explicitly define how `ContextPacket` objects serialize directly into batch job payloads, bypassing standalone markdown files entirely.

### 4. The Budget / Truncation Testing Claim
**Claim:** "Required tests: file path parsing, single-line and range excerpt extraction, diff block rendering, packet manifest emission, truncation markers, deterministic rendering... touched-file resolution."
**Verdict:** **WRONG** (Critical missing tests)
**What's actually true:** The plan ignores the single biggest point of failure in context assembly: context window overflow. The current `generate-overview.sh` script relies heavily on token math (`prompt_tokens=$((prompt_size / 4))`) to validate bounds before dispatch (lines 200-210). If the shared packet engine takes over "size budgeting / truncation", it must test token estimation and hard-limit enforcement.
**Correction:** Add `token limit estimation` and `budget-aware block eviction` to the Required Tests. Without this, the engine will confidently build 300,000-token review packets that crash down-stream `llm_dispatch.py` calls.

### 5. The Preamble Injection / Constitution Gathering Claim
**Claim:** "model-review.py... delete local preamble-building duplication where possible. Keep constitutional anchoring, but source the preamble assembly from shared selectors/helpers."
**Verdict:** **CORRECT**
**Analysis:** Lines 485-492 of `model-review.py` currently hardcode a critical "Development Context" preamble (enforcing AI-agent economic realities). Lines 470-480 crawl for `CONSTITUTION.md` and `GOALS.md`. Moving these to a shared `context_selectors.py` is correct and necessary. *Note for implementation:* Ensure the verbatim AI-agent economics block is preserved identically in the shared selector, as this is critical prompt engineering to prevent models from giving lazy "human" coding advice.

### 6. The "Thin Builder Wrappers" Migration Strategy
**Claim:** "Preserve a thin compatibility wrapper where callers already use a specific script path, but move the real logic into shared code. [For build_plan_close_context.py] keep CLI contract if users/scripts already call it."
**Verdict:** **CORRECT**
**Analysis:** This adheres strictly to the constraint: never trade stability for dev time. Keeping the existing script entrypoints (`review/scripts/build_plan_close_context.py`) and just replacing their guts with the new `PlanClosePacketBuilder` guarantees zero blast radius for external hooks, CI pipelines, or agents currently relying on those exact CLI arguments (`--repo`, `--tracked-only`, `--max-files`). 

### 7. The Scope Fallback Claim
**Claim:** `build_plan_close_context.py` correctly handles scope fallback if `scope_file` or `scope_text` are missing.
**Verdict:** **UNVERIFIABLE** (Requires checking external runner behavior)
**Analysis:** In the existing code, if no scope is provided, it injects a literal `"FILL ME"` block (lines 181-185). If the packet engine translates this blindly, it will embed `"FILL ME"` into automated, unattended review packets. I would need to check if the current CI/agent pipelines reliably supply `--scope-text` or `--scope-file`. If they don't, migrating this raw string behavior into a canonical shared builder might pollute automated review packets.
**Correction:** The `PlanClosePacketBuilder` should probably throw an exception if scope is missing during unattended execution, rather than writing a dead "FILL ME" template into the packet.

### Summary of Required Plan Adjustments before Execution:
1. **Exclude `repomix` deeply-nested assembly from Phase 4** or explicitly define how `CommandBlock(repomix)` preserves `.gitignore` and `OVERVIEW_EXCLUDE` vars.
2. **Add `JSONL Envelope Rendering`** to the rendering layer to support `generate-overview-batch.sh`.
3. **Add token-estimation tests** to Phase 1. Truncation based on character counts (`max_chars=8000`) is legacy; the engine needs tokenizer-aware budgets.