<!-- Generated: 2026-04-08T07:09:32Z | git: 756fea8 | model: gemini-3-flash-preview -->

<!-- INDEX
[SCRIPT] add-mcp.sh — Adds MCP servers (chrome-devtools, exa, anki, etc.) to project configuration
[SCRIPT] generate-overview.sh — Core generator that runs repomix and LLM calls to create markdown overviews
[SCRIPT] generate-overview-batch.sh — Batch processes multiple project overviews via Gemini Batch API for cost efficiency
[SCRIPT] agent-coord.py — Manages multi-session agent coordination and conflict detection via a shared status file
[SCRIPT] hook-trigger-log.sh — Centralized telemetry for logging hook actions (warn, block, allow) to JSONL
[MODULE] commit-check-parse.py — Logic for validating git commit message formats and suggesting trailers
[MODULE] posttool_research_reformat.py — Rewrites and archives noisy research/search MCP outputs
[MODULE] precompact-extract.py — Extracts epistemic content (hedging, decisions, questions) before conversation compaction
[MODULE] source-check-validator.py — Validates provenance tag density and structural correctness in research files
[FLOW] tool_output → posttool_research_reformat.py → ~/.claude/tool-output-archive/ — Archives raw search data
[FLOW] transcript → precompact-extract.py → .claude/checkpoint.md — Preserves state across compaction
[FLOW] hook_events → hook-trigger-log.sh → ~/.claude/hook-triggers.jsonl — Telemetry for ROI analysis
[LIB] repomix — Used to pack codebase context for LLM processing
[LIB] llmx — CLI tool used for model-agnostic LLM chat and batch operations
[LIB] jq — Required for robust JSON parsing in shell scripts
-->

### Code inventory

#### Overview Generation
Automated systems for maintaining codebase and tooling documentation.
* `generate-overview.sh`: The primary engine that uses `repomix` to gather context and `llmx` to generate markdown overviews based on templates in `hooks/overview-prompts/`.
* `generate-overview-batch.sh`: A wrapper for `generate-overview.sh` that bundles multiple requests into a single Gemini Batch API job to reduce costs by 50%.
* `overview-staleness-cron.sh`: A maintenance script that checks project markers and regenerates overviews if they are older than 7 days and the code has changed.
* `postmerge-overview.sh`: A git hook that triggers background regeneration after a pull or merge.

#### Epistemic & Research Guardrails
Tools to ensure data provenance, citation quality, and "thinking" integrity in research-heavy projects.
* `source-check-validator.py`: Validates that research files contain sufficient provenance tags (e.g., `[SOURCE: url]`, `[DATA]`) relative to the number of claims made.
* `posttool_research_reformat.py`: Intercepts noisy MCP outputs from search engines (Exa, Brave, Semantic Scholar), reformats them for readability, and archives the raw data to `~/.claude/tool-output-archive/`.
* `postwrite-frontier-timeliness.sh`: Scans for citations of "pre-frontier" models (like GPT-4 or Claude 3) and warns if a staleness disclaimer is missing.
* `subagent-epistemic-gate.sh`: Inspects subagent outputs for factual claims that lack proper sourcing before they are merged into the main session.

#### Session & State Management
Infrastructure for handling conversation compaction, session logging, and multi-agent coordination.
* `precompact-extract.py`: A critical module that parses conversation transcripts before compaction to save "epistemic content" (hedged claims, negative results, open questions) into a `.claude/checkpoint.md` file.
* `agent-coord.py`: A CLI tool and module that uses a shared `.claude/agent-work.md` file to prevent multiple agents from conflicting on the same files.
* `sessionend-log.sh`: Generates "flight receipts" at the end of a session, logging duration, cost, and git commits to `~/.claude/session-receipts.jsonl`.
* `prepare-commit-msg-session-id.sh`: Automatically appends the current session ID to git commit trailers for traceability.

#### Safety & Automation Hooks
A suite of Claude Code hooks that guard against common failure modes.
* `pretool-subagent-gate.sh`: Blocks subagent spawning if system memory is low or if the dispatch prompt lacks a "synthesis budget" (to prevent turn exhaustion).
* `posttool-bash-failure-loop.sh`: Detects consecutive bash errors and injects targeted diagnostic advice instead of allowing blind retries.
* `pretool-llmx-guard.sh`: Validates `llmx` CLI calls, blocking invalid model names or flags and detecting potential spin loops.
* `pretool-commit-check.sh`: Enforces project-specific git commit standards (prefixes, trailers, and body requirements).

### Data flow

1.  **Telemetry Flow**: Every significant hook event (warning, block, or auto-allow) is piped into `hook-trigger-log.sh`, which appends a JSON entry to `~/.claude/hook-triggers.jsonl`. This data is used for ROI and "Agent Drift" analysis.
2.  **Compaction Recovery**: When a conversation reaches the context limit, `precompact-log.sh` triggers `precompact-extract.py`. It reads the `transcript_path`, extracts key decisions and uncertainties, and writes them to `.claude/checkpoint.md`. Upon restart, `postcompact-verify.sh` reminds the agent to read this checkpoint to recover lost context.
3.  **Research Archiving**: Raw MCP tool results from search tools flow through `posttool_research_reformat.py`. The script calculates a content hash, saves the full raw text to `~/.claude/tool-output-archive/<tool_name>/<hash>.txt`, and returns a shortened, reformatted version to the agent.
4.  **Cost Tracking**: Session costs are persisted by the status line into `/tmp/claude-cockpit-<session>`. At session end, `sessionend-log.sh` moves this data into the permanent `~/.claude/session-receipts.jsonl` log.

### Key abstractions

*   **Provenance Tags**: A shared vocabulary (e.g., `[SOURCE: ]`, `[INFERENCE]`, `[DATA]`, `[TRAINING-DATA]`) used across 5+ files (`source-check-validator.py`, `pretool-source-remind.sh`, `subagent-epistemic-gate.sh`, etc.) to track the origin of factual claims.
*   **Advisory Wrapper**: The pattern implemented in `advisory-wrapper.sh` which allows blocking hooks to be converted into non-blocking "advisory" hooks that log issues to `~/.claude/hook-advisory.log` while allowing the tool call to proceed.
*   **Session Baseline**: A pattern where the state of the repository is recorded at the start of a session (e.g., `/tmp/session-base-sha-<id>.txt`) so that hooks like `stop-uncommitted-warn.sh` can distinguish between pre-existing dirty files and changes made specifically during the current session.

### Dependencies

| Package | Usage |
| :--- | :--- |
| `repomix` | Packs codebase files into a single document for overview generation. |
| `llmx` | Handles LLM chat interactions and batch API submissions. |
| `jq` | Used throughout shell hooks for reliable JSON extraction and manipulation. |
| `pyright` | Invoked by `posttool-pyright-check.sh` to provide static analysis feedback on edited Python files. |
| `uv` | Used to manage Python environments and run scripts like `sessions.py`. |
| `ed` | Used in `append-skill-memento.sh` for atomic, portable file editing. |