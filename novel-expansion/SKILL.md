---
name: novel-expansion
description: End-to-end pipeline for discovering and implementing genuinely novel analyses in a codebase. Inventory → Brainstorm → Research → Plan → Review → Implement. Encodes hard-won anti-patterns from the first run.
effort: high
---

# Novel Expansion — Discovery-to-Implementation Pipeline

Systematically discover what's missing from a codebase, validate feasibility, and implement. Six phases, each with explicit gates to prevent known failure modes observed in the inaugural run.

## When to use

"What's missing?", "novel analyses", "expand the pipeline", "brainstorm and build", or any request to discover AND implement genuinely new capabilities beyond what exists.

**Not for:** Adding a specific known feature (just build it), fixing bugs (use dispatch-research), or pure ideation without implementation (use /brainstorm directly).

## Failure Modes (hard-won)

| # | Failure | Cost | Prevention Gate |
|---|---------|------|-----------------|
| **F1** | Researching already-built features | ~200K+ tokens, 2 wasted agents | **Inventory gate**: grep `scripts/*.py` for concept keywords before dispatching ANY research agent |
| **F2** | Codex CLI as file-output tool | ~500K tokens, 4 zero-output agents | **Tool gate**: use `llmx -p openai -m gpt-5.4 -o file.md` for research file output, never `codex -q --full-auto "write to X"` |
| **F3** | Gemini Pro timeout on large context | ~50K tokens, 0-byte output | **Context gate**: summarize to <15KB for Gemini Pro; GPT-5.4 handles up to 100K but prefers <50K |
| **F4** | Duplicate frontier candidates re-entering as “new” | Repeated passes with no value gain | **Idempotency gate**: keep and enforce an existing-ID ban list before every brainstorm/research batch |
| **F5** | MCP tool-call schema mismatch | Silent evidence-call failures (e.g., wrong parameter shape) | **Schema gate**: validate each MCP request payload shape before dispatch |
| **F6** | Fixed survivor quota ("3 survivors" pattern) | Artificially smooth frontier yield; padded weak ideas | **Calibration gate**: default to 0-2 survivors; explicit no-survivor passes are healthy |
| **F7** | Concept duplicates without ID duplicates | Same idea re-enters under new phrasing | **Semantic dedup gate**: check concept overlap against memo/master plan, not just IDs |
| **F8** | Long memo append corruption | Misordered or overwritten running memo sections | **Append-at-tail gate**: inspect actual file tail before every append; never trust pass-number order alone |

These gates are **mandatory checkpoints**, not advisory. Each phase below marks where they apply.

---

## Phase 1: Inventory (~10% of effort)

**Goal:** Know exactly what exists before imagining what's missing.

### 1a. Codebase grep (NOT codebase-map)

Codebase maps go stale within days. Do a live inventory:

```bash
# Count scripts and their domains
ls scripts/*.py | wc -l
# Extract one-line descriptions from docstrings
for f in scripts/*.py; do head -5 "$f" | grep -o '"[^"]*"' | head -1; done
```

Or dispatch an Explore agent with `isolation: "worktree"`:
```
"Inventory all scripts in scripts/*.py. For each, extract: filename, docstring first line,
key imports, output paths. Write to /tmp/pipeline_inventory.md"
```

### 1b. Concept keyword grep (**F1 gate**)

Before brainstorming, build a concept index from actual code:

```bash
# What biological concepts are already implemented?
grep -l "haplotype\|phasing\|ancestry" scripts/*.py
grep -l "peptide\|MHC\|neoantigen\|immune" scripts/*.py
grep -l "telomere\|TVR\|hexamer" scripts/*.py
grep -l "G4\|quadruplex\|palindrome\|mechanome" scripts/*.py
grep -l "STR\|repeat\|expansion\|interruption" scripts/*.py

# Track existing frontier IDs already claimed in this stream
{
  [[ -f .claude/plans/novel-expansion-master-2026-03-26.md ]] && rg -o "(BR|NB|NC|ND|NE)-[0-9]+" .claude/plans/novel-expansion-master-2026-03-26.md
  [[ -f docs/research/novel_expansion_running_2026-04-03.md ]] && rg -o "(BR|NB|NC|ND|NE)-[0-9]+" docs/research/novel_expansion_running_2026-04-03.md
} | sort -V | uniq > /tmp/novel_expansion_existing_ids.txt

wc -l /tmp/novel_expansion_existing_ids.txt
```

