<!-- INDEX
- SKILLS
- HOOKS
- INFRASTRUCTURE PATTERNS
-->

### SKILLS

This library provides structured reasoning frameworks as "skills" for an AI agent. Each skill is a self-contained methodology for a specific type of task.

- **agent-pliability**: Makes a project's files more discoverable for agents by splitting monoliths and improving names.
- **architect (archive)**: Guides architectural decisions using a tournament-based proposal generation and ranking workflow.
- **causal-check**: Enforces causal inference discipline for "why" questions, matching explanation shape to observation shape.
- **causal-dag**: Mandates Directed Acyclic Graph (DAG) construction and validation before regression model specification.
- **causal-robustness**: Performs post-estimation sensitivity analysis to quantify robustness to unmeasured confounding.
- **competing-hypotheses**: Formalizes the Analysis of Competing Hypotheses (ACH) to evaluate multiple explanations for a claim.
- **constitution**: Elicits project goals and operational principles for agents via a structured questionnaire.
- **debug-mcp-servers**: Provides a systematic process for debugging why MCP (tool) servers are not loading.
- **entity-management**: Implements version-controlled knowledge management for entities (people, companies, genes).
- **epistemics**: Defines a bio/medical/scientific evidence hierarchy and provides anti-hallucination rules.
- **goals**: Elicits, clarifies, or revises project goals, producing or updating a `GOALS.md` file.
- **google-workspace**: Automates Google Workspace tasks (Drive, Sheets, Gmail) via the `gws` CLI wrapper.
- **investigate**: Defines a deep forensic investigation methodology for datasets, entities, or systems.
- **llmx-guide**: Serves as a quick reference for gotchas and best practices when using the `llmx` unified LLM CLI.
- **model-guide**: Provides a selection guide and prompting best practices for frontier AI models (Claude, GPT, Gemini, Kimi).
- **model-review**: Orchestrates cross-model adversarial review of code or decisions using `llmx`.
- **project-upgrade**: Defines a workflow for autonomous codebase improvement using large-context model analysis.
- **researcher**: Implements an autonomous research agent that orchestrates various search tools with epistemic rigor.
- **retro**: Guides a structured end-of-session retrospective to identify failures and propose automated fixes.
- **session-analyst**: Analyzes session transcripts to identify and report on behavioral anti-patterns.
- **source-grading**: Implements the NATO Admiralty System for grading source reliability and information credibility.
- **supervision-audit**: Audits session transcripts for "wasted supervision" to identify automation opportunities.

### HOOKS

Hooks provide autonomous guardrails, automation, and quality control throughout the agent's lifecycle. They are typically small shell scripts that delegate complex logic to Python helpers.

**Pre-Tool Hooks (Prevention & Guidance)**
- `pretool-bash-loop-guard.sh`: **PreToolUse:Bash**: Blocks malformed multiline bash loops to prevent common zsh parse errors.
- `pretool-commit-check.sh`: **PreToolUse:Bash**: Checks `git commit` messages against formatting rules and blocks Co-Authored-By tags.
- `pretool-consensus-search.sh`: **PreToolUse (Search)**: Warns against "consensus queries" (e.g., "best X") that produce noise, not signal.
- `pretool-data-guard.sh`: **PreToolUse:Write/Edit**: Blocks any attempt to modify protected data files (e.g., datasets, `.parquet`).
- `pretool-regression-dag-gate.sh`: **PreToolUse:Write/Edit**: Reminds agent to use `/causal-dag` when writing regression code without explicit DAG thinking.
- `pretool-search-burst.sh`: **PreToolUse (Search)**: Warns and eventually blocks rapid, consecutive search queries without consuming results.
- `pretool-source-remind.sh`: **PreToolUse:Write/Edit**: Reminds the agent to add provenance tags *before* writing to a research-related file.
- `pretool-subagent-gate.sh`: **PreToolUse:Agent**: Issues advisory warnings for suboptimal subagent spawning patterns (e.g., using a subagent for a single tool call).

**Post-Tool Hooks (Correction, Formatting & Logging)**
- `posttool-bash-failure-loop.sh`: **PostToolUse:Bash**: Detects consecutive command failures and provides targeted correction advice.
- `posttool-failure-log.sh`: **PostToolUseFailure**: Logs all tool failures across all tools with a structured error classification.
- `posttool-research-reformat.sh`: **PostToolUse (Research MCPs)**: Intercepts and reformats noisy search/paper tool outputs into a clean, structured format.
- `posttool-review-check.sh`: **PostToolUse:Bash**: Detects `llmx` errors during model reviews and warns that the review is single-model only.
- `posttool-verify-before-expand.sh`: **PostToolUse:Write/Bash**: Warns if writing a new script before a previously written one has been executed.
- `postwrite-frontier-timeliness.sh`: **PostToolUse:Write/Edit**: Warns if research files cite pre-frontier models without a staleness disclaimer.
- `postwrite-source-check.sh`: **PostToolUse:Write/Edit**: Validates the structure, density, and content of provenance tags in research files.
- `postwrite-source-check-semantic.sh`: **PostToolUse:Write/Edit**: Uses a lightweight LLM (Haiku) to semantically check for unsourced claims in research files.

