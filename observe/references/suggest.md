# Observe: suggest

Use [transcript preparation](transcript-extraction.md) and [analysis dispatch](analysis-dispatch.md). Apply [candidate lifecycle](candidate-lifecycle.md) before creating a proposal.

Detect repeated multi-tool workflows and propose skill or MCP-tool candidates: repeated tool
sequences (same 3+ step chain across 2+ sessions) · manual orchestration (the user repeating the
same multi-step instructions) · MCP gaps (shelling out to bash for what one tool could do) ·
recurring session shapes worth parameterizing.

Extract transcripts (default: current project, last 10 sessions) → extract 3/4/5-grams of tool
sequences locally, count, keep those appearing 2+ times → dispatch transcripts + the sequence
analysis asking for pattern, frequency, current cost, trigger, parameters, skeleton, classified
**SKILL** (multi-step, judgment needed) vs **MCP TOOL** (deterministic, reusable), max 7, ranked by
frequency × complexity saved. Validate before presenting: `ls ~/Projects/skills/`, read the
`.mcp.json` files, grep the `ideas.md` backlog, and spot-check every frequency claim against the
transcripts. On approval, scaffold the skill dir or propose the MCP addition.

**Guardrails:** no skills for coincidental one-offs that happened twice · no MCP tools for things
better as a bash alias · frequency matters more than complexity · cross-check the 10-use threshold in
GOALS.md · **no strong candidates? say so — do not fabricate.**
