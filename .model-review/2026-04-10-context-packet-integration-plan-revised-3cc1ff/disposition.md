# Review Findings — 2026-04-10

**19 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** Overview scripts estimate tokens with a naive `wc -c / 4` heuristic
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review identifies the current token estimate in `hooks/generate-overview.sh` lines 203-204 and `hooks/generate-overview-batch.sh` line 114 as a hardcoded byte-division hack. It warns this can silently produce oversized packets and expensive failed model requests when migrated into shared packet-building logic.
   File: hooks/generate-overview.sh
   Fix: Replace byte-based estimation with a real tokenizer implementation, such as `tiktoken` or a provider-specific tokenizer, and use it for packet budgeting.

---

2. **[HIGH]** `build_plan_close_context.py` relies on brittle `git status --short` scraping
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review specifically calls out `build_plan_close_context.py` lines 42-55 for parsing `git status --short` output and argues that moving this logic unchanged into a selector would institutionalize a brittle implementation. The reviewer cites edge cases such as filenames with spaces, renames, copies, and quoting.
   File: build_plan_close_context.py
   Fix: Replace ad hoc string parsing with a robust git data source, such as `git status --porcelain -z` or `git diff --name-status -z`, and parse the NUL-delimited format safely.

---

3. **[HIGH]** Phase 4 preserves bash orchestration instead of eliminating it
   Category: architecture | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review flags the plan's allowance for `hooks/generate-overview.sh` to 'keep shell orchestration if needed' as a long-term maintenance problem. Evidence cited includes bash managing Python subprocesses, temp files via `mktemp`, and JSON metadata extraction via inline `python3 -c`, which the reviewer argues should not survive when a full Python rewrite is feasible.
   File: 
   Fix: Replace the live and batch overview shell scripts with a single Python entrypoint that handles orchestration, config loading, dispatch, temp files, and output writing natively.

---

4. **[HIGH]** God-module risk in context_selectors.py
   Category: architecture | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The proposed context_selectors.py mixes file-range parsing, git resolution, diff collection, and repomix capture, violating concern boundaries and creating a high-drift 'god helper'.
   File: context_selectors.py
   Fix: Split functionality into discrete modules such as file_specs.py, git_context.py, and repomix_source.py.

---

5. **[HIGH]** Deterministic hashing lacks normalization contract
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   Plan distinguishes hashes but fails to define newline normalization, trailing whitespace, path normalization, or section ordering, making hashes sensitive to environment/OS.
   File: 
   Fix: Specify and implement a normalization contract including versioning and ordering rules before hashing.

---

6. **[HIGH]** `ContextPacket` budget handling lacks model-aware tokenizer integration
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   Beyond the current shell heuristic, the review says the proposed shared packet builder only exposes `token_estimate: int | None` and a loose `BudgetPolicy` without specifying how accurate, model-specific token counting will occur. It recommends coupling budget enforcement to `llm_dispatch.py` profile metadata so truncation happens before API dispatch.
   File: 
   Fix: Make budget policy query dispatch/profile metadata for token limits and tokenizer choice, then compute exact counts and truncate in the packet builder before sending requests.

---

7. **[MEDIUM]** `overview.conf` parsing is duplicated in fragile bash code
   Category: missing | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review notes that `generate-overview-batch.sh` lines 40-60 and `generate-overview.sh` both contain effectively the same regex/string-replace parser for `.claude/overview.conf`. This duplication is called out as brittle and omitted from the migration plan.
   File: hooks/generate-overview-batch.sh
   Fix: Move all `overview.conf` parsing and resolution into a shared Python implementation used by both live and batch overview generation.

---

8. **[MEDIUM]** Python migration does not absorb atomic write and metadata injection behavior
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review points to `hooks/generate-overview.sh` lines 224-241, where the shell script performs atomic replacement and injects freshness metadata such as `<!-- Generated: ... -->`. It argues that unless the Python builder takes over both safe-write semantics and metadata generation, shell will still need to manipulate the final artifact text.
   File: hooks/generate-overview.sh
   Fix: Implement atomic file writing and optional metadata/header injection in the Python overview generator so the shell wrapper can be removed entirely.

---