**Session Lifecycle Hooks (Automation & State Management)**
- `precompact-log.sh`: **PreCompact**: Creates a `checkpoint.md` with git status and session state before context compaction.
- `sessionend-index-sessions.sh`: **SessionEnd**: Asynchronously triggers an update to the session search index.
- `sessionend-log.sh`: **SessionEnd**: Logs a final "flight receipt" for the session, including cost, duration, and model used.
- `sessionend-overview-trigger.sh`: **SessionEnd**: Triggers regeneration of project overviews if significant code changes were detected.
- `postmerge-overview.sh`: **post-merge (git)**: Triggers background regeneration of project overviews after a `git pull` or `git merge`.
- `overview-staleness-cron.sh`: **Cron**: Periodically checks for and regenerates stale project overviews.

**Stop Hooks (Final Quality Gates)**
- `stop-research-gate.sh`: **Stop**: Blocks session termination if modified research files are missing provenance tags.
- `stop-uncommitted-warn.sh`: **Stop**: Blocks session termination if there are uncommitted changes, reminding the agent to commit.
- `stop-verify-plan.sh`: **Stop**: Blocks session termination if a plan's ````verify```` block contains failing acceptance criteria.

**Subagent Hooks (Sub-Task Oversight)**
- `subagent-start-log.sh`: **SubagentStart**: Logs every subagent spawn event for later analysis.
- `subagent-epistemic-gate.sh`: **SubagentStop**: Checks subagent output for factual claims that lack provenance tags.
- `subagent-source-check-stop.sh`: **SubagentStop**: Specifically checks `researcher` subagent output for source citations.

**User Interaction Hooks**
- `permission-auto-allow.sh`: **PermissionRequest**: Automatically approves requests for known-safe, read-only tools to reduce prompt fatigue.
- `userprompt-context-warn.sh`: **UserPromptSubmit**: Detects when a user pastes "continuation" boilerplate and informs them that `checkpoint.md` makes it unnecessary.

**Utility Scripts (not hooks)**
- `add-mcp.sh`: Helper script to add predefined MCP server configurations to a project.
- `generate-overview.sh`: Core script for generating codebase overviews, used by several hooks.
- `generate-overview-batch.sh`: A more advanced overview generator that uses the Gemini Batch API for cost savings.
- `hook-trigger-log.sh`: A centralized logger called by other hooks to record their activations for analysis.

### INFRASTRUCTURE PATTERNS

- **Skills as Reasoning Frameworks**: Skills are primarily markdown files that provide structured methodologies (`causal-check`, `competing-hypotheses`). They guide the agent's thinking process, promoting rigor and consistency.

- **Hooks as Architectural Guardrails**: The `hooks/` directory forms the core of the agent's autonomous operation, enforcing rules that are difficult to capture in prompts alone. Hooks are categorized by their trigger point in the agent's lifecycle (Pre-Tool, Post-Tool, Stop, SessionEnd).

- **Python Helpers for Complex Logic**: Shell hooks act as simple, robust dispatchers, delegating complex tasks like JSON parsing (`commit-check-parse.py`) or rule validation (`source-check-validator.py`) to focused Python scripts.

- **State Management via Filesystem**: Hooks maintain state across tool calls using files, typically in `/tmp` for session-specific state (e.g., `claude-search-burst-$PPID`) and `~/.claude/` for persistent logs.

- **Unified External Tooling**: The ecosystem relies on standardized CLIs like `llmx` for multi-model LLM access and `repomix` for codebase context gathering, ensuring consistent behavior across skills.

- **Epistemic Rigor as a System Property**: A central theme is enforcing evidence-based reasoning. This is implemented through skills (`epistemics`, `source-grading`) and enforced by hooks (`postwrite-source-check.sh`, `subagent-epistemic-gate.sh`), making it an architectural feature, not just an instruction.

- **Recursive Self-Improvement Loop**: A meta-pattern where specific skills (`retro`, `session-analyst`, `supervision-audit`) analyze agent behavior to propose new hooks, rules, and automations, creating a feedback loop for continuous improvement.

- **Automated Codebase Summarization**: A dedicated set of scripts and hooks (`generate-overview.sh`, `sessionend-overview-trigger.sh`, `postmerge-overview.sh`) automatically maintains high-level overviews of the project's source code and tooling. This keeps the agent's context fresh without manual intervention.
