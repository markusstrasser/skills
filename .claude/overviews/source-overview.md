<!-- Generated: 2026-06-15T18:45:33Z | git: fa0ce09 | model: gemini-3-flash-preview -->

<!-- INDEX
[SCRIPT] hooks/agent-coord.py — Coordinates multiple concurrent Claude sessions to avoid work conflicts
[SCRIPT] hooks/generate-overview.sh — Entry point for generating project source/tooling overviews
[SCRIPT] hooks/lint_hook_input_contract.py — Validates that hooks correctly handle Claude/Codex input envelopes
[MODULE] hooks/source-check-validator.py — Structural validator for provenance tags in research files
[MODULE] hooks/posttool_research_reformat.py — Sanitizes and truncates noisy research/search tool outputs
[FLOW] tool_input → hook → additionalContext — How hooks inject guidance into agent turns
[FLOW] session_start → /tmp/session-baseline → session_end — Tracking session-specific file changes
[CLASS] ProvenanceTags — Vocabulary for NATO Admiralty and evidence-based claim tagging
[LIB] jq — Used for JSON parsing and manipulation in shell hooks
[LIB] pyright — Used for static type checking in post-edit hooks
-->

### Code inventory

#### Agent Coordination & Session Management
* `hooks/agent-coord.py`: Maintains `.claude/agent-work.md` to track active PIDs and task descriptions across concurrent sessions.
* `hooks/kimi-session-start.sh`: Persists session IDs for Kimi CLI compatibility.
* `hooks/session-stability-log.sh`: Instruments session ID continuity across boundaries like compaction and resume.
* `hooks/prepare-commit-msg-session-id.sh`: Git hook that auto-appends `Session-ID` trailers to commit messages for attribution.

#### Guardrails & Safety (Blocking)
* `hooks/pretool-subagent-gate.sh`: Blocks subagent spawning based on memory pressure, missing output instructions, or missing "write-stub-first" discipline.
* `hooks/pretool-git-add-all-guard.sh`: Blocks `git add .` and `git add -A` to prevent accidental staging of scratch files.
* `hooks/pretool-bash-loop-guard.sh`: Blocks multiline shell loops that cause zsh parse errors in the agent harness.
* `hooks/pretool-uv-python-guard.py`: Forces the use of `uv run` for Python scripts to ensure project dependencies are available.
* `hooks/pretool-plan-protect.sh`: Prevents accidental deletion of plan and checkpoint markdown files.

#### Epistemic & Research Quality
* `hooks/postwrite-source-check.sh`: Validates provenance tag density and structure in research documents.
* `hooks/posttool-research-reformat.sh`: Intercepts and reformats large search/paper results to save context window.
* `hooks/stop-research-gate.sh`: Blocks session termination if new research claims lack required source tags.
* `hooks/postwrite-frontier-timeliness.sh`: Warns when citing "pre-frontier" models (e.g., GPT-4, Claude 3) without a staleness disclaimer.

#### Automation & Maintenance
* `hooks/generate-overview.sh`: CLI entry point to trigger LLM-generated project overviews.
* `hooks/overview-staleness-cron.sh`: Daily check to regenerate overviews for projects with significant changes.
* `hooks/sessionend-index-sessions.sh`: Triggers incremental indexing of agent logs for full-text search.
* `hooks/validate-changed-hooks.sh`: Pre-commit gate that syntax-checks shell and Python hooks.

### Data flow

1.  **Input Ingestion**: Claude Code/Codex pipes a JSON envelope to `stdin` containing `tool_name`, `tool_input`, `cwd`, and `session_id`.
2.  **State Tracking**: 
    *   `SessionStart` hooks write baselines to `/tmp/session-baseline-{id}.txt`.
    *   `PostToolUse` hooks (Write/Edit) append touched paths to `/tmp/session-touched-{id}.txt`.
3.  **Processing/Validation**: Hooks parse the input (often via `jq` or `python3 -c`) to check against regex patterns or project-specific rules (e.g., `GOALS.md` keywords).
4.  **Output/Feedback**:
    *   **Advisory**: Hooks print JSON to `stdout` with `additionalContext` which is injected into the agent's next turn.
    *   **Blocking**: Hooks print a reason to `stderr` and exit with code `2`, forcing the agent to retry or correct the action.
    *   **Telemetry**: Triggers are logged to `~/.claude/hook-triggers.jsonl` for ROI analysis.

### Key abstractions

*   **Provenance Tags**: A shared regex-based vocabulary (defined in `hooks/provenance_tags.re`) used across 5+ files to enforce evidence standards (e.g., `[SOURCE: url]`, `[DATA]`, `[A1]`).
*   **Fail-Open Pattern**: Almost all hooks wrap their logic in `trap 'exit 0' ERR` or `try/except` blocks to ensure that a hook failure never stalls the primary agent session.
*   **Session Attribution**: The pattern of using `session_id` (resolved from stdin or env) to key temporary files in `/tmp/` to distinguish between concurrent agents.
*   **Additional Context Injection**: The `hookSpecificOutput.additionalContext` JSON structure used to communicate with the Claude Code harness without blocking execution.

### Dependencies

| Package | Purpose |
| :--- | :--- |
| `jq` | Primary tool for JSON extraction in shell-based hooks. |
| `uv` | Used for fast Python execution and dependency management in overview generation. |
| `pyright` | Used in `posttool-pyright-check.sh` to detect newly introduced type errors. |
| `lsof` | Used in `sessionstart-peer-session-warn.sh` to detect concurrent sessions in the same directory. |
| `ed` | Used for atomic line insertion in `append-skill-memento.sh`. |