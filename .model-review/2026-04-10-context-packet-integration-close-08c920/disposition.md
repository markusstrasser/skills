# Review Findings — 2026-04-10

**11 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** "Oldest marker" selection logic is incorrectly implemented
   Category: bug | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   The comment in `hooks/sessionend-overview-trigger.sh` states it should use the oldest per-type marker as a diff baseline, but the code actually selects the first marker found in the configured types order and breaks immediately. This is an ordering property failure.
   File: hooks/sessionend-overview-trigger.sh
   Fix: Remove the 'break' statement and iterate through all markers to compare mtimes, selecting the one with the earliest timestamp.

---

2. **[HIGH]** Staleness check logic is broken for multi-type projects
   Category: logic | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   In `hooks/overview-staleness-cron.sh`, the script picks the first existing marker file it finds and computes age from only that file. If the first marker is fresh but subsequent configured types are stale, the stale types will never be regenerated.
   File: hooks/overview-staleness-cron.sh
   Fix: Evaluate staleness for every configured type in the loop rather than exiting after the first found marker, or aggregate the staleness state across all markers.

---

3. **[HIGH]** Golden fixture test for plan-close context was not implemented
   Category: missing | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review says the migration plan explicitly required "golden fixture tests for plan-close packets" to catch silent drift, but no corresponding test was added. It specifically calls out that `test_build_plan_close_context.py` does not exist and that there are no added or modified tests covering `build_plan_close_context.py`. This leaves formatting, ordering, and truncation behavior unverified after the shell-to-Python migration.
   File: review/scripts/test_build_plan_close_context.py
   Fix: Add a golden-fixture test for `build_plan_close_context.py` using a static/mock git fixture and exact string assertions against a checked-in expected packet output.

---

4. **[HIGH]** `generate_overview.py` mutates the historical prompt by appending `trailing_text`
   Category: logic | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review flags that `generate_overview.py` injects a `trailing_text` instruction — `"Write the requested codebase overview in markdown."` — into the prompt. It states this changes the legacy prompt shape and breaks the required prompt/payload equivalence guarantees, with no prompt-equivalence or payload-hash regression test to document the change. The same issue is reiterated as both "Contract Drift (Prompt Shape)" and "Silent Prompt Mutation."
   File: scripts/generate_overview.py
   Fix: Remove the extra `trailing_text` from overview packets to preserve backward-compatible prompt shape, or add an explicit equivalence/regression test if the prompt contract is intentionally changing.

---

5. **[HIGH]** Overview generation no longer prepends the historical provenance header
   Category: bug | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review notes that the previous shell implementation prepended a metadata comment like `<!-- Generated: ${gen_ts} | git: ${git_sha} | model: ${OVERVIEW_MODEL} -->`, but the new Python path writes the LLM output verbatim via `distribute_results` / `r.get("content", "")`. That means generated markdown permanently loses generation timestamp, git SHA, and model provenance that existed in historical outputs.
   File: scripts/generate_overview.py
   Fix: Prepend the historical HTML comment before writing overview markdown, e.g. generate UTC timestamp, current git SHA, and profile/model name, then write the header followed by the model output.

---

6. **[MEDIUM]** Overview batch orchestration is brittle because it shells out and scrapes stdout for the job ID
   Category: architecture | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review calls out that `generate_overview.py` uses `subprocess.run(batch_submit_command(...))` and then parses stdout lines such as `line.startswith("Submitted:")` to recover the batch job ID. This is fragile compared with using native Python bindings, because CLI output format changes can break job submission or tracking without type-checked API guarantees.
   File: scripts/generate_overview.py
   Fix: Replace CLI shell-out submission with the native `llmx` Python client/API and consume the returned batch/job object directly instead of parsing stdout text.

---

7. **[MEDIUM]** Overview configuration contract is duplicated across multiple parsers
   Category: architecture | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The logic for parsing `.claude/overview.conf` exists in three places: `shared.overview_config`, shell-based `grep/cut/xargs` in cron hooks, and an inline parser in the trigger hook. This creates a high risk of contract drift.
   File: hooks/overview-staleness-cron.sh
   Fix: Centralize all configuration reading and marker path resolution into a single shared Python utility and invoke it from the shell hooks.

---

8. **[MEDIUM]** Plan-close budget metadata under-reports actual packet size
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The `BudgetPolicy` limit (e.g., 40k chars) is attached to the packet but only describes the diff component. The total packet size includes file excerpts (up to 96k additional chars) and metadata, making the reported budget significantly smaller than the actual payload.
   File: review/scripts/build_plan_close_context.py
   Fix: Update the manifest to report total packet size or clarify that the budget policy applies specifically to the diff component only.

---

9. **[MEDIUM]** Lack of verification for migration success criteria
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The project claims 'implemented' status, but there are no shown tests enforcing live-vs-batch payload hash equivalence, marker semantics correctness, or plan-close golden output consistency.
   File: scripts/test_generate_overview.py
   Fix: Implement regression tests that assert byte-for-byte equality between live and batch rendering paths and validate marker selection logic.

---

10. **[MEDIUM]** Overview renderer may drift prompt tag casing/formatting from the legacy shell prompt
   Category: logic | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review highlights a potential compatibility problem: the old bash prompt used lowercase tags like `<instructions>` and `<codebase>`, while `generate_overview.py` now builds `PacketSection("Instructions", ... tag="instructions")` and depends on the `tagged` renderer to emit exactly the legacy shape. If the renderer uses title-cased section names, ignores `tag`, or adds formatting differences, the prompt signature changes even though the content source is similar.
   File: scripts/generate_overview.py
   Fix: Add a prompt-shape regression test that snapshots the fully rendered overview prompt and verifies exact tag names/formatting, or hardcode renderer behavior to match the historical shell output exactly.

---

11. **[LOW]** Project enumeration is hardcoded in multiple locations
   Category: style | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   Repo lists are hardcoded in both `scripts/generate_overview.py` and `hooks/overview-staleness-cron.sh`. Adding a new repository requires manual code edits in multiple files, which is not scalable.
   File: scripts/generate_overview.py
   Fix: Replace hardcoded lists with an automatic discovery mechanism that searches for directories containing `.claude/overview.conf`.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

