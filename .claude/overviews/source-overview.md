<!-- Generated: 2026-06-03T19:05:40Z | git: 5f44068 | model: gemini-3-flash-preview -->

<!-- INDEX
[SCRIPT] hooks/agent-coord.py — Coordinates multiple Claude sessions via a shared status file to avoid work conflicts.
[SCRIPT] hooks/add-mcp.sh — CLI tool to add MCP server presets (exa, svelte, etc.) to project configuration.
[SCRIPT] hooks/generate-overview.sh — Entry point for regenerating codebase overviews using LLM-based analysis.
[SCRIPT] hooks/posttool_research_reformat.py — Rewrites noisy research/search MCP outputs to preserve context window.
[SCRIPT] hooks/source-check-validator.py — Validates structural provenance tags ([SOURCE], [DATA]) in research documents.
[SCRIPT] hooks/precompact-extract.py — Extracts epistemic content (hedging, decisions) before session compaction.
[HOOK] pretool-subagent-gate.sh — Blocks/advises on subagent dispatch based on memory pressure and output discipline.
[HOOK] stop-research-gate.sh — Blocks session termination if research files lack required provenance citations.
[HOOK] pretool-llmx-guard.sh — Blocks invalid model names, forbidden flags, and chat-style CLI automation for llmx.
[HOOK] posttool-bash-failure-loop.sh — Detects consecutive Bash failures and injects targeted diagnostic advice.
[HOOK] stop-plan-gate.sh — Unified gate verifying plan status and executing ```verify block acceptance criteria.
[HOOK] pretool-git-add-all-guard.sh — Blocks dangerous global git commands (add -A, add .) to prevent artifact leakage.
[FLOW] tool_output → archive → reformatted_output — Research MCP results are archived raw and summarized for the LLM.
[FLOW] session_transcript → checkpoint.md — Epistemic state is extracted during compaction to prevent context loss.
[LIB] jq — Used for robust JSON parsing and manipulation in shell scripts.
[LIB] pyright — External static type checker used for regression detection in Python edits.
-->

### Code inventory

#### Agent Coordination & Session Management
* `hooks/agent-coord.py`: Manages `.claude/agent-work.md` to track active PIDs and file locks across concurrent sessions.
* `hooks/kimi-session-start.sh`: Persists session IDs for Kimi CLI integration.
* `hooks/prepare-commit-msg-session-id.sh`: Automatically appends `Session-ID` trailers to git commits for provenance tracking.
* `hooks/agent-coord.py`: CLI entry points: `status`, `register`, `check`, `deregister`.

#### Research & Epistemic Governance
* `hooks/posttool_research_reformat.py`: Intercepts large MCP outputs (Exa, PubMed) and reformats them into structured summaries.
* `hooks/source-check-validator.py`: Enforces tag density and structural validity of citations like `[SOURCE: url]` or `[A1]`.
* `hooks/source-check-haiku.py`: Uses a sub-model to semantically rate source coverage in research memos.
* `hooks/postwrite-source-check.sh`: Trigger for validating provenance on files in `docs/` or `research/` paths.

#### Automation & Tooling Guards
* `hooks/pretool-subagent-gate.sh`: Monitors system memory and enforces "write-stub-first" discipline for subagents.
* `hooks/pretool-llmx-guard.sh`: Validates `llmx` CLI calls, blocking forbidden models (Gemini 2.5) and unbuffered redirects.
* `hooks/pretool-git-add-all-guard.sh`: Prevents accidental staging of scratch files by blocking `git add .` and `git add -A`.
* `hooks/pretool-bash-loop-guard.sh`: Blocks multiline shell loops that cause `zsh` parse errors in the Claude harness.

#### Verification & Quality Control
* `hooks/stop-plan-gate.sh`: Executes shell commands found in ````verify```` blocks within plan files to gate session completion.
* `hooks/posttool-pyright-check.sh`: Runs `pyright` on edited Python files and reports only *newly introduced* errors.
* `hooks/pretool-ast-precommit.sh`: Validates Python syntax in staged `.py` and inline `.sh` blocks before allowing a commit.
* `hooks/stop-verify-claims.sh`: Checks final assistant messages against `git log` to ensure "I committed" claims are true.

#### Telemetry & Logging
* `hooks/hook-trigger-log.sh`: Centralized logger for all hook actions (block/warn/allow) into `~/.claude/hook-triggers.jsonl`.
* `hooks/posttool-failure-log.sh`: Classifies and logs tool errors (timeout, permission, syntax) for ROI analysis.
* `hooks/sessionend-log.sh`: Generates "flight receipts" including cost, duration, and context usage at session end.

### Data flow

1.  **Tool Execution**: When a tool (Bash, Read, MCP) is called, `PreToolUse` hooks (like `pretool-llmx-guard.sh`) validate or rewrite the input.
2.  **Output Processing**: `PostToolUse` hooks (like `posttool_research_reformat.py`) intercept the result. Raw data is moved to `~/.claude/tool-output-archive/`, and a reformatted summary is returned to the agent.
3.  **State Persistence**: Throughout the session, `posttool-session-touched-log.sh` tracks which files were modified.
4.  **Compaction**: When the context window fills, `precompact-log.sh` triggers `precompact-extract.py` to pull "epistemic content" (decisions, open questions) into `.claude/checkpoint.md`.
5.  **Session Close**: `Stop` hooks (like `stop-research-gate.sh`) verify the state of the filesystem and git log. If valid, `sessionend-log.sh` writes a final receipt to `~/.claude/session-receipts.jsonl`.

### Key abstractions

*   **Provenance Tags**: A shared vocabulary (`[SOURCE]`, `[DATA]`, `[INFERENCE]`, `[A1-F6]`) used across 5+ files to mark the origin of factual claims.
*   **Advisory Wrapper**: The pattern of converting blocking hooks to non-blocking via `advisory-wrapper.sh`, logging the "block" but allowing the tool to proceed with `additionalContext`.
*   **Session State Tracking**: Use of `/tmp/claude-*-${PPID}` or `${CLAUDE_SESSION_ID}` to maintain state (like search burst counts or unverified scripts) across discrete tool calls.
*   **Shadow Mode**: A pattern (seen in `stop-progress-check.sh` and `stop-unsupported-completion.sh`) where hooks log "would-fire" events to JSONL for precision testing without affecting the agent.

### Dependencies

| Library | Usage |
| :--- | :--- |
| `jq` | Primary engine for parsing and rewriting hook JSON payloads in shell scripts. |
| `uv` | Used to run Python-based scripts and validators with managed dependencies. |
| `pyright` | Static type checking for Python regression detection. |
| `anthropic-sdk` | (Via `urllib` in `source-check-haiku.py`) Used for semantic review of research quality. |
| `git` | Extensively used for state verification, diffing, and provenance (git notes). |
| `duckdb` | Referenced in guards to prevent double-quote string literal errors. |