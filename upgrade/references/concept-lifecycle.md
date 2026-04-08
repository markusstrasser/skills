<!-- Reference file for evolution-forensics skill. Loaded on demand. -->

# Concept Lifecycle Inference (Phase 1d)

Concepts are tracked entities that persist across file renames, merges, and deletions. Derive them from git history — don't maintain a manual registry.

## How to Identify Concepts

A concept is a cluster of related commits sharing a scope tag, touching overlapping files, or referencing the same improvement-log finding. Examples:
- `dup-read-detection` — research memo → session-analyst detection rule → hook → promoted to block
- `finding-triage-db` — script → DB → retired (full lifecycle, short-lived)
- `knowledge-substrate` — MCP server → retired, replaced by hook + propagate-correction.py

## Lifecycle States

| State | Signal |
|-------|--------|
| **RESEARCH** | Exists only in research/, decisions/, or brainstorm artifacts |
| **PROTOTYPE** | Script or tool exists but isn't wired into any workflow |
| **INTEGRATED** | Wired in: called by a skill, hook, pipeline, or justfile recipe |
| **PROMOTED** | Graduated: advisory→blocking, optional→default, project→cross-project |
| **NARROWED** | Scope reduced: exceptions added, conditions tightened |
| **SUPERSEDED** | Replaced by something else (check vetoed-decisions.md, commit bodies) |
| **RETIRED** | Deleted or archived |

## Typed Relationships

- **implements** — concept X implements idea from memo Y
- **replaces** — concept X supersedes concept Y
- **narrows** — concept X restricts scope of concept Y
- **extends** — concept X broadens concept Y
- **deprecates** — concept X makes concept Y obsolete

## Output Format

Write concept lifecycle to `$ARTIFACT_DIR/concept-lifecycle.md`:

```markdown
## Concept: [name]
**State:** INTEGRATED
**First seen:** 2026-03-10 (research/agent-memory-architectures.md)
**Current manifestation:** scripts/propagate-correction.py + hook
**Relationships:** replaces knowledge-substrate, implements correction-propagation
**Trajectory:** RESEARCH → PROTOTYPE → INTEGRATED (12 days)
**Evidence:** [commit hashes]
```
