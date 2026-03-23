---
name: entity-management
description: Versioned knowledge management for entities (people, companies, genes, drugs, stocks). Use when the user wants to profile, track, build a dossier on, or save structured notes about a specific entity. One file per entity, git-versioned, every claim sourced.
user-invocable: true
argument-hint: [entity name — person, company, gene, drug, stock]
effort: medium
---

# Entity Management

Track knowledge about individual entities with full provenance. Every edit is a git commit so you can see reasoning evolution, belief updates, and corrections over time.

## File Structure

```
docs/entities/
├── companies/      # Companies under investigation or research (primary)
├── people/         # Named individuals — officers, insiders, analysts
├── contracts/      # Key contracts, agreements, JVs
├── filings/        # SEC filings, court records, regulatory submissions
├── genes/          # Individual genes (g6pd.md, ebf3.md)
├── drugs/          # Medications, supplements
├── self/           # User's own profile, cognitive traits
└── <category>/     # Any domain-specific category
```

One file per entity at `docs/entities/<category>/<entity-name>.md`.

## Provenance Rules

Every claim must cite a ground-truth source or explicit derivation chain:

### Primary Sources (highest reliability)
- Paper DOIs, PMIDs
- Database IDs: ClinVar, gnomAD, OMIM, PharmGKB
- Official URLs: FDA labels, CPIC guidelines, SEC filings
- API responses: with timestamp and query parameters
- Court records, government reports

### Derived Claims
State the inputs + transformation:
> "PRS percentile computed from `prs_results.tsv` using EUR reference panel"

### Inferred Claims
Explicitly mark as `[INFERRED]` with reasoning chain:
> "[INFERRED] Likely reduced enzyme activity based on MAVE score 0.023 + structural homology to known loss-of-function variants"

### Unverified Claims
Mark as `[UNVERIFIED]` with the source of the claim:
> "[UNVERIFIED] Reported in a blog post but no primary source found"

### Corrected Claims
When updating a previous claim, mark as `[CORRECTED]`:
> "[CORRECTED] Previously stated OR=2.3; actual OR=1.3 per gnomAD v4.1"

## Cross-References (Zettelkasten Pattern)

Entity files should link to related entities. When a gene is a drug target, the gene file links to the drug file and vice versa. When a person is an officer of a company, both files cross-reference.

Format: `→ see [entity-name](../category/entity-name.md)` in the relevant Key Facts row.

This enables traversal: starting from one entity, you can follow links to build a complete picture without relying on search. Based on A-MEM's Zettelkasten-inspired memory architecture (ICLR 2026, arXiv:2502.12110) — structured connections between memories improve retrieval over flat storage.

## Staleness Detection

Every claim in the Key Facts table has a `Date Verified` column. Claims older than 6 months should be flagged for re-verification when the entity file is loaded:

> **STALE:** [N] claims last verified >6 months ago. Re-verify before relying on them.

This is especially critical for: stock prices, company officers, clinical trial status, drug approval status, regulatory filings.

## Progressive Disclosure Within Entity Files

When an entity file exceeds ~200 lines, add a `## Summary` section at the top (after the one-liner) containing ONLY the Key Facts table. This lets agents load the summary without reading the full narrative — reducing context cost when the entity is referenced but not the focus.

## Never Do This

- State conclusions without provenance
- Use "I read it somewhere" or "an AI said it" as a source — find the primary reference or mark `[UNVERIFIED]`
- Copy claims from one entity file to another without re-verifying
- Delete incorrect claims — correct them with `[CORRECTED]` so the git history shows the evolution

## Template

```markdown
# Entity Name

> One-line description. Category: <type>.

## Key Facts

| Fact | Source | Date Verified |
|------|--------|---------------|
| ... | DOI/URL/database ID | YYYY-MM-DD |

## Narrative Summary

[Sourced prose. Every paragraph ends with citations.]

## Open Questions

- [What's unresolved]
- [What would change the assessment]

## Changelog

- YYYY-MM-DD: Created with initial findings from [source]
- YYYY-MM-DD: [CORRECTED] claim X based on [new source]
```

## Conviction Journal (Investment Entities)

For entities with investment conviction tracking (tickers with `conviction_journal` in frontmatter):

- Every conviction change requires a journal entry in YAML frontmatter
- Schema and vocabulary defined in project-local `.claude/rules/conviction-schema.md`
- Never silently change the `conviction:` frontmatter field — the journal entry IS the change
- KL divergence: `sum(p_i * ln(p_i / q_i))`, use 0.001 floor for zero probabilities
- Evidence field must be a real file path or URL with `[source grade]`

## Git Conventions

- Every edit is a separate commit
- Commit message format: `entities/<category>/<name>: <what changed>`
- Example: `entities/genes/g6pd: correct enzyme activity from MAVE data`
- Don't batch entity updates with unrelated changes

## When to Create an Entity File

Create one when:
- Knowledge will accumulate over multiple sessions
- Multiple sources contribute to understanding the entity
- Corrections or belief updates are likely
- The entity appears in multiple contexts (research memos, protocols, analyses)

Don't create one for:
- Entities mentioned once in passing
- Entities fully described in a single research memo
- Generic categories (create a research memo instead)
