<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Phase 3: Research (~25% of effort)

Dispatch parallel research agents on EXPLORE ideas. This is where F1, F2, and F3 hit hardest, with F4/F5 as common secondary failures.

## Pre-dispatch checklist (MANDATORY)

For EACH idea being researched:

- [ ] **F1 gate:** `grep -l "keyword1\|keyword2" scripts/*.py` returns 0 matches for this concept
- [ ] **F1 gate:** Checked `existing_concepts.txt` — concept not listed
- [ ] **F4 gate:** Checked `/tmp/novel_expansion_existing_ids.txt` for duplicate IDs
- [ ] Agent prompt includes specific output file path
- [ ] Agent prompt includes: "Write findings to {file} INCREMENTALLY. After every 3 searches, append."
- [ ] Scope is narrow enough for 8 search calls per agent (per subagent-output-discipline rule)

## Tool schema guardrails (F5 gate)

- `mcp__scite__search_literature`:
  - `title` is a scalar string per call.
  - Pass multiple titles as repeated calls, not one array payload.
- `mcp__brave_search__brave_news_search`, `mcp__brave_search__brave_web_search`:
  - Keep query focused; open/crawl on selected URLs for source details.
- `perplexity` calls:
  - Set `search_context_size` explicitly and use recent `search_recency_filter` only when needed.

## Research dispatch patterns

**For paper reading / tool evaluation:**
```bash
# CORRECT — llmx with file output
llmx -p openai -m gpt-5.4 --reasoning-effort high --stream --timeout 600 \
  -o "$RESEARCH_DIR/research-{topic}.md" \
  "Research {specific question}. Find: (1) existing tools, (2) feasibility at 30x short-read,
   (3) key papers with DOIs. Stop at 70% of your reasoning budget and synthesize."
```

**For codebase analysis:**
```
Agent(subagent_type="researcher", prompt="...", name="research-{topic}")
```
with the file-first incremental output rule.

**Codex CLI — correct pattern (if using dispatch-research):**
```bash
# CORRECT — Codex text output captured via -o, NOT by telling the agent to write files
codex exec --full-auto -o "$RESEARCH_DIR/research-{topic}.md" "Research X. Do NOT create files."
```

**NEVER use (F2 gate):**
```bash
# BROKEN — codex CLI cannot write to specified files from prompt instructions
codex -q --full-auto "Research X. Write to research-X.md"  # → 0 bytes every time
# See also: dispatch-research skill (same fix, prompt template rewritten 2026-03-26)
```

## Parallel dispatch strategy

- Up to 3 Claude researcher agents in parallel (more causes MCP contention)
- Up to 2 llmx GPT-5.4 calls in parallel
- Each agent covers ONE idea (not "research all 5 ideas")

## Post-research verification

After agents complete:
1. Check output file sizes: `wc -c $RESEARCH_DIR/*.md`
2. Any file < 200 bytes → transcript recovery (read agent task output)
3. Cross-check: did any agent "discover" something from existing_concepts.txt? → discard

## Survivor calibration (F6 gate)

Do **not** target a fixed survivor count.

- Default expectation for mature frontiers: **0-2 survivors**
- **1 strong survivor** is a good pass
- **0 survivors** is acceptable and should be logged explicitly
- A pass with 3+ survivors should be treated as unusual and justified, not assumed

If the search is producing reframings, caveats with no caller, or operator duplicates, stop and log a no-survivor pass instead of padding.
