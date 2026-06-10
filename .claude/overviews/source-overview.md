<!-- Generated: 2026-06-10T10:47:20Z | git: be39325 | model: gemini-3-flash-preview -->

<!-- INDEX
[SCRIPT] hooks/agent-coord.py — Coordinates multiple Claude sessions via a shared status file
[SCRIPT] hooks/commit-check-parse.py — Logic for validating git commit message formats and trailers
[SCRIPT] hooks/posttool_research_reformat.py — Rewrites noisy research MCP outputs to save context
[SCRIPT] hooks/source-check-validator.py — Structural validator for provenance tags in research files
[SCRIPT] hooks/lint_hook_input_contract.py — Enforces correct stdin/envelope handling in hook scripts
[MODULE] hooks/source-check-haiku.py — Semantic source coverage rater using Anthropic API
[FLOW] tool_output → posttool_research_reformat.py → updated_output — Noisy data is quarantined and summarized
[FLOW] session_start → hooks/kimi-session-start.sh → .claude/current-session-id — Session tracking persistence
[FLOW] git_commit → hooks/pretool-ast-precommit.sh → block/allow — Syntax validation of staged code
[CLASS] HookEnvelope — The JSON structure (tool_name, tool_input, cwd) passed to all hooks
[LIB] pyright — Used for advisory type checking on edited Python files
[LIB] uv — Used for fast Python script execution and environment management
-->

### [SCRIPT] hooks/agent-coord.py
A coordination utility for multi-agent environments. It maintains `.claude/agent-work.md` to track active PIDs, terminal IDs, and the specific files or Modal jobs each agent is currently handling. It includes commands to `register`, `check` for conflicts, and `deregister`.

### [SCRIPT] hooks/commit-check-parse.py
The core logic for git commit validation. It enforces the `[scope] Verb — why` format, checks for `Co-Authored-By: Claude` (blocking), and suggests trailers like `Evidence:`, `Rejected:`, and `Native-First:` based on staged file types (e.g., governance files or new scripts).

### [SCRIPT] hooks/posttool_research_reformat.py
A transformation script that intercepts large MCP outputs from tools like Exa, Brave Search, or research paper readers. It archives the raw text to `~/.claude/tool-output-archive/` and returns a "quarantined" summary to the agent to prevent context window exhaustion.

### [SCRIPT] hooks/source-check-validator.py
Validates the presence and density of provenance tags (e.g., `[SOURCE: url]`, `[DATA]`, `[TRAINING-DATA]`) in research documents. It enforces a 30% cap on training-data citations and ensures quantitative claims have checkable sources.

### [SCRIPT] hooks/lint_hook_input_contract.py
A meta-tool that scans the hook fleet to ensure they correctly implement the Claude Code/Codex input contract. It flags hooks that attempt to read environment variables (which are unset in Claude Code) instead of parsing the stdin JSON envelope.

### [MODULE] hooks/source-check-haiku.py
A semantic analysis module that sends the first 150 lines of a research file to `claude-haiku-4-5` to rate source coverage as GOOD, SPARSE, or NONE, providing specific examples of missing attributions.

### [FLOW] tool_output → posttool_research_reformat.py → updated_output
This flow manages high-volume data ingestion from external search MCPs.
1.  **Source**: Raw JSON/Text from search or paper-fetch tools.
2.  **Processing**: `posttool_research_reformat.py` hashes the content and extracts key sections (Abstract, Introduction, etc.).
3.  **Storage**: Raw content is saved to `~/.claude/tool-output-archive/<hash>.txt`.
4.  **Output**: A truncated, structured summary is injected back into the agent's turn via the `updatedMCPToolOutput` contract.

### [FLOW] session_start → hooks/kimi-session-start.sh → .claude/current-session-id
Ensures session continuity across different CLI environments.
1.  **Source**: `SessionStart` event from Kimi or Claude.
2.  **Processing**: Extracts the UUID and current working directory.
3.  **Storage**: Writes the ID to `.claude/current-session-id`.
4.  **Output**: Subsequent git commits read this file to append `Session-ID:` trailers.

### [FLOW] git_commit → hooks/pretool-ast-precommit.sh → block/allow
A safety gate for code integrity.
1.  **Source**: `git commit` command intercepted by `PreToolUse:Bash`.
2.  **Processing**: Uses `ast.parse` to check staged `.py` files and inline Python blocks in `.sh` files.
3.  **Output**: Returns a `block` decision with line-specific syntax errors if parsing fails, preventing broken code from being committed.

### [CLASS] HookEnvelope
While not a formal Python class, this is the ubiquitous data structure used across 50+ files. It is a JSON object containing:
- `tool_name`: The tool being invoked (e.g., "Bash", "Write", "Agent").
- `tool_input`: Arguments specific to the tool (e.g., `command`, `file_path`).
- `cwd`: The current working directory of the agent.
- `session_id`: The unique identifier for the current conversation.

### [LIB] pyright
Used in `hooks/posttool-pyright-check.sh` to provide real-time type checking. It compares current errors against a cached baseline in `~/.cache/claude-pyright-baseline/` to surface only new regressions introduced by the agent's latest edit.

### [LIB] uv
Used as the primary runner for Python-based hooks (e.g., `hooks/generate-overview.sh`, `hooks/sessionend-index-sessions.sh`). It ensures scripts run with the correct dependencies defined in the `agent-infra` project.