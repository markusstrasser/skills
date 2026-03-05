# Agent Skills

Shared skills following the [Agent Skills open standard](https://github.com/anthropics/agent-skills). Compatible with Claude Code, OpenAI Codex, and Gemini CLI.

## Cross-Tool Discovery

All three tools discover skills via user-level symlinks pointing here:

| Tool | Discovery path | Status |
|------|---------------|--------|
| Claude Code | `~/.claude/skills/` or per-project `.claude/skills/` | Per-project symlinks (selective) |
| OpenAI Codex | `~/.agents/skills/` or per-project `.agents/skills/` | `~/.agents/skills → ~/Projects/skills` |
| Gemini CLI | `~/.gemini/skills/` or `~/.agents/skills/` | `~/.gemini/skills → ~/Projects/skills` |

## Skills

| Skill | What it does | Portability |
|-------|-------------|-------------|
| `causal-check` | Causal inference discipline. Shape-match explanations to observations, define the null. | Portable |
| `constitution` | Elicit project goals and constitutional principles through structured questionnaire. | Portable |
| `epistemics` | Bio/medical/scientific evidence hierarchy and anti-hallucination rules. | Portable |
| `source-grading` | NATO Admiralty System (A-F reliability, 1-6 credibility). For OSINT, forensic, legal work. | Portable |
| `goals` | Elicit, clarify, or revise project goals. Produces or updates GOALS.md. | Portable |
| `investigate` | Deep forensic investigation. Fraud detection, OSINT, billing audits. Adversarial, cross-domain. | Portable |
| `competing-hypotheses` | Analysis of Competing Hypotheses (ACH). Bayesian LLR scoring. | Mostly portable |
| `entity-management` | Versioned knowledge files for entities (people, companies, genes, drugs). | Mostly portable |
| `model-guide` | Frontier model selection and prompting guide. Which model for which task, known pitfalls. | Mostly portable |
| `retro` | End-of-session retrospective. Extracts failure modes and tooling proposals. | Mostly portable |
| `supervision-audit` | Audit sessions for wasted supervision. Outputs concrete automation fixes. | Mostly portable |
| `agent-pliability` | Make project files more discoverable for agents. Renames, splits, builds indexes. | Mostly portable |
| `llmx-guide` | Gotchas when calling llmx from Python or Bash. Non-obvious bugs and incompatibilities. | Mostly portable |
| `model-review` | Cross-model adversarial review via llmx. Dispatches to Gemini and GPT for critique. | Claude-heavy |
| `researcher` | Autonomous multi-source research. Orchestrates Exa, Brave, Perplexity, Semantic Scholar. | Claude-heavy |
| `session-analyst` | Analyzes session transcripts for behavioral anti-patterns. Dispatches to Gemini. | Claude-heavy |
| `project-upgrade` | Autonomous codebase improvement via Gemini structured analysis. | Claude-heavy |
| `debug-mcp-servers` | Debug MCP server loading issues in Claude Code. | Claude-only |

## Hooks

`hooks/` contains shared hooks for Claude Code — bash loop guards, search burst detection, source attribution checks, epistemic gates, session logging. Referenced by absolute path from each project's `settings.json`.

## Portability Notes

- **Portable**: Pure reasoning frameworks — work identically in any agent.
- **Mostly portable**: Reference Claude Code tool names (Bash, Grep, Glob, etc.) but core logic is prose. Other agents can follow the instructions even if tool names differ.
- **Claude-heavy**: Deep tool routing, embedded hooks, MCP orchestration. Need per-tool variants for full functionality elsewhere.
- **Claude-only**: Entirely dependent on Claude Code internals.

## Usage

Skills are discovered automatically via the symlinks above. For per-project selection in Claude Code, symlink individual skills:

```bash
ln -s ~/Projects/skills/researcher /your-project/.claude/skills/researcher
```

## Archive

`archive/` contains superseded skill versions.
