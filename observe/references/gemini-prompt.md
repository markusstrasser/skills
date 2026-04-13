<!-- Reference file for observe skill (architecture mode). Loaded on demand. -->

# Gemini Pattern Extraction Prompt

Dispatch compressed transcripts to Gemini 3.1 Pro for structured pattern extraction.

```bash
OBSERVE_PROJECT_ROOT="${OBSERVE_PROJECT_ROOT:-$HOME/Projects/agent-infra}"
ARTIFACT_DIR="${OBSERVE_ARTIFACT_ROOT:-$OBSERVE_PROJECT_ROOT/artifacts/observe}"
PROMPT_FILE="$ARTIFACT_DIR/gemini-pattern-prompt.txt"
cat > "$PROMPT_FILE" <<'PROMPT'
You are extracting STRUCTURAL PATTERNS from agent session transcripts. Output structured findings, not prose.

For each pattern found, output this exact JSON-like format (one per finding):

### PATTERN: [short name]
- **Type:** WORKFLOW_REPEAT | MANUAL_COORDINATION | REINVENTED_LOGIC | CROSS_PROJECT | DECISION_REVISITED | TOOL_GAP
- **Frequency:** [N occurrences across M sessions]
- **Sessions:** [list session ID prefixes where observed]
- **Evidence:** [verbatim quotes from user messages or tool sequences, max 3 lines each]
- **Tool sequence:** [if WORKFLOW_REPEAT: the repeated tool call pattern]
- **User action:** [if MANUAL_COORDINATION: what the user typed to coordinate]
- **Projects:** [which projects involved]

Pattern types to look for:

1. WORKFLOW_REPEAT: Same sequence of 3+ tool calls appearing in 2+ sessions. Example: Read → Grep → Edit → Bash(git commit) appearing in every bug-fix session.

2. MANUAL_COORDINATION: User acting as message bus — typing transitions like "now take that output and...", "check if X was updated after Y", "in the other project, do Z". The user is doing work the system should do.

3. REINVENTED_LOGIC: Agent builds the same function/query/check/transform in multiple sessions. Copy-paste across sessions = missing shared abstraction.

4. CROSS_PROJECT: Similar work patterns across different projects suggesting shared infrastructure. Example: every project does the same "read CLAUDE.md, check rules, grep for X" dance.

5. DECISION_REVISITED: Same design question debated in multiple sessions. Sign of underdocumented or wrong prior decision.

6. TOOL_GAP: Agent attempts something repeatedly with workarounds, suggesting a missing tool. Example: parsing JSON with sed because no jq MCP tool exists.

IMPORTANT:
- Include VERBATIM evidence (exact user messages, exact tool names). I will verify these.
- Only include patterns that appear 2+ times. Single occurrences are noise.
- Do NOT propose solutions — just extract patterns.
- If you find fewer than 3 patterns, that's fine. Don't fabricate.
- Output ONLY the patterns, no preamble or summary.
PROMPT
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile deep_review \
  --context "$ARTIFACT_DIR/all.md" \
  --prompt-file "$PROMPT_FILE" \
  --output "$ARTIFACT_DIR/patterns.md" \
  --meta "$ARTIFACT_DIR/dispatch.meta.json"
```

Save Gemini output to `patterns.md` in `$ARTIFACT_DIR`.