Save as `$BRAINSTORM_DIR/existing_concepts.txt`. Keep the ID list at `/tmp/novel_expansion_existing_ids.txt`.
Both are **mandatory context** for Phase 2.

### 1d. Semantic overlap check (**F7 gate**)

Before promoting any candidate, ask:

- Is this actually new, or a sharper restatement of an existing row?
- Is it a new primitive, or just a limiter on an existing operator?
- Does it have a likely caller in this repo?

If it fails those checks, reject or merge it. Do not assign a new frontier ID just because the wording is different.

### 1c. Stage registry check

```python
from pipeline_stages import STAGES
print(f"{len(STAGES)} stages registered")
```

Or equivalent for the project's stage/task registry.

**Gate:** Phase 2 cannot start until the inventory file exists and has been read.

---

## Phase 2: Brainstorm (~15% of effort)

Invoke `/brainstorm` with the full inventory as context.

**Critical:** Include the existing_concepts.txt in the brainstorm prompt:

```
"The following features ALREADY EXIST — do not propose them:
[paste existing_concepts.txt or inventory summary]
Existing frontier IDs already used (do not reuse):
/tmp/novel_expansion_existing_ids.txt

What's genuinely MISSING that would add new biological/analytical insight?"
```

Use the brainstorm skill's perturbation axes:
- **Denial cascade:** forbid the dominant paradigms from initial generation
- **Domain forcing:** pick 3 distant domains (insurance, materials science, ATC)
- **Constraint inversion:** "what if we had family data?", "what if compute were free?"

**Output:** Disposition table with EXPLORE/PARK/REJECT for every extracted idea.

---

## Phase 3: Research (~25% of effort)

Dispatch parallel research agents on EXPLORE ideas. This is where F1, F2, and F3 hit hardest, with F4/F5 as common secondary failures.

### Pre-dispatch checklist (MANDATORY)

For EACH idea being researched:

- [ ] **F1 gate:** `grep -l "keyword1\|keyword2" scripts/*.py` returns 0 matches for this concept
- [ ] **F1 gate:** Checked `existing_concepts.txt` — concept not listed
- [ ] **F4 gate:** Checked `/tmp/novel_expansion_existing_ids.txt` for duplicate IDs
- [ ] Agent prompt includes specific output file path
- [ ] Agent prompt includes: "Write findings to {file} INCREMENTALLY. After every 3 searches, append."
- [ ] Scope is narrow enough for 8 search calls per agent (per subagent-output-discipline rule)

### Tool schema guardrails (**F5 gate**)

- `mcp__scite__search_literature`:
  - `title` is a scalar string per call.
  - Pass multiple titles as repeated calls, not one array payload.
- `mcp__brave_search__brave_news_search`, `mcp__brave_search__brave_web_search`:
  - Keep query focused; open/crawl on selected URLs for source details.
- `perplexity` calls:
  - Set `search_context_size` explicitly and use recent `search_recency_filter` only when needed.

### Research dispatch patterns

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

**NEVER use (**F2 gate**):**
```bash
# BROKEN — codex CLI cannot write to specified files from prompt instructions
codex -q --full-auto "Research X. Write to research-X.md"  # → 0 bytes every time
# See also: dispatch-research skill (same fix, prompt template rewritten 2026-03-26)
```

### Parallel dispatch strategy

- Up to 3 Claude researcher agents in parallel (more causes MCP contention)
- Up to 2 llmx GPT-5.4 calls in parallel
- Each agent covers ONE idea (not "research all 5 ideas")

### Post-research verification

After agents complete:
1. Check output file sizes: `wc -c $RESEARCH_DIR/*.md`
2. Any file < 200 bytes → transcript recovery (read agent task output)
3. Cross-check: did any agent "discover" something from existing_concepts.txt? → discard

### Survivor calibration (**F6 gate**)

Do **not** target a fixed survivor count.

- Default expectation for mature frontiers: **0-2 survivors**
- **1 strong survivor** is a good pass
- **0 survivors** is acceptable and should be logged explicitly
- A pass with 3+ survivors should be treated as unusual and justified, not assumed

If the search is producing reframings, caveats with no caller, or operator duplicates, stop and log a no-survivor pass instead of padding.

---

## Phase 4: Plan (~15% of effort)

