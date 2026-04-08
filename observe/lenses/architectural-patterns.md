# Architectural Pattern Types

Pattern types extracted from session transcripts by Gemini. These are structural observations -- the creative synthesis happens in Claude.

## WORKFLOW_REPEAT

Same sequence of 3+ tool calls appearing in 2+ sessions. Example: Read -> Grep -> Edit -> Bash(git commit) appearing in every bug-fix session. Signal: missing skill or pipeline.

## MANUAL_COORDINATION

User acting as message bus -- typing transitions like "now take that output and...", "check if X was updated after Y", "in the other project, do Z". The user is doing work the system should do. Signal: missing orchestration or cross-project tooling.

## REINVENTED_LOGIC

Agent builds the same function/query/check/transform in multiple sessions. Copy-paste across sessions = missing shared abstraction. Signal: extract to script, skill, or MCP tool.

## CROSS_PROJECT

Similar work patterns across different projects suggesting shared infrastructure. Example: every project does the same "read CLAUDE.md, check rules, grep for X" dance. Signal: shared skill or hook.

## DECISION_REVISITED

Same design question debated in multiple sessions. Sign of underdocumented or wrong prior decision. Signal: needs a decision journal entry or the prior decision needs revision.

## TOOL_GAP

Agent attempts something repeatedly with workarounds, suggesting a missing tool. Example: parsing JSON with sed because no jq MCP tool exists. Signal: build the tool.

## Convergent Selection Filters

After extracting patterns, apply these filters to select proposals:

1. **Already exists?** Check existing skills, hooks, backlog. Mark as `KNOWN:location` and skip.
2. **Bitter-lesson-proof?** Will a better model make this unnecessary? If yes, build only if cheap (<30 min).
3. **Reversible?** Prefer hooks (removable) over CLAUDE.md rules (sticky) over architectural changes (costly).
4. **Cross-project leverage?** A tool used by 5 projects beats one used by 1.
5. **Evidence of need?** 2 sessions = weak. 5+ sessions = strong. 10+ = urgent.
