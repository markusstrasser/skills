# Review Findings — 2026-04-10

**13 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** Truncation helpers do not honor their own max_chars contracts
   Category: bug | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   The functions read_file_excerpt and truncate_diff_text return content longer than max_chars because they append truncation markers after selecting characters up to the limit. In read_file_excerpt, the output is head + TRUNCATION_MARKER + tail, where head + tail equals max_chars, making the total length > max_chars.
   File: shared/file_specs.py
   Fix: Rewrite truncation helpers so marker insertion is included inside the character budget, not appended after it.

---

2. **[HIGH]** Diff truncation appends marker outside of budget
   Category: bug | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   In truncate_diff_text, selected diff content is kept within max_chars, but then a newline and DIFF_TRUNCATION_MARKER are appended, resulting in a returned length exceeding the specified limit.
   File: shared/git_context.py
   Fix: Modify truncate_diff_text to account for the marker length within the max_chars calculation.

---

3. **[HIGH]** ContextPacket does not enforce BudgetPolicy or perform real truncation
   Category: architecture | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review states that `shared/context_packet.py` was supposed to own packet primitives, section composition, and truncation, but currently performs zero actual truncation. `BudgetPolicy` is only recorded in the manifest, while `build_plan_close_context.py` still manually truncates by character length before creating packet blocks. The reviewer also notes this leaves the original risk unmitigated: overly large packets can still be handed to dispatch because truncation is not tied to practical model limits.
   File: shared/context_packet.py
   Fix: Implement token-aware truncation inside the packet engine (or a shared builder/enforcer) so raw blocks are passed in and the engine drops or truncates lower-priority content until an estimated token budget fits `BudgetPolicy.limit`. Remove pre-packet manual truncation from callers.

---

4. **[HIGH]** build_plan_close_context.py still uses legacy character caps instead of profile-based model budgets
   Category: architecture | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review flags that `build_plan_close_context.py` retains `--max-diff-chars 40_000` and `--max-file-chars 8_000` rather than adjusting dynamically from a dispatch profile's input token budget. It further states the script has no concept of which model will consume the packet, so it cannot look up the correct `DispatchProfile` input limit. This undermines the intended migration to model-aware budgeting.
   File: build_plan_close_context.py
   Fix: Replace static character-limit arguments with a `--profile` or equivalent model-selection input, look up the profile from dispatch configuration, and derive packet truncation from the model's input token budget.

---

5. **[HIGH]** Plan-close manifest budget is mathematically inconsistent
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The BudgetPolicy sets a limit based on max_diff_chars for the whole ContextPacket, but only the diff block is actually truncated by this value. File excerpts are separately capped, allowing the total artifact to exceed the declared budget by over 3.4x (approx 136,000 chars vs 40,000 char limit).
   File: review/scripts/build_plan_close_context.py
   Fix: Replace single packet-level budget with an honest total upper bound or separate manifest fields for packet_budget_limit and block_limits.

---

6. **[HIGH]** Lack of hash-equivalence tests for overview payloads
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   There is no visible test asserting that live and batch overview paths produce identical payload hashes for the same repository state and configuration, leaving the 'shared path' claim unverified.
   File: scripts/generate_overview.py
   Fix: Implement equivalence tests that build the same overview payload through both live and batch paths and assert payload_hash equality.

---

7. **[MEDIUM]** generate_overview.py double-buffers repomix output through disk and memory
   Category: performance | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review says `generate_overview.py` writes repomix output to `.overview-{type}-codebase.txt`, then reads the entire file back into memory using `repomix_output.read_text()`, wraps it in a packet, and writes it again as `.overview-{type}-payload.txt`. For large codebases this creates unnecessary disk I/O and memory overhead.
   File: generate_overview.py
   Fix: Avoid full-file `read_text()` and support streaming into the final payload, e.g. via a `FileStreamBlock` or by writing the repomix output directly into the payload artifact without reloading the whole file into RAM.

---

8. **[MEDIUM]** test_context_packet.py lacks tests for budget-driven truncation
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review says `test_context_packet.py` only covers basic manifest generation and file spec parsing, and does not test behavior when a packet exceeds a token budget. The reviewer ties this directly to the missing truncation engine: there is no test asserting that a large packet is reduced to fit a model budget.
   File: test_context_packet.py
   Fix: Add tests that construct packets larger than the allowed budget and verify the packet engine truncates or drops lower-priority blocks until the estimated token count fits the selected policy/profile.

---

9. **[MEDIUM]** Overview manifests missing source provenance for primary inputs
   Category: missing | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The build_overview_packet function creates TextBlocks for instructions and codebase without metadata paths. Because build_manifest only records source_path when block.metadata['path'] exists, the resulting manifest is empty for these dominant inputs.
   File: scripts/generate_overview.py
   Fix: Attach metadata={'path': str(prompt_file)} to the instructions block and metadata={'path': str(repomix_output)} to the codebase block.

---

10. **[MEDIUM]** Migration claim of inspectable provenance is incomplete
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The system produces artifact hashes without auditable source lineage for overview generation. The manifest exists but fails to identify which prompt file or repomix snapshot was used.
   File: shared/context_packet.py
   Fix: Update build_manifest to ensure provenance captures both prompt templates and source snapshots consistently.

---

11. **[MEDIUM]** Inadequate test coverage for new artifact contract
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Current tests focus on rendered string output rather than the new ContextPacket models, manifest fidelity, or truncation bounds. Refactor risk has moved into manifests and budgets, but tests have not followed.
   File: review/scripts/test_build_plan_close_context.py
   Fix: Add unit tests to exercise build_packet_model and write_packet_artifact, specifically checking manifest source-path fidelity.

---

12. **[MEDIUM]** Missing adversarial tests for shared context helpers
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Shared helpers handle complex edge cases like binary files, symlinks, and renames, but visible test coverage only hits happy-path scenarios. A failure in these centralized helpers has a high blast radius.
   File: shared/file_specs.py
   Fix: Add fixture-driven tests and ensure 100% branch coverage for binary files, symlinks, deleted files, and renames with spaces.

---

13. **[MEDIUM]** model-review.py appears to generate redundant per-axis context files instead of one shared context
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review notes the plan explicitly called for stopping the creation of multiple semantically identical context payloads, but git status still shows axis-specific files such as `.model-review/.../arch-context.md` and `.model-review/.../formal-context.md`. Based on that evidence, the reviewer concludes `model-review.py` is still generating redundant context files per axis rather than one unified `shared-context.md` referenced by all review axes.
   File: model-review.py
   Fix: Assemble one `shared-context.md` and corresponding manifest per run, then have each axis reuse that shared artifact rather than writing separate near-identical context files.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

