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

These gates are **mandatory checkpoints**, not advisory. Each phase below marks where they apply.

| # | Failure | Prevention Gate |
|---|---------|-----------------|
| **F1** | Researching already-built features (~200K+ tokens wasted) | **Inventory gate**: grep `scripts/*.py` for concept keywords before ANY research |
| **F2** | Codex CLI as file-output tool (~500K tokens, 0-byte output) | **Tool gate**: use `llmx -o file.md`, never `codex -q "write to X"` |
| **F3** | Gemini Pro timeout on large context (0-byte output) | **Context gate**: summarize to <15KB for Gemini Pro; <50KB for GPT-5.4 |
| **F4** | Duplicate frontier candidates re-entering | **Idempotency gate**: maintain existing-ID ban list |
| **F5** | MCP tool-call schema mismatch (silent failures) | **Schema gate**: validate payload shape before dispatch |
| **F6** | Fixed survivor quota padding weak ideas | **Calibration gate**: default 0-2 survivors; 0 is healthy |
| **F7** | Concept duplicates under new phrasing | **Semantic dedup gate**: check concept overlap, not just IDs |
| **F8** | Long memo append corruption | **Append-at-tail gate**: inspect file tail before every append |

See `references/` for detailed gate procedures and code examples.

---

## Pipeline

### Phase 1: Inventory (~10%) -- F1, F7 gates

**Do:** Live grep of `scripts/*.py` (not codebase-map). Build concept index + existing frontier ID list. Check stage registry. Semantic overlap check on every candidate.

**Gate:** Phase 2 cannot start until inventory file exists and has been read.

See `references/phase-1-inventory.md` for grep patterns and dispatch templates.

### Phase 2: Brainstorm (~15%) -- F1, F4 gates

**Do:** Invoke `/brainstorm` with full inventory + existing IDs as negative context. Use perturbation axes (denial cascade, domain forcing, constraint inversion).

**Output:** Disposition table: EXPLORE / PARK / REJECT for every idea.

See `references/phase-2-brainstorm.md` for prompt template and axis details.

### Phase 3: Research (~25%) -- F1, F2, F3, F4, F5, F6 gates

**Do:** Parallel research agents on EXPLORE ideas. Pre-dispatch checklist is MANDATORY per idea.

**Key judgments:**
- Up to 3 Claude agents + 2 llmx GPT-5.4 in parallel. One idea per agent.
- Survivor calibration: default 0-2. A 0-survivor pass is healthy -- log it, don't pad.
- Post-research: check file sizes (`wc -c`), cross-check against inventory, recover transcripts for <200 byte outputs.

See `references/phase-3-research.md` for checklists, tool schema guardrails, and dispatch patterns.

### Phase 4: Plan (~15%)

**Do:** Structured plan with tiers, evidence grades, falsification criteria, caller identification.

**Key judgments:**
- Every object must have a caller -- dead code with a plan does not pass.
- Classify each as: new primitive / limiter on existing / follow-up qualifier / reject-merge.
- LOC estimates must be realistic, dependencies explicit.

See `references/phase-4-plan.md` for plan template and quality gates checklist.

### Phase 5: Model Review (~15%) -- F3 gate

**Do:** `/model-review` on the plan. Match review depth to blast radius (1-2 additions = simple, 6+ = deep).

**Key judgments:**
- Summarize to <15KB before Gemini Pro dispatch. Use `--extract` when possible.
- Each finding: ACCEPT / REJECT (with reason) / NOTE.

See `references/phase-5-review.md` for depth table, transport notes, and integration steps.

### Phase 6: Implement (~20%)

**Do:** Execute amended plan. Up to 5 parallel agents for independent scripts.

**Key judgments:**
- Status truthfulness: `implemented` vs `locally verified` vs `runtime-pending`. Never write "completed" with pending remote steps.
- Multi-agent safety: commit after each script, or use `isolation: "worktree"`.
- Post-agent: `ruff check` all new files, one commit per script.
- CYCLE.md write-back if it exists (prevents research-cycle re-discovery).

See `references/phase-6-implement.md` for agent prompt requirements, commit patterns, and cleanup steps.

---

## Anti-Patterns

| Anti-Pattern | Do This Instead |
|-------------|-----------------|
| Skip inventory, brainstorm first | Always Phase 1 first |
| Use codebase-map as ground truth | Live grep on scripts/*.py |
| Codex CLI for file output | `llmx -o file.md` |
| >15KB context to Gemini Pro | Summarize or use `--extract` |
| One mega-agent for all ideas | One narrow agent per idea |
| Implement before model review | Review catches 30-50% of issues |
| Batch-commit all scripts | One commit per script |
| Skip ruff after agent code | Always ruff check new files |
| Reuse old frontier IDs | Maintain ban list, allocate fresh series |
| Schema-mismatched MCP payloads | Validate parameter types before dispatch |

## Operational Discipline

See `references/operational-discipline.md` for running memo rules, cross-repo git safety, and effort budget breakdown (~1.5M tokens total for 6-8 analysis expansion).

## Customization Points

- **Brainstorm axes:** Override with `--axes denial,domain` or `--domains "jazz, geology"`
- **Research depth:** `--quick` skips Tier 3 research entirely
- **Review depth:** Match to blast radius (see Phase 5)
- **Implementation:** Can stop after plan (Phase 4) if user wants to implement later
