# Review Findings — 2026-04-10

**24 findings** from 3 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** Missing golden output compatibility harness
   Category: missing | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   There is no requirement for bit-for-bit or equivalent output verification before migrating live paths, risking silent behavior/prompt drift.
   File: 
   Fix: Capture golden fixtures for plan-close and overview payloads and require byte-identity (excluding metadata) for migration pass.

---

2. **[HIGH]** Batch overview flow lacks JSONL envelope rendering support
   Category: missing | Confidence: 1.0 | Source: Gemini Pro (domain correctness)
   The review says the proposed rendering model is incomplete because `generate-overview-batch.sh` does more than emit Markdown: it constructs JSONL requests tied to a manifest for the llmx/Gemini Batch API. The reviewer cites lines 140-160 of the batch script as evidence. If the new packet system only renders Markdown plus a manifest, the batch submission workflow breaks unless downstream shell code manually reconstructs the JSONL payloads.
   File: hooks/generate-overview-batch.sh
   Fix: Add a batch-oriented renderer such as `BatchJSONLRenderer`, or define direct serialization from `ContextPacket` to batch job payloads so the batch pipeline can continue to emit API-ready JSONL without ad hoc shell wrapping.

---

3. **[HIGH]** Overview migration risks regressing repomix-based repository packing
   Category: architecture | Confidence: 1.0 | Source: Gemini Pro (domain correctness)
   The review flags the plan to move `hooks/generate-overview.sh` context assembly into a shared Python packet builder as overreach. The cited evidence is that this script currently depends on `repomix --stdout --include "$include_pattern"`, which already performs repository-specific logic such as `.gitignore` handling, recursive traversal, binary exclusion, and `<codebase>` formatting. Replacing that behavior with native Python `FileBlock` assembly would likely lose those semantics and cause migration regressions.
   File: hooks/generate-overview.sh
   Fix: Do not reimplement repomix behavior in the packet engine for this phase. Either keep `repomix` as the underlying aggregation engine and wrap its output as a packet block, explicitly preserving `.gitignore` and `OVERVIEW_EXCLUDE` behavior, or defer this migration until equivalent native capabilities exist.

---

4. **[HIGH]** New packet primitives do not preserve head/tail file excerpt truncation
   Category: missing | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review highlights that `build_plan_close_context.py` currently truncates large files by keeping both the beginning and end (`text[:head]` and `text[-tail:]`) at lines 142-149. The proposed `TextBlock`/`FileBlock` primitives do not specify how this behavior is represented, so a naive truncation implementation could keep only the start or only the end and lose critical end-of-file logic in plan-close reviews.
   File: build_plan_close_context.py
   Fix: Add a native truncation mode such as `HEAD_TAIL` to the shared packet model and preserve the current start-and-end excerpt behavior during migration.

---

5. **[HIGH]** Required tests omit token-budget estimation and hard-limit enforcement
   Category: missing | Confidence: 1.0 | Source: Gemini Pro (domain correctness)
   The review identifies a critical testing gap around context-window overflow. It notes that `generate-overview.sh` currently performs token math (`prompt_tokens=$((prompt_size / 4))`) before dispatch, citing lines 200-210. The migration plan only mentions truncation-oriented tests, but not tokenizer-aware estimation or eviction under a hard token cap. Without those tests, the shared packet engine could produce oversized packets that fail in downstream `llm_dispatch.py` calls.
   File: hooks/generate-overview.sh
   Fix: Add tests for token estimation accuracy, hard token-limit enforcement, and budget-aware block eviction/prioritization. The packet builder should validate size before dispatch using token-aware budgeting rather than only character-count truncation.

---

6. **[HIGH]** Shared context budgeting ignores incompatible char- and token-based limits
   Category: logic | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review flags a budgeting disconnect: `build_plan_close_context.py` uses character caps such as `max_diff_chars=40_000` and `max_file_chars=8_000`, while `generate-overview.sh` uses a rough token heuristic (`wc -c / 4`) and profile token limits. The reviewer warns that a shared truncation engine will mis-budget or behave inconsistently if it tries to unify these without standardizing the measurement model.
   File: 
   Fix: Introduce a single `ContextBudgeter` that budgets in `max_tokens` for all builders, using either the existing `wc -c / 4` heuristic or a real tokenizer such as `tiktoken`, and retire the ad hoc character limits.

---

