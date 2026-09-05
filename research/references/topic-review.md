# Topic Review — Standard and Deep

Use this for a topic review, comparison, literature review, or broad investigation. A single factual lookup can finish at a verified source without this workflow.

## Ground the question

Check relevant local context before repeating a full research pass: recent memos and git history, curated entity pages, project data, or the saved paper corpus. Use `rg` for exact searches and the configured knowledge tools for semantic retrieval. Read a recent answer first, then research the unresolved gap or changed facts.

Curated entity pages and sourced memos are useful starting points; trace decision-critical claims to their primary evidence and verify currency. They do not automatically outrank a newer official record or raw source. For reviews of agent behavior, raw transcripts remain the principal evidence.

If the question concerns a product or application, identify its governing discipline and category conventions as well as the named people or tools. The named entities are a subset of the question's domain.

## Search in rounds

Choose independent perspectives that could change the answer. Mechanism, failure/criticism, adjacent domains, history, practitioner experience, academic literature, and population outcomes are useful options. Two differently worded queries from one perspective are still one axis. Use the perspectives relevant to the question rather than filling every category.

Start broad enough to discover the field's vocabulary, then narrow from the results. Exa is semantic: describe the concept; `additionalQueries` can cover distinct framings when the current schema supports it. Read promising sources before launching the next search round. Do not keep broad recency searches running after one useful seam emerges.

Choose dates by what can change in the domain; verify dates in the returned source. Fast-moving tools may need a recent release check. Historical foundations may remain relevant. An official policy or legal source still needs a currency check even when the subject is old.

For academic claims, follow [paper evidence checks](paper-evidence.md). A saved paper or search snippet does not establish what its methods and results say. Use [tool routing](tool-routing.md) when a tool choice or retrieval failure needs resolution.

## Test the emerging answer

For evaluative conclusions, articulate the claim and what would contradict it. Search for failures, null results, limitations, and alternative explanations. Check whether results come from one lab or independent groups; check population and endpoint transfer. If a serious search found no contradiction, say "no contradictory evidence found," not "none exists."

Claims about literature consensus need a citation-stance check when scite is available, plus inspection of the relevant supporting and contrasting papers. Report `[SCITE: NO COVERAGE]` for zero coverage; if the tool is unavailable, say so and inspect later citations, replications, and reviews directly. Neither a coverage gap nor a stance count establishes consensus.

## Synthesize when the evidence resolves the question

After each round, assess what changed and which unresolved issue would alter the conclusion. Continue for a consequential gap or new contradiction. Synthesize when new results repeat existing material or broaden the topic without resolving it. Respect the user's budget; reserve time for a useful write-up instead of exhausting the session on search quotas.

Before concluding, compare the actual evidence items: result, sample/population, method, uncertainty, and source quality. Derive the conclusion from that comparison. Agreement between sources that share an upstream source is not independent confirmation.

Organize the answer around findings and uncertainties. Use [memo-output.md](memo-output.md) if a durable artifact would help or the user requested one. If evidence is insufficient, report the question, sources searched, missing evidence, and the partial findings that remain defensible.

## Deep additions

Deep research needs enough distinct approaches to cover the question and an explicit disconfirmation pass. Analogies to another domain can open a missing literature; use them when they expose a concrete mechanism rather than merely changing vocabulary.

Keep a search log (queries, tools, dates, useful hits and misses) and a verification log separating directly checked claims from inference or unverified leads. Record access limitations and important unanswered questions. These logs support reproducibility; they need not dominate the user-facing prose.

Persist an actionable research plan in the project's `.claude/plans/` or `docs/` before a handoff. A research-only request ends with findings and a concrete recommendation; work already authorized by the user can continue within that scope.
