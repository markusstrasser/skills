# Observe: pliability

Existing approval of concrete split/rename/index work carries forward; do not ask again for the same authorized operation. New scope remains subject to the boundary below.

Make a project's files discoverable for agents. **A file name is the cheapest index entry.** If the
name is good enough the agent knows to read it without a rule: `context-rot-mitigation-strategies.md`
self-triggers on a context task; `notes.md` triggers nothing.

**Scan** knowledge files (docs, research, CLAUDE.md, skills, scripts) for line count, name
descriptiveness, section count → **identify**: **monoliths** (>150 lines, 3+ `##` sections on
different topics) · **cryptic names** (don't say what's inside or when to read it) · **missing index**
(no "consult before" mapping in CLAUDE.md) · **iterative content** — dated iterations of the same
analysis are **NEVER** archival or deletion candidates, they are *indexing* candidates → **propose**
a table (split / rename / index) and **ask before proceeding** → **execute approved changes only**:
splits preserve front matter and add a provenance note
(`[pliability] Split {original} into {n} topic files`); renames `grep -r` for references first, then
`git mv` and update them; indexing adds the "consult before" triggers → **verify** with `ls`, read
the index, check for broken references.

**Does NOT:** rewrite file contents (splits and moves only) · change code or tests · modify CLAUDE.md
beyond the index section · touch files outside the project root · rename conventionally named files
(README, CLAUDE.md, pyproject.toml).
