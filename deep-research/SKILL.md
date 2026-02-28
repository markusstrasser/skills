---
name: deep-research
description: "[REDIRECTED] Use `/researcher` instead. This skill has been merged into the researcher skill, which is a strict superset with effort-adaptive tiers (quick/standard/deep), domain profiles, and better tool routing."
argument-hint: [research question or topic]
---

# Deep Research → Researcher

This skill has been merged into **`/researcher`**. The researcher skill includes everything deep-research had, plus:

- Effort-adaptive tiers (quick/standard/deep) — deep-research was always "deep" tier
- Domain-specific profiles (see `researcher/DOMAINS.md`)
- Better tool routing (selve, DuckDB, intelligence MCPs)
- Recitation-before-conclusion protocol
- Diminishing returns gate
- Corpus building workflow

**Use `/researcher` for all research tasks.** It auto-selects the appropriate tier. To force deep tier: `/researcher --deep [question]`.

$ARGUMENTS
