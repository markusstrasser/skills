<!-- Generated: 2026-04-09T16:29:53Z | git: e858f7e | model: gemini-3-flash-preview -->

<!-- INDEX
[SCRIPT] hooks/generate-overview.sh — Core generator: extracts codebase via repomix and updates overviews via Gemini
[SCRIPT] hooks/generate-overview-batch.sh — Batch processor for multiple project overviews using Gemini Batch API (50% cost reduction)
[SCRIPT] hooks/overview-staleness-cron.sh — Daily maintenance script that regenerates overviews if they are >7 days old
[SCRIPT] hooks/add-mcp.sh — CLI utility to add MCP server presets (exa, anki, svelte, etc.) to project configuration
[SCRIPT] hooks/agent-coord.py — Multi-session coordinator that prevents file conflicts between concurrent agents
[MODULE] hooks/commit-check-parse.py — Logic for validating git commit message structure, scopes, and trailers
[MODULE] hooks/posttool_research_reformat.py — Content transformation engine for cleaning and archiving noisy research tool outputs
[MODULE] hooks/precompact-extract.py — Epistemic extractor that preserves hedging, decisions, and open questions before context compaction
[MODULE] hooks/source-check-validator.py — Structural validator for provenance tags ([SOURCE:], [DATA], etc.) in research prose
[FLOW] codebase → repomix → Gemini → markdown — The transformation of source code into functional overviews
[FLOW] transcript → precompact-extract.py → checkpoint.md — Extraction of epistemic state to survive context window compaction
[FLOW] tool_output → research_reformat.py → archive/ — Quarantine and normalization of high-volume research data
[LIB] repomix — Codebase packing for LLM consumption
[LIB] llmx — CLI/Python interface for multi-model chat and batch processing
[LIB] jq — JSON processing for configuration and hook data
-->

### Code inventory

#### Overview Generation
Automated system for maintaining high-level documentation of the codebase.
* `hooks/generate-overview.sh`: The primary entry point for generating a single or auto-configured set of overviews.
* `hooks/generate-overview-batch.sh`: Orchestrates multiple overview requests into a single Batch API job for efficiency.
* `hooks/overview-staleness-cron.sh`: Monitors `overview-marker` files and triggers updates based on age and git activity.
* `hooks/postmerge-overview.sh`: Git hook to refresh overviews automatically after a pull or merge.
* `hooks/sessionend-overview-trigger.sh`: Analyzes session changes (LOC, structural changes) to decide if a refresh is warranted.

#### Epistemic & Research Governance
Tools for enforcing citation standards and preserving "soft" knowledge (uncertainty, rationale).
* `hooks/source-check-validator.py`: Validates that factual claims in research paths have appropriate provenance tags.
* `hooks/posttool_research_reformat.py`: Intercepts noisy MCP outputs (like paper text or search results) to normalize them for the LLM.
* `hooks/precompact-extract.py`: Scans conversation transcripts before compaction to save "epistemic content" (hedged claims, negative results) into `checkpoint.md`.
* `hooks/postwrite-frontier-timeliness.sh`: Detects citations of obsolete models (e.g., GPT-3.5) without staleness disclaimers.

#### Agent Coordination & Safety
Infrastructure for managing multiple agents and preventing common failure modes.
* `hooks/agent-coord.py`: Uses a shared `.claude/agent-work.md` file and process tracking to prevent agents from editing the same files.
* `hooks/pretool-subagent-gate.sh`: Blocks subagent spawning under high memory pressure or when runaway delegation is detected.
* `hooks/pretool-llmx-guard.sh`: Prevents "spin loops" and catches hallucinated model flags or forbidden model versions.
* `hooks/pretool-multiagent-commit-guard.sh`: Prevents global git operations (like `git add .`) when multiple agents are active in the same repo.

#### Git & Workflow Automation
Hooks that enforce project-specific conventions during the development lifecycle.
* `hooks/commit-check-parse.py`: Validates commit messages against the `[scope] Verb — why` format and suggests trailers.
* `hooks/prepare-commit-msg-session-id.sh`: Automatically appends the current `Session-ID` to git commit trailers.
* `hooks/stop-plan-gate.sh`: Blocks session termination if acceptance criteria in a plan's `verify` block are failing.
* `hooks/postcommit-propagate-check.sh`: Warns when a commit touches files that have downstream consumers listed in a dependency manifest.

### Data flow

1.  **Codebase to Overview**: `repomix` packs source files based on `OVERVIEW_DIRS` config → `generate-overview.sh` wraps this in a prompt → `llmx` sends to Gemini → Output is saved to `.claude/overviews/`.
2.  **Epistemic Preservation**: `SessionEnd` or `PreCompact` triggers → `precompact-extract.py` parses the JSONL transcript → Epistemic items (questions, hedges) are written to `.claude/checkpoint.md` → Agent reads checkpoint to resume state.
3.  **Research Archiving**: Research MCP tool returns raw data → `posttool_research_reformat.py` hashes the content → Raw data is saved to `~/.claude/tool-output-archive/` → A truncated, normalized summary is returned to the agent's context.
4.  **Telemetry**: Hooks pipe JSON metadata to `hook-trigger-log.sh` → Appended to `~/.claude/hook-triggers.jsonl` → Used for ROI and failure rate analysis.

### Key abstractions

*   **Provenance Tags**: A shared vocabulary (`[SOURCE:]`, `[DATA]`, `[INFERENCE]`, `[TRAINING-DATA]`) used across 5+ files to track the origin of factual claims.
*   **Session-ID**: A unique identifier stored in `.claude/current-session-id` used to link git commits, logs, and temporary state files across different hooks.
*   **Advisory Wrapper**: The pattern of exiting `0` while providing `additionalContext` in JSON, allowing hooks to guide the agent without hard-blocking the workflow.
*   **Plan Verify Blocks**: Executable bash snippets inside markdown plans (` ```verify `) used by `stop-verify-plan.sh` to mechanically confirm task completion.

### Dependencies

*   `repomix`: Used for packing codebase subsets into a single context for overview generation.
*   `llmx`: The primary interface for interacting with LLMs (Gemini, GPT) via CLI or Python API for batch jobs and reviews.
*   `jq`: Heavily utilized in shell scripts for robust parsing of the JSON objects passed by Claude Code hooks.
*   `pyright`: Used by `posttool-pyright-check.sh` to provide immediate feedback on Python syntax and type errors after a write.
*   `uv`: Used for fast execution of Python scripts and managing tool environments (e.g., `uv run llmx`).