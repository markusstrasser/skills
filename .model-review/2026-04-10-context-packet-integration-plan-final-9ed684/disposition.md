# Review Findings — 2026-04-10

**24 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** `DispatchProfile` does not expose input-token limits needed for budget enforcement
   Category: missing | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review points out that `shared/llm_dispatch.py` defines `PROFILES` with only `max_tokens`, which governs output tokens, but does not publish `context_window` or `input_token_limit`. As written, a packet builder cannot enforce model-specific input budgets because the dispatch layer does not define them.
   File: shared/llm_dispatch.py
   Fix: Extend `DispatchProfile`/`PROFILES` with an explicit input-token budget field such as `input_token_limit` (and optionally context window metadata), and make packet builders consume it.

---

2. **[HIGH]** `build_plan_close_context.py` truncates diffs by raw character count and breaks patch structure
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review points to `build_plan_close_context.py` slicing diff output with `diff_text[:max_diff_chars]`. It argues that this can cut through the middle of unified diff hunks or file sections, breaking diff syntax, ruining syntax highlighting, and causing models to hallucinate file boundaries.
   File: build_plan_close_context.py
   Fix: Truncate diffs only at safe boundaries such as whole-file or whole-hunk boundaries, ideally in `shared/git_context.py`, and emit an explicit truncation marker.

---

3. **[HIGH]** `generate-overview.sh` uses an inaccurate `wc -c / 4` token heuristic
   Category: logic | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review flags the shell math in `hooks/generate-overview.sh` that estimates tokens by dividing byte count by 4. It states this is highly inaccurate for dense codebases and causes random dispatch failures when model limits are exceeded.
   File: hooks/generate-overview.sh
   Fix: Replace the `wc -c` heuristic with profile-aware token budgeting from shared Python code, using an explicit token estimate implementation tied to dispatch limits.

---

4. **[HIGH]** `llm_dispatch.py` recomputes context hashes instead of consuming builder manifests
   Category: architecture | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review says `llm_dispatch.py` calculates `context_sha256 = _sha256(context_body)` and writes it into `meta.json`, even though the proposed artifact layer would already provide a `payload_hash`. It also states dispatch currently accepts only raw text or unstructured paths, so the `BuildArtifact` contract is orphaned unless dispatch can ingest a manifest directly.
   File: shared/llm_dispatch.py
   Fix: Add manifest-aware dispatch input (for example `--context-manifest`) and have dispatch reuse artifact `payload_hash`/token metadata instead of recomputing hashes from raw text.

---

5. **[HIGH]** `parse_status_paths` in `build_plan_close_context.py` breaks on spaces and renames
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review says the current status parsing in `build_plan_close_context.py` relies on `parse_status_paths`, and explicitly claims it fails on filenames containing spaces and on rename records. The reviewer recommends replacing this with `git status --porcelain -z` / `git diff --name-status -z` parsing in a shared helper to avoid silent path corruption.
   File: build_plan_close_context.py
   Fix: Remove ad hoc status parsing and centralize path extraction in `shared/git_context.py` using NUL-delimited git output (`--porcelain -z`, `--name-status -z`).

---

6. **[HIGH]** Missing failure rule for budget vs protected blocks
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   PreambleBlock is protected from truncation, but the system also enforces hard budgets. There is no defined behavior for when protected blocks alone exceed the budget.
   File: 
   Fix: Extend the packet build contract to include an explicit 'budget_exceeded' or 'unrenderable_within_budget' failure outcome.

---

7. **[HIGH]** Under-defined hash taxonomy for content vs payload
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The manifest defines content_hash as normalized rendered content, but payload_hash (used for live/batch equivalence and model-consumable payloads) lacks a byte-scope definition. This makes hashes incomparable across different builders.
   File: 
   Fix: Define a strict hash taxonomy with explicit byte-scopes for source_hash, block_hash, content_hash, payload_hash, and output_hash.

---

8. **[HIGH]** Unspecified handling of non-text source entities
   Category: missing | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The plan requires test coverage for binary files, symlinks, and submodules, but no normative behavior or placeholder policy is defined for these types.
   File: 
   Fix: Create a source-entity policy matrix specifying exact rendering and manifest behavior for text, binary, deleted, symlink, and submodule entities.

---

9. **[HIGH]** Ambiguous equivalence target for Overview live/batch
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   Current live paths prepend freshness metadata to final outputs, making byte-for-byte equivalence with batch mode impossible unless the 'payload' scope is strictly isolated.
   File: 
   Fix: Introduce a single Python API that returns the exact prompt payload artifact and require both live and batch wrappers to call it.

---

10. **[HIGH]** Inconsistent token budget metadata in dispatch profiles
   Category: logic | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The plan relies on profile-aware token budgets, but profiles in 'shared/llm_dispatch.py' inconsistently define context-window limits, often conflating them with output-token limits.
   File: shared/llm_dispatch.py
   Fix: Standardize dispatch profiles to explicitly expose context-window limits separate from output limits.

---

11. **[MEDIUM]** `llm_dispatch.py` still contains a duplicate `assemble_context` packet builder
   Category: architecture | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review notes that `shared/llm_dispatch.py` already contains its own `assemble_context(sources)` helper that renders labeled sources into a prompt string. This duplicates the proposed canonical packet assembly layer and prevents a single integration spine for context construction.
   File: shared/llm_dispatch.py
   Fix: Delete `assemble_context` from `shared/llm_dispatch.py` and migrate its callers to `shared/context_packet.py`.

---

