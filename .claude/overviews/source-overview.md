<!-- Generated: 2026-06-19T12:36:04Z | git: e78884d | model: gemini-3-flash-preview -->

<!-- INDEX
[SCRIPT] hooks/agent-coord.py — coordinates multiple concurrent Claude sessions to avoid file conflicts
[SCRIPT] hooks/lint_hook_input_contract.py — validates that hooks correctly parse the Claude Code stdin envelope
[SCRIPT] hooks/generate-overview.sh — entry point for automated codebase overview generation
[SCRIPT] hooks/add-mcp.sh — CLI utility to add MCP server presets to project configuration
[MODULE] hooks/commit-check-parse.py — logic for validating git commit message structure and trailers
[MODULE] hooks/posttool_research_reformat.py — cleans and truncates noisy research/search tool outputs
[MODULE] hooks/source-check-validator.py — enforces provenance tag density and structural rules in research docs
[MODULE] hooks/precompact-extract.py — extracts epistemic content (hedging, decisions) before context compaction
[CLASS] Hook — executable scripts triggered by Claude Code lifecycle events (PreToolUse, PostToolUse, Stop, etc.)
[FLOW] tool_input → hook → decision/additionalContext — how hooks intercept and influence agent actions
[FLOW] transcript → precompact-extract.py → checkpoint.md — preservation of context across compactions
[LIB] jq — used for JSON parsing and manipulation in shell hooks
[LIB] uv — used for fast Python execution and dependency management
-->

### Code inventory

The codebase consists of a comprehensive suite of automation hooks and utility scripts designed to govern, monitor, and assist AI agents (Claude Code and Codex).

**Agent Coordination & Session Management**
* `hooks/agent-coord.py`: Manages `.claude/agent-work.md` to track active PIDs and terminal IDs across concurrent sessions.
* `hooks/kimi-session-start.sh`: Persists session IDs for Kimi CLI integration.
* `hooks/peer-session-count.sh`: Detects independent Claude sessions sharing the same working directory.
* `hooks/session-stability-log.sh`: Instruments session ID continuity across compactions and resumes.

**Governance & Safety Gates (Blocking)**
* `hooks/pretool-subagent-gate.sh`: Blocks subagent dispatches lacking output instructions or write-stubs; monitors memory pressure.
* `hooks/pretool-git-add-all-guard.sh`: Blocks dangerous `git add .` or `-A` commands.
* `hooks/pretool-plan-protect.sh`: Prevents accidental deletion of plan and checkpoint files.
* `hooks/pretool-modal-run-guard.sh`: Validates Modal configurations (GPU/disk) before image builds.
* `hooks/pretool-uv-python-guard.py`: Forces use of `uv run` for Python scripts to ensure dependency availability.
* `hooks/pretool-cursor-model-guard.py`: Restricts Cursor-agent to native Composer models.

**Epistemic & Research Quality (Advisory)**
* `hooks/postwrite-source-check.sh`: Validates provenance tags (e.g., `[SOURCE: url]`) in research documents.
* `hooks/posttool_research_reformat.py`: Reformats and truncates large search/paper outputs to save context window.
* `hooks/pretool-research-skill-gate.py`: Ensures the `/research` skill is loaded before allowing deep search queries.
* `hooks/postwrite-frontier-timeliness.sh`: Warns when citing stale AI models without a disclaimer.
* `hooks/pretool-consensus-search.sh`: Nudges agents away from "best/top" noise-heavy search queries.

**Forensics & Telemetry**
* `hooks/hook-trigger-log.sh`: Unified logger for all hook firings to track ROI and false-positive rates.
* `hooks/sessionend-log.sh`: Generates "flight receipts" including cost, duration, and commit history.
* `hooks/permission-log.sh`: Records permission requests and denials for autonomy measurement.
* `hooks/posttool-failure-log.sh`: Classifies and logs tool errors (syntax, timeout, network, etc.).

**Developer Utilities**
* `hooks/add-mcp.sh`: Adds MCP servers (Chrome, Exa, Anki) to `.mcp.json`.
* `hooks/generate-overview.sh`: Generates project overviews using LLM-based summarization.
* `hooks/validate-changed-hooks.sh`: Pre-commit gate that syntax-checks shell and Python hooks.

### Data flow

Data primarily flows through the Claude Code hook protocol:

1.  **Input**: Claude Code pipes a JSON envelope to `stdin`. This envelope contains the `hook_event_name`, `tool_name`, `tool_input` (e.g., command, file path), and session metadata (`cwd`, `session_id`).
2.  **Processing**:
    *   **Pre-filters**: Shell scripts use `grep` or `jq` for fast path/command matching.
    *   **Analysis**: Python scripts parse the envelope to evaluate complex logic (e.g., AST parsing in `pretool-modal-run-guard.sh` or semantic checks in `source-check-haiku.py`).
3.  **State Persistence**:
    *   **Global Logs**: Events are appended to JSONL files in `~/.claude/` (e.g., `hook-triggers.jsonl`, `session-receipts.jsonl`).
    *   **Session State**: Temporary counters and trackers are stored in `/tmp/` keyed by `$PPID` or `session_id`.
4.  **Output**:
    *   **Blocking**: Hooks exit with code `2` and a message to `stderr` to stop the agent.
    *   **Advisory**: Hooks exit with code `0` and return a JSON object containing `additionalContext` to nudge the agent.
    *   **Rewriting**: `PreToolUse` hooks can return `updatedInput` to modify commands (e.g., injecting `PYTHONUNBUFFERED=1`).

### Key abstractions

*   **The Hook Envelope**: A standard JSON structure received on `stdin`. Modules like `lint_hook_input_contract.py` enforce that all hooks read from `.tool_input` rather than the top level.
*   **Shadow Mode**: A pattern where hooks log "would-fire" events to a `.jsonl` file without actually blocking or advising, used to measure precision before enforcement (e.g., `stop-progress-check.sh`).
*   **Fail-Open**: A design principle implemented via `trap 'exit 0' ERR` and `2>/dev/null`, ensuring that automation bugs do not wedge the agent's main loop.
*   **Provenance Taxonomy**: A shared vocabulary of tags (`[SOURCE:]`, `[DATA]`, `[INFERENCE]`) defined in `provenance_tags.json` and projected into `provenance_tags.re` for consistent enforcement across multiple gates.
*   **Session Attribution**: The practice of using `session_id` or `/tmp/session-touched-<id>.txt` to distinguish one agent's work from another in concurrent environments.

### Dependencies

| Package | Purpose |
| :--- | :--- |
| `jq` | Essential for parsing and generating JSON in shell-based hooks. |
| `uv` | Used to manage Python environments and execute scripts with project-specific dependencies. |
| `pyright` | Invoked by `posttool-pyright-check.sh` to provide incremental type-checking feedback. |
| `git` | Used extensively for diffing, logging, and metadata (trailers/notes) management. |
| `python3` | The primary engine for complex logic, AST parsing, and semantic evaluation. |
| `ed` | Used for atomic file insertions in `append-skill-memento.sh`. |