9. **[MEDIUM]** Deterministic hashing strategy is unresolved with embedded generated timestamps
   Category: logic | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review identifies a mismatch between the plan's requirement for deterministic hashes excluding metadata and the current overview flow, which injects `<!-- Generated: [TIMESTAMP] ... -->` directly into the text stream. It says the plan does not explain how these embedded timestamps will coexist with stable `content_hash` values.
   File: hooks/generate-overview.sh
   Fix: Separate volatile generation metadata from hashed content, or exclude/strip timestamped sections when computing content hashes and cache keys.

---

10. **[MEDIUM]** Incomplete overview migration allows continued drift
   Category: logic | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The plan only migrates prompt/context assembly, leaving config parsing and include-pattern construction in shell scripts (generate-overview.sh/batch.sh), resulting in partial unification.
   File: scripts/generate-overview.sh
   Fix: Centralize overview config parsing and repomix argument construction in Python.

---

11. **[MEDIUM]** Unification fails due to inconsistent budget metrics
   Category: logic | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   System uses chars for some truncations, tokens for others, and 'bytes/4' for estimates; a shared budget engine cannot function without a shared metric.
   File: 
   Fix: Adopt a single shared metric engine and label manifests with the estimation method used.

---

12. **[MEDIUM]** Model-review creates redundant context files
   Category: performance | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The current plan still allows model-review to write N identical context files for N axes, maintaining duplication of content and storage.
   File: model-review.py
   Fix: Update model-review to point all axes to a single shared content path if the content hash is identical.

---

13. **[MEDIUM]** Constitutional preamble should be a non-truncatable block type
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   For `model-review.py`, the review argues that the constitutional preamble logic at lines 463-480 should not just be a helper. It recommends formalizing it as a `PreambleBlock` so truncation policies cannot cut the constitution and invalidate the review packet.
   File: model-review.py
   Fix: Introduce a dedicated `PreambleBlock` (or equivalent) in the packet model and exempt it from normal truncation rules.

---

14. **[MEDIUM]** Migration plan lacks golden output-equivalence tests
   Category: missing | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The reviewer prioritizes strict golden-fixture tests before any refactor, warning about 'silent migration drift.' They recommend byte-for-byte fixture comparisons for `plan-close` and `model-review` output before introducing shared packet abstractions.
   File: 
   Fix: Add golden markdown fixtures and automated byte-match regression tests for legacy packet outputs before starting the migration.

---

15. **[MEDIUM]** Repomix capture strategy does not address large stdout handling
   Category: performance | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review says the plan's mention of an optional `repomix` capture helper is too vague given the current subprocess call at `generate-overview.sh` line 197. It specifically warns that dumping massive `repomix` stdout into in-memory strings can create memory bloat on large repositories.
   File: hooks/generate-overview.sh
   Fix: Design repomix integration to stream output to a file or use a streamed block abstraction rather than always materializing the entire payload in memory.

---

16. **[MEDIUM]** BuildArtifact underspecified for overview requirements
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The BuildArtifact schema lacks the prompt string data ('Write the requested codebase overview...') required by the overview flow, making the handoff boundary insufficient.
   File: context_packet.py
   Fix: Extend BuildArtifact to include prompt payloads or ensure the shared core handles task-specific instructions.

---

17. **[MEDIUM]** Missing policy for non-text files
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Current strategy lacks explicit handling for binary files, symlinks, or submodules, which may lead to silent mis-rendering.
   File: context_selectors.py
   Fix: Implement excerpt policy tests specifically for binary, symlink, and submodule inputs.

---

18. **[LOW]** Grep-based enforcement is architecturally weak
   Category: style | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Using grep to prevent helper duplication is easily evaded by renaming and doesn't verify behavioral consolidation.
   File: 
   Fix: Replace grep checks with behavioral contract tests and strict import constraints in CI.

---

19. **[LOW]** Python batch overview rewrite may require missing batch abstractions in `llm_dispatch.py`
   Category: missing | Confidence: 0.6 | Source: Gemini (architecture/patterns)
   In the reviewer's blind spots, they note that `generate-overview-batch.sh` currently builds JSONL for `llmx` and assume Python can use batch generation through `shared/llm_dispatch.py`. They explicitly warn that this assumption may be false and that removing the shell path could expose missing batch-dispatch features.
   File: 
   Fix: Verify or implement native batch request construction/submission in `shared/llm_dispatch.py` before replacing the batch shell script.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

