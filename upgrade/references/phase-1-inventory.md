<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Phase 1: Inventory (~10% of effort)

**Goal:** Know exactly what exists before imagining what's missing.

## 1a. Codebase grep (NOT codebase-map)

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

## 1b. Concept keyword grep (F1 gate)

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

## 1c. Stage registry check

```python
from pipeline_stages import STAGES
print(f"{len(STAGES)} stages registered")
```

Or equivalent for the project's stage/task registry.

## 1d. Semantic overlap check (F7 gate)

Before promoting any candidate, ask:

- Is this actually new, or a sharper restatement of an existing row?
- Is it a new primitive, or just a limiter on an existing operator?
- Does it have a likely caller in this repo?

If it fails those checks, reject or merge it. Do not assign a new frontier ID just because the wording is different.

**Gate:** Phase 2 cannot start until the inventory file exists and has been read.
