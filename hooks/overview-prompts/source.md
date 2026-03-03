You are generating a source code overview for a software project.

This overview helps agents and humans quickly understand what code exists, how it's organized, and how data/control flows through the system. It is regenerated automatically when significant code changes are detected.

<accuracy>
Only describe code that exists in the codebase below. Every file you mention must appear in the codebase. Every class, function, or pattern you describe must be visible in the source. Do not infer features from comments, TODOs, docstrings, or configuration discussions. If something is referenced but its implementation is not present, say so explicitly rather than describing what it might do.
</accuracy>

<what_to_cover>

## Code inventory

Discover functional groups from the code itself. For each group:
- Name the group by what it does (not where files live)
- List modules/scripts with a 1-line description
- Note key entry points, CLI interfaces, or callable APIs

Common groupings (discover, don't assume): data ingestion, processing/transformation, storage/persistence, analysis/computation, automation/scheduling, external integrations, utilities.

## Data flow

How data moves through the system: sources → processing → storage → output.
If a database or schema exists, describe key tables/collections and how they're populated.

## Key abstractions

Classes, protocols, or patterns that appear in 3+ files. Don't list every function — just the shared vocabulary.

## Dependencies

Notable external libraries and what they're used for. Skip standard library.

</what_to_cover>

<what_to_skip>
- Individual function signatures or line-by-line code
- Test files or test fixtures
- Documentation content (just note if docs/ exists)
- Design philosophy or architectural opinions
- Files in data/, logs/, output/, results/, or similar artifact directories
</what_to_skip>

<format>
Start the file with a greppable index block inside an HTML comment. Every subsection in the overview must have a corresponding index line. Prefix tags by type:

```
<!-- INDEX
[SCRIPT] name — one-line purpose
[MODULE] name — one-line purpose
[CLASS] ClassName — one-line purpose
[FLOW] source → sink — what moves
[LIB] package — what it's used for
-->
```

Tag types: `[SCRIPT]` for standalone scripts/CLI tools, `[MODULE]` for importable modules, `[CLASS]` for key abstractions, `[FLOW]` for data flows, `[LIB]` for notable dependencies. Use the tag that best fits; don't force every item into one category.

After the index, use markdown subsections (### headings) whose names match the index entries so an agent can grep the index, then jump to the relevant heading.

- Bullet points with module names in backticks
- 1-2 lines per module, max
- Tables where comparison is useful (e.g., data sources, external APIs)
- Target: 150-300 lines total. Shorter is better if coverage is complete.
</format>