Write a structured implementation plan. Use `/plan` or write directly to `.claude/plans/`.

### Plan structure

```markdown
# {Title} — Implementation Plan

**Session:** {date} | **Project:** {name}
**Origin:** Inventory ({N} scripts) → Brainstorm ({N} ideas, {axes}) → Research ({N} agents)

## Executive Summary
- Tier 1 (build now): N analyses, ~N LOC
- Tier 2 (build with new tools): N analyses, ~N LOC
- Tier 3 (research first): N analyses, 0 LOC

## Tier 1 — {each analysis with: source, effort, evidence grade, implementation steps, validation, dependencies}
## Tier 2 — {same}
## Tier 3 — {research needed before building}

## Implementation Order
## QA Integration (per-analysis: @stage, validate(), canary impact)
## Constitutional Alignment (per-principle assessment)
## Falsification Criteria (per-analysis: what would disprove this)
```

### Plan quality gates

- [ ] Every analysis has an evidence grade (B3, E5, research_only, etc.)
- [ ] Every analysis has falsification criteria
- [ ] No analysis overlaps with existing_concepts.txt entries
- [ ] LOC estimates are realistic (not just "~50 LOC" for everything)
- [ ] Dependencies are explicit (databases to download, libraries to install)
- [ ] Each proposed object has a caller; "dead code with a plan" does not pass
- [ ] Each proposed object is classified as one of:
  - new primitive
  - limiter on an existing primitive
  - follow-up qualifier
  - reject/merge

---

## Phase 5: Model Review (~15% of effort)

Invoke `/model-review` on the plan. Depth depends on blast radius:

| Plan scope | Review depth | Axes |
|-----------|-------------|------|
| 1-2 simple additions | `--axes simple` | 1 query (Gemini Pro combined) |
| 3-5 new analyses | `--axes arch,formal` | 2 queries (standard) |
| 6+ analyses or domain-dense | `--axes deep` | 4 queries (arch + formal + domain + mechanical) |
| Shared infrastructure changes | `--axes full` | 5 queries |

### Context size gate (**F3 gate**)

Before dispatching:

```bash
wc -c context.md
# If > 15KB: summarize before sending to Gemini Pro
# If > 50KB: summarize before sending to GPT-5.4
# The model-review.py script handles this automatically with --extract
```

## Running Memo Discipline

For long-running novelty sweeps:

1. Read the actual tail of the running memo before appending.
2. Append at the tail even if prior pass numbers are out of order.
3. Never rewrite old passes just to normalize numbering or survivor counts.
4. Commit the memo periodically; it is the mission-critical artifact.

If the memo gets numerically messy, preserve append-only history and fix the process forward rather than rewriting the past.

## Cross-Repo Git Safety

Novelty sessions often touch sibling repos (shared skills, meta docs, related projects).

Before any `git diff`, `git status`, or `git commit` on edited files:

1. detect the owning git root for those files
2. switch to that repo before running git commands
3. treat "outside repository" as a routing failure, not a git problem

Do not stage or commit cross-repo edits from the wrong cwd just because the absolute path is visible.

**Why 15KB for Gemini:** model-review.py dispatches Gemini via CLI transport (free tier,
`--timeout 300`, no `--stream`, no `--max-tokens`). CLI transport can handle 1M context
in theory but thinking models timeout at ~15KB within the 300s window. The script falls
back to Flash on failure, but Flash is shallow — you lose deep review. Summarize instead.

**To force API transport** (paid, handles larger context): add `--stream` to the axis flags
in model-review.py. But this costs money — prefer summarizing to <15KB.

**Preferred:** Use `model-review.py --extract` (auto-extracts claims cross-family).

### Review integration

