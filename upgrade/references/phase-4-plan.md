<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Phase 4: Plan (~15% of effort)

Write a structured implementation plan. Use `/plan` or write directly to `.claude/plans/`.

## Plan structure

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

## Plan quality gates

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
