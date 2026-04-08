<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Operational Discipline

Cross-cutting concerns that apply across multiple phases.

## Running Memo Discipline

For long-running novelty sweeps:

1. Read the actual tail of the running memo before appending.
2. Append at the tail even if prior pass numbers are out of order.
3. Never rewrite old passes just to normalize numbering or survivor counts.
4. Commit the memo periodically; it is the mission-critical artifact.

If the memo gets numerically messy, preserve append-only history and fix the process forward rather than rewriting the past.

## Cross-Repo Git Safety

Novelty sessions often touch sibling repos (shared skills, meta docs, related projects).

Before any `git diff`, `git status`, or `git commit` on edited files:

1. detect the owning git root for those files
2. switch to that repo before running git commands
3. treat "outside repository" as a routing failure, not a git problem

Do not stage or commit cross-repo edits from the wrong cwd just because the absolute path is visible.

## Effort Budget

| Phase | % of session | Tokens (typical) | Parallelizable? |
|-------|-------------|-------------------|-----------------|
| Inventory | 10% | ~20K | No |
| Brainstorm | 15% | ~200K (with llmx dispatch) | Partially (llmx calls) |
| Research | 25% | ~500K (across agents) | Yes (up to 5 agents) |
| Plan | 15% | ~30K | No |
| Review | 15% | ~300K (cross-model) | Yes (models run in parallel) |
| Implement | 20% | ~400K (agent dispatch) | Yes (up to 5 agents) |

**Total:** ~1.5M tokens for a 6-8 analysis expansion. The inventory and concept grep (~20K tokens) saves ~200K+ in wasted research.
