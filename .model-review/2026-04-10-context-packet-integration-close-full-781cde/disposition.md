# Review Findings — 2026-04-10

**14 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** Plan-close manifest budget does not describe the actual packet budget
   Category: logic | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   build_plan_close_context.py sets BudgetPolicy(metric="chars", limit=max_diff_chars), default 40_000. However, the packet includes up to 96_000 chars of excerpts plus metadata, meaning the manifest reports a limit that is only ~29% of the actual packet ceiling.
   File: build_plan_close_context.py
   Fix: Compute a total-packet budget bound or emit per-section limits (diff_limit, file_excerpt_limit, etc) instead of a single misleading budget_limit.

---

2. **[HIGH]** Overview trigger default threshold is inconsistent across consumers
   Category: logic | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   shared/overview_config.py defaults OVERVIEW_LOC_THRESHOLD to 200, but hooks/sessionend-overview-trigger.sh defaults to 50, causing inconsistent automation behavior depending on which consumer reads the config.
   File: shared/overview_config.py
   Fix: Unify all overview.conf parsing through shared.overview_config; replace manual parsing in shell scripts with the shared helper.

---

3. **[HIGH]** Live overview default prompt location changed without compatibility proof
   Category: architecture | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The default prompt location shifted from .claude/overview-prompts to ~/Projects/skills/hooks/overview-prompts, which may cause repositories relying on project-local prompts to fail or use incorrect defaults.
   File: shared/overview_config.py
   Fix: Codify a fallback order for prompt discovery (project-local first, shared second) and add compatibility tests.

---

4. **[HIGH]** Dispatch is not packet-manifest canonical
   Category: architecture | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   shared/llm_dispatch.py still supports raw context transport and emits parallel hashes (context_sha256 and context_payload_hash), making canonical provenance optional rather than enforced.
   File: shared/llm_dispatch.py
   Fix: Deprecate raw-context dispatch and require context_manifest_path for automated entrypoints.

---

5. **[HIGH]** Overview generator no longer enforces the input token ceiling
   Category: logic | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review claims the old `generate-overview.sh` aborted when the prompt exceeded 900,000 tokens, but the new Python path only computes/stores the budget and never checks `token_estimate > input_token_limit` before dispatch. Evidence cited: `generate-overview.sh` had `if [[ $prompt_tokens -gt 900000 ]]; then ... return 1; fi`, while `scripts/generate_overview.py` allegedly omits the equivalent guard. The reviewer warns this can cause expensive API rejections or quota burn on large repositories.
   File: scripts/generate_overview.py
   Fix: Reintroduce a pre-dispatch validation in `scripts/generate_overview.py` that aborts when the estimated prompt tokens exceed the configured/input token limit (including the legacy 900k threshold behavior where appropriate).

---

6. **[HIGH]** Batch mode may reference undefined helper functions
   Category: bug | Confidence: 0.4 | Source: Gemini (architecture/patterns)
   The reviewer reports that `scripts/generate_overview.py` references `batch_submit_command` and `batch_get_command` inside `batch_mode()`, and warns that if those functions are truly absent, batch mode will fail with `NameError`. The reviewer also notes the context snippet was truncated, so this may depend on omitted code.
   File: scripts/generate_overview.py
   Fix: Ensure `batch_submit_command` and `batch_get_command` are defined/imported before use, or replace those calls with a supported execution path.

---

7. **[MEDIUM]** Binary and symlink fixture coverage is missing in context packet tests
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The reviewer states there is no fixture coverage for binaries or symlinks in `test_context_packet.py`, despite that coverage being explicitly called for in the mitigation plan. The recommended verification is that a binary file yields a placeholder like `[binary file omitted...]` instead of causing decode failures, and that symlinks are handled correctly.
   File: test_context_packet.py
   Fix: Add fixture-based tests in `test_context_packet.py` covering binary files and symlinks, asserting the expected placeholder/handling behavior.

---

8. **[MEDIUM]** Insufficient regression testing for migration claims
   Category: missing | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The current test suite fails to verify live-vs-batch payload hash equivalence, plan-close golden output, or binary/submodule omission behavior despite these being cited as risks.
   File: 
   Fix: Add a regression suite covering live/batch equivalence, plan-close golden packets, and constitution discovery matrices.

---

9. **[MEDIUM]** Diff truncation logic lacks unit tests
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review flags `shared/git_context.py`'s `truncate_diff_text` as complex and currently untested. Evidence cited: the function uses a line-by-line fallback, and without tests an off-by-one error could silently corrupt unified diff blocks or drop required headers such as `diff --git`.
   File: shared/git_context.py
   Fix: Add focused unit tests (for example in `test_git_context.py`) that feed multi-file diffs into `truncate_diff_text` and assert truncation occurs cleanly at file/line boundaries without mangling patch structure.

---

10. **[MEDIUM]** Live-vs-batch payload hash equivalence test is missing
   Category: missing | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review says the implementation failed its own mitigation plan by not adding the promised 'exact payload-hash equivalence tests' for live versus batch modes. Evidence cited: there are no tests asserting that the live packet build and the batch request path produce identical `payload_hash` values for the same repository/input.
   File: 
   Fix: Add a test (for example in `test_generate_overview.py`) that runs the live builder and batch loop on the same mocked repo/input and asserts identical `payload_hash` output.

---

11. **[MEDIUM]** Constitution discovery semantics narrowed relative to reference contract
   Category: logic | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   shared/context_preamble.py ignores general CONSTITUTION.md files at the root or in docs/, only checking .claude/rules/constitution.md or CLAUDE.md, causing a semantic regression.
   File: shared/context_preamble.py
   Fix: Update the shared preamble helper to include broad CONSTITUTION.md discovery as described in documentation.

---

12. **[LOW]** Leftover ad hoc contract parsing in shell hooks
   Category: logic | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   Shell scripts sessionend-overview-trigger.sh and overview-staleness-cron.sh still parse overview.conf manually instead of utilizing the centralized shared.overview_config utility.
   File: hooks/sessionend-overview-trigger.sh
   Fix: Replace manual shell-based parsing of config files with calls to the shared Python configuration module.

---

13. **[LOW]** Atomic write helpers are duplicated across shared modules
   Category: architecture | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review notes duplication of `atomic_write_text` and `atomic_write_json` functionality between `shared/llm_dispatch.py` and `shared/context_packet.py`. This increases maintenance overhead and risks behavioral drift between two implementations of the same utility.
   File: shared/llm_dispatch.py
   Fix: Remove the duplicate implementation (for example `_atomic_write_text` in `shared/llm_dispatch.py`) and import/reuse a single canonical atomic write helper from one shared module.

---

14. **[LOW]** Batch orchestration should call subprocesses directly instead of wrapper helpers
   Category: architecture | Confidence: 0.6 | Source: Gemini (architecture/patterns)
   As an alternative design recommendation, the review argues that batch command execution should use `subprocess.run(["uv", "run", "llmx", "batch", ...])` inline rather than wrapping those CLI calls in helper functions such as `batch_submit_command`. The stated rationale is to keep orchestration clearer and closer to the prior shell behavior.
   File: scripts/generate_overview.py
   Fix: Simplify batch orchestration by inlining the `subprocess.run(...)` calls for submit/get operations instead of introducing thin wrapper helpers, unless those helpers provide substantive reusable behavior.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