7. **[HIGH]** Markdown-only builder output would break the batch JSONL path
   Category: missing | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review notes that `generate-overview-batch.sh` currently serializes request payloads into JSONL via inline Python at lines 135-141. If the new builder only emits Markdown files, the batch flow would need to re-read, escape, and re-serialize those files, creating a second handling layer and an additional failure point.
   File: generate-overview-batch.sh
   Fix: Have the builder support a native structured export, such as a Python `dict` or JSON-ready prompt/context payload, so the batch script can write JSONL directly without shell re-escaping Markdown.

---

8. **[HIGH]** Repomix handling is underestimated as a simple Python helper
   Category: architecture | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review says the plan's 'optional repomix capture helper' framing is misleading because `generate-overview.sh` depends on `repomix` for recursive directory resolution, `.gitignore` handling, and syntax-aware formatting. The reviewer argues that tightly wrapping a Node-based CLI inside Python would add orchestration and failure-mode management to the packet builder, increasing maintenance burden and blast radius.
   File: generate-overview.sh
   Fix: Keep `repomix` execution and its failure handling in the shell workflow, write its output to a temporary file, and have the Python packet builder ingest that file as an opaque input block rather than owning the CLI orchestration.

---

9. **[HIGH]** Overview renderer migration scope inconsistency
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The plan includes hooks/generate-overview.sh for migration but Phase 1 only specifies Markdown rendering. Current overview input uses a tagged prompt format (<instructions> and <code>), not a Markdown packet, creating a conflict in Phase 4.
   File: hooks/generate-overview.sh
   Fix: Update Phase 1 to include a second renderer for prompt-wrapped formats or redefine the overview output scope.

---

10. **[HIGH]** Budgeting and truncation policy missing from object contract
   Category: architecture | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   Despite budgeting being a success criterion, the ContextPacket and PacketSection models lack fields for token estimates, budgets, or truncation contracts, likely leading to ad hoc logic in builders.
   File: 
   Fix: Introduce a BudgetPolicy and token_estimate field into the shared packet object model.

---

11. **[MEDIUM]** Deterministic hash conflict with manifest timestamps
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The plan requires stable hashing and deterministic rendering but also includes 'created timestamp' in the manifest. If the hash covers the manifest, it cannot be stable across runs.
   File: 
   Fix: Explicitly define content_hash to cover normalized rendered content only, excluding run-metadata like timestamps.

---

12. **[MEDIUM]** Lack of mandatory Git fixture tests
   Category: missing | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The test plan is missing coverage for critical edge cases including renamed, deleted, and untracked files, as well as commit-range vs. worktree modes.
   File: 
   Fix: Implement Git fixture tests covering renamed/deleted/untracked files and valid/invalid file-spec ranges.

---

13. **[MEDIUM]** Overview config parsing will drift if Bash and Python both interpret overview.conf
   Category: bug | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The reviewer points out that `generate-overview-batch.sh` parses `.claude/overview.conf` with `eval` at lines 53-73 to obtain values like `OVERVIEW_EXCLUDE` and `OVERVIEW_SOURCE_DIRS`. If the Python builder also assumes responsibility for overview packet generation without replacing this parser, two independent parsers will likely diverge and cause include/exclude mismatches.
   File: generate-overview-batch.sh
   Fix: Make one component the single source of truth for `overview.conf` parsing: either keep parsing in Bash and pass resolved values into Python, or move parsing into a shared parser and delete the duplicated Bash logic.

---

14. **[MEDIUM]** Shared preamble migration must preserve the exact AI-agent economics guidance
   Category: constitutional | Confidence: 0.9 | Source: Gemini Pro (domain correctness)
   Although the overall preamble-selector migration is endorsed, the review adds a specific implementation warning: `model-review.py` currently hardcodes a critical `Development Context` block at lines 485-492 and discovers `CONSTITUTION.md`/`GOALS.md` around lines 470-480. The reviewer says the economics-focused prompt text should be preserved verbatim when moved into shared helpers, because altering it may degrade prompt behavior and lead models to produce unrealistic human-centric coding advice.
   File: model-review.py
   Fix: When extracting preamble assembly into shared selectors/helpers, keep the AI-agent economics block byte-for-byte identical and add a regression test to verify exact preservation of the migrated text.

---

15. **[MEDIUM]** Universal packet object model creates excessive coupling
   Category: architecture | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The plan treats plan-close, model-review, and overview as the same problem, but overview produces a tagged prompt rather than a Markdown document. A universal AST may introduce unnecessary maintenance drag.
   File: 
   Fix: Narrow the shared boundary to source fragments, provenance, and preamble composition instead of a forced universal AST.

