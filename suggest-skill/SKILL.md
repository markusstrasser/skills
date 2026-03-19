---
name: suggest-skill
description: Analyze recent sessions for repeated multi-tool workflows and suggest new skill or MCP tool candidates. Run after a work session, plan execution, or periodically. The "builder agent" component — detects automation opportunities from actual usage.
user-invocable: true
argument-hint: '[project] [--sessions N]'
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
---

# Suggest Skill

Detect repeated multi-tool workflows in recent sessions and propose concrete skill or MCP tool candidates.

## What This Detects

1. **Repeated tool sequences** — Same 3+ step tool chain appearing across 2+ sessions (e.g., Grep → Read → Edit → Bash test pattern)
2. **Manual orchestration** — User repeatedly giving the same multi-step instructions that could be a single skill invocation
3. **MCP tool gaps** — Cases where the agent shells out to bash or uses multiple tools to accomplish what a single MCP tool could do
4. **Workflow templates** — Recurring session shapes (research → synthesize → commit, debug → fix → test) that could be parameterized

## Process

### Step 1: Extract Transcripts

Parse project from $ARGUMENTS. Default: current project, last 10 sessions (wider window than session-analyst to catch cross-session patterns).

```bash
python3 ~/Projects/skills/session-analyst/scripts/extract_transcript.py <project> --sessions 10 --output ~/Projects/meta/artifacts/suggest-skill/input.md
```

If the extractor isn't available, fall back to reading the 10 most recent JSONL files from `~/.claude/projects/-Users-alien-Projects-<project>/` directly. Strip thinking blocks and base64.

### Step 2: Extract Tool Sequences

Before dispatching to Gemini, do a quick local analysis to identify candidate patterns:

```bash
# Extract tool_use sequences from transcripts
python3 -c "
import json, sys, re
from pathlib import Path
from collections import Counter

input_file = Path.home() / 'Projects/meta/artifacts/suggest-skill/input.md'
text = input_file.read_text()

# Find tool call sequences (look for Tool: or tool_use patterns)
tools = re.findall(r'(?:Tool|tool_use):\s*(\w+)', text)

# Extract 3-grams of tool sequences
trigrams = [tuple(tools[i:i+3]) for i in range(len(tools)-2)]
counts = Counter(trigrams)

print('## Tool Sequence Frequency (3-grams)')
for seq, count in counts.most_common(20):
    if count >= 2:
        print(f'  {\" -> \".join(seq)}: {count}x')

# Extract 4-grams and 5-grams too
for n in [4, 5]:
    ngrams = [tuple(tools[i:i+n]) for i in range(len(tools)-n+1)]
    counts = Counter(ngrams)
    frequent = [(s, c) for s, c in counts.most_common(10) if c >= 2]
    if frequent:
        print(f'\n## Tool Sequence Frequency ({n}-grams)')
        for seq, count in frequent:
            print(f'  {\" -> \".join(seq)}: {count}x')
"
```

### Step 3: Dispatch to Gemini

Send transcripts + tool sequence analysis to Gemini 3.1 Pro for pattern extraction:

```bash
mkdir -p ~/Projects/meta/artifacts/suggest-skill

llmx -p google -m gemini-3.1-pro-preview \
  -f ~/Projects/meta/artifacts/suggest-skill/input.md \
  "$(cat <<'PROMPT'
You are analyzing Claude Code session transcripts to find repeated workflows that should become reusable skills or MCP tools.

For each pattern you find, classify it as:

**SKILL candidate** — A multi-step workflow the agent performs repeatedly that could be invoked with a single /command. Skills are prompt-level instructions that guide the agent through a procedure.
- Good skill: "research a topic, synthesize findings, write memo, commit" — parameterizable, multi-step, judgment needed
- Bad skill: "run pytest" — too simple, just use Bash

**MCP TOOL candidate** — A specific capability that the agent repeatedly builds from bash commands, API calls, or multi-tool chains. MCP tools are deterministic functions the agent can call.
- Good MCP tool: "search sessions by keyword and return summaries" — deterministic, reusable, wraps complex query
- Bad MCP tool: "write a file" — already exists as a native tool

For each candidate, output:

### [SKILL|MCP_TOOL]: [name]
- **Pattern**: What the agent repeatedly does (specific tool sequences and steps)
- **Frequency**: How many times / across how many sessions
- **Current cost**: Approximate tool calls and turns spent each time
- **Trigger**: When would a user invoke this? What are they trying to accomplish?
- **Parameters**: What varies between invocations?
- **Skeleton**:
  For SKILL: A draft SKILL.md frontmatter + outline
  For MCP_TOOL: Function signature, inputs, outputs, implementation sketch

IMPORTANT:
- Only suggest patterns that appear 2+ times across different sessions
- Don't suggest things that already exist as skills (check the skill names in the transcripts)
- Don't suggest trivially simple operations
- Rank by (frequency x complexity saved per invocation)
- Max 7 candidates. Quality over quantity.

Output ONLY the candidates, no preamble.
PROMPT
)"
```

### Step 4: Validate and Deduplicate

Before presenting candidates:

1. **Check existing skills**: `ls ~/Projects/skills/` — skip candidates that duplicate existing skills
2. **Check existing MCP tools**: Read `.mcp.json` files — skip candidates that duplicate existing MCP tools
3. **Check ideas.md backlog**: `grep -i "KEYWORD" ~/Projects/meta/ideas.md` — note if a candidate matches an existing backlog item
4. **Verify frequency claims**: Spot-check that Gemini's claimed patterns actually appear in the transcripts

### Step 5: Output

Present candidates ranked by ROI (frequency x complexity):

```markdown
## Skill/MCP Suggestions — YYYY-MM-DD

**Sessions analyzed:** N (project: X)
**Patterns detected:** N
**New candidates:** N (after dedup with existing skills/tools)

### 1. [SKILL|MCP_TOOL]: name
- **ROI**: [high|medium] — Nsessions x ~N tool calls saved
- **Pattern**: [what happens now]
- **Proposal**: [what it would look like]
- **Skeleton**: [SKILL.md draft or MCP tool signature]
- **Dedup check**: [new | matches backlog item X | similar to existing skill Y]

### 2. ...
```

### Step 6: Persist

Save output to `~/Projects/meta/artifacts/suggest-skill/YYYY-MM-DD.md` for reference.

If the user approves a candidate, offer to scaffold it:
- For SKILL: create directory in `~/Projects/skills/` with SKILL.md
- For MCP_TOOL: propose addition to the relevant MCP server

## Guardrails

- Don't suggest skills for one-off workflows that happened to repeat twice by coincidence
- Don't suggest MCP tools for things that are better as bash aliases or shell functions
- A 3-step workflow used 10 times beats a 10-step workflow used twice — frequency matters more than complexity
- If no strong candidates emerge, say "no clear patterns worth automating" — don't fabricate
- Cross-check with the 10-use threshold from the constitution: "If used/encountered 10+ times -> hook, skill, or scaffolding"

$ARGUMENTS
