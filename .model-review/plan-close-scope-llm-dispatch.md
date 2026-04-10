- Target users: agents and repo hooks consuming `~/Projects/skills` across local project repos; not a public SaaS surface
- Scale: currently ~18 active skills, ~33 hooks, several sibling repos consuming overview/research/review hooks; designed for repeated automation across many local repos
- Rate of change: high; dispatch patterns and skill instructions are still changing weekly

## Migration note

- Active-path migration target: normal automation should stop composing raw `llmx chat` calls and route through the shared dispatch helper instead.
- Remaining live compatibility boundary: `hooks/generate-overview.sh` still accepts sibling repos' existing `OVERVIEW_MODEL` config because `/Users/alien/Projects/{genomics,intel,meta,selve,arc-agi,research-mcp,skills}/.claude/overview.conf` already set it.
- Removal condition for that seam: once those repos migrate their overview configs to `OVERVIEW_PROFILE`, delete the `OVERVIEW_MODEL` -> profile mapping in `hooks/generate-overview.sh`.
