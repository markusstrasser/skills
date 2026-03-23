---
name: agent-pliability
description: Make a project's files more discoverable for agents. Splits monolithic docs into semantic subgroups, renames files for self-description, and builds a research/docs index in CLAUDE.md. The goal — file names alone should tell an agent what to read before acting.
argument-hint: "[path to project root — e.g., '~/Projects/genomics', '.', or leave blank for cwd]"
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
effort: low
---

# Agent Pliability — Make Files Self-Discoverable

<core_insight>
A file name is the cheapest index entry. If the name is good enough, the agent
knows to read it without needing a rule. A file called
`context-rot-mitigation-strategies.md` self-triggers when the task involves
context. A file called `notes.md` triggers nothing.

The goal: an agent scanning `ls` output should know which files to read before
acting on any given task — without rules, memory, or instructions telling it to.
</core_insight>

## When to use

- New project onboarding (make it agent-ready)
- After a research sweep produced monolithic output files
- When you notice agents not consulting relevant docs before acting
- Periodic hygiene (quarterly or after major doc changes)

## Phase 1: Scan

```bash
PROJECT_ROOT="${ARGUMENTS:-$(pwd)}"
PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd)
```

Inventory the project's knowledge files. Look at:

1. **Docs directory** — `ls docs/ research/ *.md`
2. **CLAUDE.md** — does it have a research/docs index section?
3. **Skills** — `ls .claude/skills/`
4. **Scripts** — are names descriptive? `ls scripts/`

For each file, note:
- **Line count** (monolith threshold: >150 lines with 3+ `##` sections)
- **Name descriptiveness** — does the name tell you WHEN to read it?
- **Section count** — how many distinct topics in one file?

## Phase 2: Identify problems

<problems>
### 2a. Monoliths

Files with multiple unrelated sections that should be separate files. Signs:
- >150 lines with 3+ top-level `##` sections covering different topics
- You'd need to read the whole file to find the 20 lines that matter
- The index entry would have to say "research on... many things"

**Example:** A 400-line file with sections on context rot, agent reliability,
multi-agent coordination, and reasoning internals → 4 separate files.

**Exception:** Files where sections are deeply cross-referenced and splitting
would lose important connections. Don't split a coherent argument into fragments.

### 2b. Cryptic names

Files where the name doesn't tell you what's inside or when to read it.

| Bad | Better | Why |
|-----|--------|-----|
| `notes.md` | `spliceai-integration-notes.md` | Topic in the name |
| `research.md` | `prs-calibration-research.md` | Specific enough to trigger |
| `TODO.md` | stays `TODO.md` | Convention, everyone knows what it is |
| `analysis.py` | `gnomad-frequency-filter.py` | What it does, not what it is |

**Don't rename:** files with conventional names (`README.md`, `CLAUDE.md`,
`pyproject.toml`), files imported by other code (check callers first), files
referenced by CI/build systems.

### 2c. Missing index

CLAUDE.md has no section mapping docs/research files to "when to consult."
The agent sees the CLAUDE.md but has no pointer to the research that should
inform its decisions.

### 2d. Iterative content (NEVER archive)

**Critical failure mode:** Files that are dated iterations of the same analysis
(e.g., `report_2026_02_19.md`, `report_2026_02_26.md`) look like supersession
candidates. They are NOT. Each iteration typically contains:

- Unique analytical angles not present in later versions
- Intermediate reasoning and exploration paths
- Verification details that the "final" compressed away
- Findings that were later overturned (documenting what was believed when)

**Rule: iterative analysis reports are NEVER candidates for archival or deletion.**
They are candidates for *indexing* — mark the latest as current, list others as
historical context in the CLAUDE.md index.

**How to detect iterative content:**
- Multiple files with the same topic stem and different dates
- Files with names like `*_v1`, `*_v2`, `*_YYYY_MM_DD`
- Files explicitly referencing/building on each other

**What to do instead of archiving:**
1. Index all versions in CLAUDE.md with `[current]` / `[historical]` tags
2. If the latest version is missing corrections found in git log, apply them
3. Add cross-references between versions so each points to the others
4. If truly redundant (copy-paste duplicate, not analytical iteration), propose
   deletion with evidence that no unique content exists — diff the files first

**Example from real failure:** 5 genomics analysis reports archived as
"superseded by latest." Each contained unique analytical angles, verification
trails, and intermediate findings absent from the kept version. The "latest"
also had 5+ stale claims that corrections in later sessions had fixed in the
individual reports but never propagated forward.
</problems>

## Phase 3: Propose changes

Output a table. Don't execute yet.

```markdown
## Pliability Report for {project_name}

### Monoliths to split
| File | Lines | Sections | Proposed split |
|------|-------|----------|----------------|
| research/frontier-models.md | 424 | 8 | context-rot.md, agent-reliability.md, ... |

### Files to rename
| Current name | Proposed name | Reason |
|--------------|---------------|--------|
| analysis.py | gnomad-frequency-filter.py | Describes function |

### Index to add/update in CLAUDE.md
| File | Topic | Consult before |
|------|-------|----------------|
| research/context-rot.md | Context window degradation, mitigation | Designing context management, writing long prompts |
| research/prompt-structure.md | XML tags, emphasis, Opus 4.6 formatting | Writing prompts, skills, CLAUDE.md sections |
```

**Ask the user before proceeding.** Splits and renames are reversible (git) but
disruptive if done wrong.

## Phase 4: Execute

For approved changes only:

<splitting>
### Splitting a monolith

1. Read the original file fully
2. For each new file:
   - Extract the relevant sections
   - Preserve any front matter (date, tier, sources) relevant to that section
   - Add a one-line provenance note: `*Split from {original_file} on {date}.*`
   - Cross-reference siblings if sections referenced each other
3. Delete the original only after all splits are written and verified
4. Git commit: `[pliability] Split {original} into {n} topic files`
</splitting>

<renaming>
### Renaming a file

1. Check for references: `grep -r "old_name" .` (imports, CLAUDE.md, other docs)
2. `git mv old_name new_name`
3. Update all references found in step 1
4. Git commit: `[pliability] Rename {old} → {new} for discoverability`
</renaming>

<indexing>
### Building the CLAUDE.md index

Add or update a section in CLAUDE.md:

```markdown
## Research & Docs Index

Files the agent should consult before acting. Scan this list when starting a task.

| File | Topic | Consult before |
|------|-------|----------------|
| research/context-rot.md | Context degradation evidence, mitigation | Context management, long prompt design |
| research/prompt-structure.md | XML, emphasis, Opus 4.6 formatting | Writing prompts, skills, CLAUDE.md |
| ... | ... | ... |
```

The "Consult before" column is the trigger. It should match task descriptions
the agent would encounter: "writing a prompt," "designing a hook,"
"adding a pipeline stage."

Git commit: `[pliability] Add research index to CLAUDE.md`
</indexing>

## Phase 5: Verify

After all changes:
1. `ls` the affected directories — do the names tell a story?
2. Read the CLAUDE.md index — would an agent know what to read for any given task?
3. Check that no references are broken: `grep -r` for old file names

## What this skill does NOT do

- Rewrite file contents (only splits and moves)
- Change code logic or tests
- Modify CLAUDE.md beyond the index section
- Touch files outside the project root
- Rename conventionally-named files (README, CLAUDE.md, pyproject.toml)
