<!-- Generated: 2026-04-12T23:51:56Z | git: 757c45a | model: gemini-3-flash-preview -->

<!-- INDEX
[SCRIPT] add-mcp.sh — adds MCP servers to project configuration via presets
[SCRIPT] advisory-wrapper.sh — converts blocking hooks into advisory-only logging hooks
[SCRIPT] agent-coord.py — coordinates multiple concurrent Claude sessions via a shared status file
[SCRIPT] append-skill-memento.sh — appends known issues to skill documentation
[SCRIPT] commit-check-parse.py — validates git commit message formatting and trailers
[SCRIPT] generate-overview.sh — entry point for codebase overview generation
[SCRIPT] hook-trigger-log.sh — unified telemetry logger for all hook events
[SCRIPT] permission-denied-retry.sh — auto-retries safe tool calls incorrectly denied by Claude
[SCRIPT] posttool_research_reformat.py — cleans and truncates noisy research/search tool outputs
[SCRIPT] precompact-extract.py — extracts epistemic content (hedging, decisions) before context compaction
[SCRIPT] source-check-validator.py — validates provenance tags and source density in research files
[MODULE] source-check-haiku.py — uses Claude Haiku to semantically rate source coverage
[FLOW] tool_output → hook-trigger-log.sh → ~/.claude/hook-triggers.jsonl — telemetry flow
[FLOW] transcript → precompact-extract.py → .claude/checkpoint.md — handoff state preservation
[LIB] jq — used for robust JSON manipulation in shell scripts
[LIB] pyright — used for static type checking in Python hooks
-->

### Code inventory

#### Hook Infrastructure & Telemetry
These scripts manage the execution and monitoring of the hook system itself.
* `hook-trigger-log.sh`: The central telemetry sink. It logs every hook firing (warn, block, allow) to a unified JSONL file for ROI analysis.
* `advisory-wrapper.sh`: A utility that wraps any blocking hook, allowing it to run but converting a "block" decision into an "allow" with an advisory message.
* `permission-log.sh`: Specifically tracks `PermissionRequest` and `PermissionDenied` events to measure agent autonomy.

#### Git & Governance Automation
Scripts that enforce project standards during the commit and development lifecycle.
* `pretool-commit-check.sh` / `commit-check-parse.py`: Enforces a specific commit format: `[scope] Verb — why`, and suggests trailers like `Evidence:` or `Session-ID:`.
* `stop-uncommitted-warn.sh`: Automatically stages and commits session changes at session end to prevent work loss.
* `pretool-ast-precommit.sh`: Validates Python syntax in staged files before allowing a commit.
* `prepare-commit-msg-session-id.sh`: Automatically appends the current session ID to git commit trailers.

#### Epistemic & Research Guardrails
A large group of scripts dedicated to maintaining high standards for factual claims and research quality.
* `postwrite-source-check.sh` / `source-check-validator.py`: Validates "provenance tags" (e.g., `[SOURCE: url]`, `[DATA]`, `[INFERENCE]`) in research markdown files.
* `posttool-research-reformat.sh` / `posttool_research_reformat.py`: Intercepts noisy MCP outputs (like full research papers or search results), archives the raw text, and presents a cleaned summary to the agent.
* `subagent-epistemic-gate.sh`: Inspects subagent outputs for factual claims, warning if they lack citations.
* `postwrite-frontier-timeliness.sh`: Warns if the agent cites older AI models (e.g., GPT-4, Claude 3.5) without a "pre-frontier" disclaimer.

#### Session & Subagent Management
Tools for managing the state and behavior of Claude sessions and subagents.
* `agent-coord.py`: Manages `.claude/agent-work.md` to prevent multiple agents from editing the same files simultaneously.
* `precompact-log.sh` / `precompact-extract.py`: Runs before Claude compacts its context window. It extracts "epistemic content" (uncertainties, negative results, decisions) into a `checkpoint.md` file so they aren't lost in the summary.
* `pretool-subagent-gate.sh`: Prevents "agent recursion" or runaway spawning by checking system memory and process counts.
* `stop-plan-gate.sh`: Blocks session termination if a plan's `verify` block (acceptance criteria) fails.

#### Tool-Specific Guards
Utilities that prevent common errors with specific CLI tools or MCPs.
* `pretool-llmx-guard.sh`: Prevents common mistakes with the `llmx` CLI, such as using forbidden models or hallucinated flags.
* `pretool-bash-loop-guard.sh`: Blocks multiline shell loops that typically cause Zsh parse errors in the agent environment.
* `pretool-duckdb-quote-guard.sh`: Catches the common DuckDB error of using double quotes for string literals.

### Data flow

1.  **Telemetry Flow**: Most hooks pipe their decisions into `hook-trigger-log.sh`, which appends to `~/.claude/hook-triggers.jsonl`. This provides a global audit trail of agent behavior and hook effectiveness.
2.  **Compaction Recovery**: When a session hits the context limit, `precompact-extract.py` reads the session transcript, extracts key sentences (questions, hedged claims, decisions), and writes them to `.claude/checkpoint.md`.
3.  **Research Archiving**: `posttool_research_reformat.py` takes raw tool results, hashes them, and saves the full content to `~/.claude/tool-output-archive/` while returning a truncated version to the agent's active context.
4.  **Session Coordination**: `agent-coord.py` reads and writes to `.claude/agent-work.md`, using file locking (`fcntl`) to ensure atomic updates across different terminal sessions.

### Key abstractions

*   **Provenance Tags**: A shared vocabulary used across 5+ files (e.g., `source-check-validator.py`, `pretool-source-remind.sh`) to label the origin of information: `[SOURCE]`, `[DATA]`, `[INFERENCE]`, `[TRAINING-DATA]`, and NATO Admiralty grades (`[A1]-[F6]`).
*   **Advisory vs. Blocking**: A pattern where hooks return a JSON object with a `decision` of either `allow` (with `additionalContext`) or `block` (with a `reason`).
*   **Session State Files**: Many hooks use `/tmp/claude-*-${PPID}` or `.claude/current-session-id` to maintain state across multiple tool calls within a single session.

### Dependencies

*   **jq**: Used extensively for parsing and generating JSON in shell-based hooks.
*   **pyright**: Invoked by `posttool-pyright-check.sh` to provide immediate feedback on Python code changes.
*   **uv**: Used to run Python scripts with managed dependencies (e.g., `llm-dispatch.py`, `sessions.py`).
*   **git**: The primary source of truth for file changes, commit history, and session baselines.
*   **vm_stat**: Used on macOS to monitor memory pressure before spawning subagents.