---

16. **[MEDIUM]** Overview migration does not define ownership of concurrency and marker updates
   Category: architecture | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review says `generate-overview.sh` heavily manages concurrency and state, including background jobs, `MAX_CONCURRENT=2`, and `.claude/overview-marker-${type}` writes around lines 173 and 201. Moving assembly into Python without clearly defining where Bash regains control for atomic `mv` operations and marker updates leaves a race-prone boundary and risks silent workflow breakage.
   File: generate-overview.sh
   Fix: Constrain Python to deterministic packet construction and keep Bash responsible for concurrency control, atomic file moves, and marker writes, with an explicit file-based interface between them.

---

17. **[MEDIUM]** Absence of shared preamble assembly API
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The plan aims to eliminate duplicated preamble assembly but fails to specify a canonical API (e.g., build_preamble()) to handle constitution and goals discovery.
   File: 
   Fix: Extract shared preamble composition into a first-class module independent of packet rendering.

---

18. **[MEDIUM]** High risk in Overview live and batch migration
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The plan underestimates the complexity of overview migration (repomix, config parsing, batch JSONL distribution) by treating it as just another packet.
   File: hooks/generate-overview.sh
   Fix: Treat overview as a format-preservation migration gated by exact prompt equivalence tests.

---

19. **[MEDIUM]** Migration sequence starts with the riskiest script instead of the simplest one
   Category: architecture | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The reviewer disagrees with migrating `build_plan_close_context.py` first, arguing it is high-risk because it combines diff stat parsing, untracked file resolution, and head/tail excerpt logic. By contrast, `model-review.py` is described as a low-risk 1:1 replacement that mainly parses `file:range` specs and injects preambles, making it a better first migration target.
   File: 
   Fix: Reorder the phases so `model-review.py` migrates first, use it to validate the shared packet engine, and defer the plan-close refactor until the primitives are proven.

---

20. **[MEDIUM]** Violation of 'shared mechanics, not semantics' in context selectors
   Category: architecture | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   context_selectors.py is intended to be mechanical but is assigned responsibility for constitution/goals discovery and repomix capture, which are policy-driven semantic tasks.
   File: context_selectors.py
   Fix: Separate the selectors module into mechanical source acquisition vs. a semantic policy layer for goals and constitutions.

---

21. **[MEDIUM]** Missing scope falls back to literal "FILL ME" placeholder in plan-close context
   Category: bug | Confidence: 0.8 | Source: Gemini Pro (domain correctness)
   The review calls out that `build_plan_close_context.py` injects a literal `"FILL ME"` block when neither `scope_file` nor `scope_text` is provided, citing lines 181-185. The reviewer warns that if this behavior is migrated unchanged into a shared builder, unattended or automated runs may silently send meaningless scope text in review packets.
   File: review/scripts/build_plan_close_context.py
   Fix: Change the shared `PlanClosePacketBuilder` to fail fast when scope is required but missing, especially in unattended execution paths, instead of emitting the `"FILL ME"` placeholder.

---

22. **[MEDIUM]** Manifest sidecars should be emitted before deeper builder rewrites
   Category: missing | Confidence: 0.7 | Source: Gemini (architecture/patterns)
   Although the review supports provenance manifests, it recommends implementing `.manifest.json` sidecars in existing outputs before replacing current internals. The rationale is that predictable manifest emission would immediately expose hashes, source paths, and truncation details, lowering supervision cost during the migration rather than waiting for a full rewrite.
   File: build_plan_close_context.py
   Fix: Add `PacketManifest` JSON sidecar generation to current builders first, then refactor their content assembly onto shared packet primitives in a later step.

---

23. **[LOW]** Proposed block model ignores existing edge cases
   Category: logic | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Current behavior handles absent/deleted files and diff placeholders (e.g., 'no tracked unified diff available'). The proposed schema does not explicitly model these provenance or error states.
   File: 
   Fix: Extend the block schema to include explicit states for error markers and file provenance.

---

24. **[LOW]** Token estimation not integrated into construction artifact
   Category: performance | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The plan mentions token budgets but does not require a token estimate to be generated before dispatch as part of the shared artifact contract.
   File: 
   Fix: Define a BuildArtifact structure that includes context_path, manifest_path, and token_estimate.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

