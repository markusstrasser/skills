<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Paper-Reading Dispatch (Research Audits)

When auditing tool implementations against source papers:

## DOI handling

- Never hardcode DOIs in prompts — they're often wrong (3/4 were wrong in the 2026-03-18 genomics audit). Tell agents to SEARCH for the paper by title/author, then verify the DOI matches.
- Tell agents: "Search for the paper first. Do not trust the DOI I provide — verify it resolves to the correct paper."

## S2 fallbacks

- Semantic Scholar (S2) API goes down periodically (403 errors). Tell agents: "If search_papers with S2 fails, retry with `backend='openalex'`. If fetch_paper fails, use exa to find the paper on PMC or the publisher site."
- All 4 agents in the 2026-03-18 session hit S2 403s but recovered via OpenAlex + PMC full text.

## Paper-reading turn budget

- Fetching a paper + reading a script + comparing + writing a report = ~6-8 tool calls minimum per tool.
- With Codex's ~15-20 turn limit, each agent can cover 2-3 tools (not 4+).
- Have agents write findings incrementally after each tool, not in one synthesis at the end.

## Output preservation

- Codex sandbox file writes can be cleaned up on agent exit. The `-o` flag output can also disappear.
- **Read output files while agents are still running** (poll with `while` loop checking file existence).
- Immediately `git add` or copy files once found. Don't wait for all agents to complete.
- If files vanish after agent completion: the content is lost. Recreate from conversation context if you read it during execution.

## What GPT-5.4 does well for paper audits

- Code-grounded comparison (reading scripts, citing file:line) — consistently accurate
- Identifying threshold mismatches between configs and paper recommendations
- Finding real bugs (missing imports, config path errors, mode drift)
- Correcting wrong DOIs and finding the right papers

## What GPT-5.4 does poorly

- Severity grading (tends to inflate)
- Claiming things are "missing" when they exist in different files
- External knowledge claims about API behavior, library features (verify these)

Codex CLI only supports OpenAI models. For Claude/Gemini dispatch, use `llmx` or Claude Code subagents. Consult `/model-guide` for task-specific routing if uncertain.