After review completes:
1. Read all outputs (formal, domain, mechanical, arch)
2. For each finding: ACCEPT (amend plan), REJECT (with reason), or NOTE (track but don't change)
3. Update the plan with a "## Model Review Amendments" section at top
4. Adjust tiers based on review (things may get demoted)

---

## Phase 6: Implement (~20% of effort)

Execute the amended plan. Key efficiency patterns:

### Parallel agent dispatch for independent scripts

If the plan has N independent new scripts, dispatch up to 5 agents in parallel:

```
Agent(name="script-a", mode="bypassPermissions", prompt="Write script at {path}. [full spec]...")
Agent(name="script-b", mode="bypassPermissions", prompt="Write script at {path}. [full spec]...")
```

Each agent prompt MUST include:
1. Full import pattern from the project (`from variant_evidence_core import ...`)
2. Output path convention (`data/wgs/analysis/{stage}/`)
3. JSON output structure
4. `validate()` function spec
5. "Do NOT commit — I will commit after review"

### Multi-agent commit safety

Check `OTHER ACTIVE AGENTS` in session context. If other sessions are running:
- Commit after EACH script (not in a batch) — parallel agents may sweep uncommitted edits
- Or use `isolation: "worktree"` on implementation agents to avoid conflicts
- Run `git status` before each commit to verify only your files are staged

(Source: dispatch-research skill update 2026-03-26 — parallel agent commit race condition)

### Post-agent cleanup

After agents complete:
1. `ruff check --select F821,F401,F841,E741` on all new files
2. Fix any Pyright errors (agents often miss type issues on `max()`, conditional imports)
3. Commit each script separately with semantic messages
4. Register stages in the stage registry
5. Run canary/regression gate

### Commit pattern

```
[scope] Wire {analysis name} — {what it does}

{1-3 line body: key design choice, smoke test result}
```

One commit per script. Final commit for stage registration + codebase map update.

### Execution status truthfulness

Do not collapse build state into a single word.

- `implemented`: files, wiring, and registrations exist locally
- `locally verified`: imports/tests/CLI checks passed on the local machine
- `runtime-pending`: detached Modal jobs, benchmarks, or full reruns have not completed

If any runtime-critical remote step is still pending, do not write `executed` or `completed`
in `CYCLE.md`, plans, or status summaries. Spell out what ran and what did not run yet.

### CYCLE.md Write-Back

If `CYCLE.md` exists in the project root, append completed items to `## Completed This Session` so `/research-cycle` doesn't re-discover them:
```
- **{name}** ({commit}) — {one-line description}
```
One line per implemented analysis. This coordinates the growth lane — novel-expansion is a deep batch run, research-cycle is incremental. Without write-back, research-cycle's discover phase may re-propose work that was just built.
If work is only implementation-complete, log it as implemented plus runtime-pending detail rather than as fully executed.

---

## Effort Budget

| Phase | % of session | Tokens (typical) | Parallelizable? |
|-------|-------------|-------------------|-----------------|
| Inventory | 10% | ~20K | No |
| Brainstorm | 15% | ~200K (with llmx dispatch) | Partially (llmx calls) |
| Research | 25% | ~500K (across agents) | Yes (up to 5 agents) |
| Plan | 15% | ~30K | No |
| Review | 15% | ~300K (cross-model) | Yes (models run in parallel) |
| Implement | 20% | ~400K (agent dispatch) | Yes (up to 5 agents) |

**Total:** ~1.5M tokens for a 6-8 analysis expansion. The inventory and concept grep (~20K tokens) saves ~200K+ in wasted research.

---

## Anti-Patterns

| Anti-Pattern | What Happens | Do This Instead |
|-------------|-------------|-----------------|
| Skip inventory, go straight to brainstorm | Propose 3+ already-built features | Always Phase 1 first |
| Use codebase-map as ground truth | Miss 5+ recently added scripts | Live grep on scripts/*.py |
| Dispatch codex CLI for file output | 0-byte output files | Use `llmx -p openai -o file.md` |
| Send >15KB context to Gemini Pro | Timeout, 0-byte output | Summarize or use model-review.py |
| One mega-agent for "research all ideas" | Exhausts turns, 0 synthesis | One narrow agent per idea |
| Implement before model review | Build wrong things | Review catches 30-50% of issues |
| Commit all scripts in one commit | Hard to revert individual changes | One commit per script |
| Skip ruff after agent writes code | F821 undefined names ship | Always ruff check new files |
| Reuse an old frontier ID prefix/number | Memos collide, review loses lineage | Keep `/tmp/novel_expansion_existing_ids.txt` and allocate a fresh series ID |
| Pass a scite title array or other schema-mismatched payload | Failed evidence calls with no obvious error | Validate parameter types per tool before dispatch |

## Customization Points

- **Brainstorm axes:** Override with `--axes denial,domain` or `--domains "jazz, geology"`
- **Research depth:** `--quick` skips Tier 3 research entirely
- **Review depth:** Match to blast radius (see table above)
- **Implementation:** Can stop after plan (Phase 4) if user wants to implement later