12. **[MEDIUM]** Batch overview generation still assembles JSONL via raw string interpolation
   Category: logic | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review flags `generate-overview-batch.sh` for constructing a single JSONL file using `python3 -c "import json..."` and raw string interpolation. The reviewer argues that unless the shared builder emits JSONL-ready rows natively, batch mode will keep using ad hoc string assembly and may violate `content_hash` equivalence with live generation.
   File: generate-overview-batch.sh
   Fix: Move JSONL row generation into shared Python code so live and batch modes serialize the same payload structure from the same builder output.

---

13. **[MEDIUM]** Overview payloads collide with `llm_dispatch.py` prompt wrapping
   Category: logic | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review says `hooks/generate-overview.sh` treats the built "context" as the entire prompt (`instructions + codebase`), while `shared/llm_dispatch.py` `_build_full_prompt()` always concatenates `context_text + "\n\n---\n\n" + prompt`. If overview generation starts passing a single built artifact as `--context`, dispatch will wrap an already-complete prompt in an extra delimiter structure.
   File: shared/llm_dispatch.py
   Fix: Define a dispatch mode that accepts a fully assembled prompt artifact without adding the default context/prompt delimiter, or split overview artifacts into true context and prompt components.

---

14. **[MEDIUM]** There is no canonical shared context-packet module
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review repeatedly recommends a single `shared/context_packet.py` layer with primitives such as `PacketSection`, `TextBlock`, and `FileBlock`, preserving structured filepath and line-range metadata before rendering. The current design is described as fragmented: context assembly logic is spread across scripts instead of being centralized.
   File: shared/context_packet.py
   Fix: Create `shared/context_packet.py` as the sole context assembly engine and migrate existing packet/prompt construction to it.

---

15. **[MEDIUM]** Overview generation should be rewritten in Python rather than orchestrated in bash
   Category: architecture | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review explicitly argues against keeping `generate-overview-batch.sh` as the primary orchestrator and later expands that recommendation to both live and batch overview flows. The proposed direction is a single Python orchestrator that reads config, calls the packet engine, invokes repomix, and writes output/JSONL, with shell scripts reduced to thin `exec uv run ...` pass-throughs.
   File: generate-overview-batch.sh
   Fix: Replace bash-heavy overview orchestration with a Python entry point (for example `scripts/overview_generator.py`) and keep shell wrappers minimal.

---

16. **[MEDIUM]** `model-review.py` still uses ad hoc file-spec parsing instead of shared helpers
   Category: logic | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review recommends deleting ad hoc parsing in `model-review.py` and relying entirely on `shared/file_specs.py` for `path:start-end` resolution. This implies the current file-spec handling in `model-review.py` is duplicated and should be replaced by the shared implementation.
   File: model-review.py
   Fix: Remove custom file-spec parsing from `model-review.py` and delegate all range parsing/resolution to `shared/file_specs.py`.

---

17. **[MEDIUM]** Truncation logic may leave markdown code fences unclosed
   Category: bug | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review recommends that any truncation of code or diffs must close open markdown fences, giving an explicit example of appending `...` and a closing ``` fence before a truncation notice. Without this, truncated packets can leave malformed markdown/code blocks.
   File: 
   Fix: Update truncation helpers to detect open fences and always close them before appending truncation notices.

---

18. **[MEDIUM]** Context artifacts lack deterministic manifest/provenance hashes
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review identifies a blind spot in the current review-packet flow: there is no `BuildArtifact`-style manifest with deterministic `content_hash` and `payload_hash`. The reviewer says this prevents reliable debugging, trace verification, and perfect cacheability of built context packets.
   File: 
   Fix: Introduce a `BuildArtifact` manifest for generated context/prompt artifacts, including stable content and payload hashes plus provenance metadata.

---

19. **[MEDIUM]** Phase ordering and test criteria sequencing inconsistency
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Phase 1 exit criteria include equivalence tests for overview payloads and plan-close artifacts, but the migration for those components does not occur until Phase 2 and Phase 4.
   File: 
   Fix: Move component-specific equivalence tests to the phases where those components are actually migrated.

---

20. **[MEDIUM]** Lack of automated enforcement against helper duplication
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Success criteria prohibit duplicated helpers, but enforcement is described as manual or test-based rather than using machine-checkable AST or import boundary gates.
   File: 
   Fix: Implement CI-level grep or AST rules (e.g., preventing 'parse_file_spec' definitions outside 'shared/file_specs.py').

---

21. **[MEDIUM]** Incomplete selector precedence rules for migration
   Category: logic | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Legacy plan-close code has implicit precedence (e.g., --file overrides touched-file discovery) that is not recorded in the migration plan, risking silent drift.
   File: 
   Fix: Explicitly document and formalize the precedence of selector rules (explicit files vs git ranges vs worktree).

---

22. **[LOW]** `model-review.py` keeps constitutional/preamble logic inline instead of sharing it
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review proposes stripping constitutional logic out of `model-review.py` into `shared/context_preamble.py`. This indicates the current implementation mixes preamble/constitutional semantics into the review script instead of reusing a shared component.
   File: model-review.py
   Fix: Extract constitutional or preamble-building logic into `shared/context_preamble.py` and have `model-review.py` consume that shared helper.

---

23. **[LOW]** Low-value CLI surface expansion
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The proposed 'scripts/context-packet.py' adds a public surface and compatibility burden that may be unnecessary if importable builders are the primary integration mode.
   File: scripts/context-packet.py
   Fix: Deprioritize or remove the generic CLI unless specifically required by shell-facing consumers.

---

24. **[LOW]** Domain-specific logic leak in shared preamble helper
   Category: style | Confidence: 0.7 | Source: GPT-5.4 (quantitative/formal)
   The 'context_preamble.py' module includes constitution and agent-economics text assembly, which is semantically specialized for reviews rather than being a generic packet mechanic.
   File: context_preamble.py
   Fix: Isolate mechanical preamble assembly from task-specific semantic content.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

