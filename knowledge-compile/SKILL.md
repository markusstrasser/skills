---
name: knowledge-compile
description: Synthesize multiple research memos and entity files about a concept into a unified article with per-claim provenance, contradiction surfacing, and gap identification. Cross-project (meta, selve, genomics).
user-invocable: true
argument-hint: [concept name — e.g., CYP2D6, POTS, retrieval paradox]
effort: medium
---

# Knowledge Compile

Synthesize scattered research memos into a unified concept article. Reads across
projects, extracts claims with provenance, surfaces contradictions, identifies gaps.

**Not an entity page.** Entity pages (via /entity-management) track facts about a
single entity with versioned provenance. Compiled articles synthesize *understanding*
across multiple sources and multiple entities. A CYP2D6 entity page tracks allele
frequencies and function. A CYP2D6 compiled article synthesizes what we know about
its metabolism across genomics findings, selve health observations, and research
literature.

## When to Use

- User asks "what do we know about X across projects?"
- Multiple research memos (3+) touch the same concept but were written in different
  sessions/projects and haven't been synthesized
- Before starting a new implementation that depends on cross-project domain knowledge
- After a research cycle produces findings that should be consolidated

## When NOT to Use

- Single-entity fact tracking -> use /entity-management
- Literature review from external sources -> use /researcher
- Single-project implementation notes -> just read the memos
- Concept with <3 touching memos -> not enough to synthesize

## Phases

### Phase 1: Discover Sources

Search across all three projects for the concept:

```bash
# Step 1: Header-grep FIRST — finds files where concept is a primary topic
# (has its own section heading), not just mentioned in passing. This is the
# key noise filter: CYP2D6 appears in 134 files but has a heading in ~25.
grep -r "^#.*{concept}" ~/Projects/selve/docs/ ~/Projects/genomics/docs/ ~/Projects/meta/research/ --include="*.md" -l

# Step 2: MCP search for section-level matches (if server has been restarted
# since any recent meta_mcp.py edits — new scopes require restart)
search_meta("{concept}", scope="all", max_tokens=500)
```

List all matching files with a one-line relevance snippet. Discard files that
mention the concept only in passing (single reference in a list). Keep files
where the concept is a primary topic or has a dedicated section.

**Stop at 70% of turns and synthesize** — don't search exhaustively.

### Phase 2: Read and Extract

For each source file (up to 15):

1. Read the file (or relevant sections if large)
2. Extract discrete claims about the concept, each with:
   - The claim text
   - Source file path and project
   - Date (from frontmatter or filename)
   - Confidence/conviction level (if stated)
   - Source grade (if tagged, e.g., [A1], [CALC])
3. Note any contradictions between sources
4. Note the date of each source — older claims may be superseded

### Phase 3: Compile

Produce a unified markdown article:

```markdown
---
type: compiled
concept: {Concept Name}
compiled: {YYYY-MM-DD}
sources: {N}
projects: [{list of projects with sources}]
---

## Summary

[2-3 sentence overview of current understanding. Lead with what's known,
then what's uncertain.]

## Key Claims

| # | Claim | Source | Project | Date | Grade |
|---|-------|--------|---------|------|-------|
| 1 | ... | pgx_deep_dive.md | selve | 2026-03 | [A1] |
| 2 | ... | combinatorial_pgx_memo.md | genomics | 2026-02 | [CALC] |

[Order by confidence, not chronologically. Highest-confidence claims first.]

## Contradictions and Open Questions

[Where sources disagree, cite both sides with their provenance.
These are the most valuable part — they surface disagreements that
live in different repos and would otherwise go unnoticed.]

## Timeline

[If the understanding evolved over time, show the progression:
when beliefs changed and why.]

## Cross-References

[Links to all source memos, grouped by project]

## Gaps

[What's missing — questions that no source addresses, data that
would resolve contradictions, follow-up research suggested.]
```

### Phase 4: File

Route the compiled article based on scope:

**Cross-project compilations** (sources from 2+ projects):
- Write to `~/Projects/meta/research/compiled/{concept-slug}.md`
- Meta is the cross-project synthesis repo — this is its purpose
- Indexed by meta_mcp.py via `research/compiled/*.md` glob

**Single-project compilations** (all sources from one project):
- Write to that project's `docs/compiled/{concept-slug}.md`
- E.g., genomics-only compilation -> `~/Projects/genomics/docs/compiled/`

Create the `compiled/` directory if it doesn't exist.

Commit with message: `[research] Compile {concept} — {N} sources across {projects}`

## Key Properties

- **Derived, not source-of-truth.** Source memos remain authoritative. Compiled
  articles are rederivable — re-run the skill to update.
- **Freshness via frontmatter.** The `compiled:` date tells you when it was last
  synthesized. If source memos have been updated since, re-compile.
- **Provenance per claim.** Every claim in the table traces back to a specific
  file in a specific project. No orphan claims.
- **Contradictions are features.** The contradictions section is the highest-value
  part. Don't resolve them — surface them. The user or a future research session
  resolves them.

## Relationship to Other Skills

| Skill | Scope | When to use instead |
|-------|-------|---------------------|
| /entity-management | Single entity, versioned facts | Tracking CYP2D6 allele data |
| /researcher | External literature | Need new papers, not internal synthesis |
| /knowledge-diff | Novel information extraction | Analyzing a single new source |
| /research-cycle | Discovery loop | Finding gaps, not synthesizing existing |

## Anti-Patterns

- **Don't compile with <3 sources.** Below 3, just read the memos directly.
- **Don't resolve contradictions.** Surface them. Resolution requires judgment
  the skill doesn't have.
- **Don't include every mention.** A memo that mentions CYP2D6 once in a list
  is not a source about CYP2D6. Filter to substantive coverage.
- **Don't skip the gaps section.** The gaps are what make the next research
  session productive.
