# Claude Code Skills

Shared skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Used across multiple projects via a SessionStart hook or direct copy.

## Skills

| Skill | What it does |
|-------|-------------|
| `researcher` | Autonomous multi-source research with epistemic rigor. Orchestrates Exa, Brave, Perplexity, Semantic Scholar, paper-search MCPs. Effort-adaptive. |
| `epistemics` | Bio/medical/scientific evidence hierarchy. Source-grade-on-write, counterfactual generation. Companion to researcher. |
| `source-grading` | NATO Admiralty System (A-F reliability, 1-6 credibility). For OSINT, forensic, legal, entity audit work. |
| `entity-management` | Versioned knowledge files for entities (people, companies, genes, drugs). One file per entity, every claim sourced. |
| `competing-hypotheses` | Analysis of Competing Hypotheses (ACH). Multi-agent adversarial evaluation with Bayesian LLR scoring. |
| `causal-check` | Causal inference discipline. Shape-match explanations to observations, define the null, predict footprints. |
| `investigate` | Deep forensic investigation. Fraud detection, OSINT, billing audits, shell companies. Adversarial, cross-domain. |
| `model-review` | Cross-model adversarial review via llmx. Dispatches to Gemini and GPT for independent critique. |
| `model-guide` | Frontier model selection and prompting guide. Which model for which task, known pitfalls. |
| `llmx-guide` | Gotchas when calling llmx from Python or Bash. Non-obvious bugs and incompatibilities. |
| `constitution` | Elicit project goals and constitutional principles through structured questionnaire. |
| `goals` | Elicit, clarify, or revise project goals. Produces or updates GOALS.md. |
| `retro` | End-of-session retrospective. Extracts failure modes and tooling proposals. |
| `session-analyst` | Analyzes session transcripts for behavioral anti-patterns. Dispatches to Gemini for analysis. |
| `supervision-audit` | Audit sessions for wasted supervision. Outputs concrete automation fixes. |
| `project-upgrade` | Autonomous codebase improvement via Gemini structured analysis. |
| `agent-pliability` | Make project files more discoverable for agents. Renames, splits, builds indexes. |
| `debug-mcp-servers` | Debug MCP server loading issues in Claude Code. |

## Hooks

`hooks/` contains shared hooks for Claude Code — bash loop guards, search burst detection, source attribution checks, epistemic gates, session logging. Referenced by absolute path from each project's `settings.json`.

## Usage

Projects pull skills via a SessionStart hook that clones this repo and copies relevant skill directories into `.claude/skills/`. See any project's `session-pull.sh` for the pattern.

```bash
# Manual: copy specific skills into your project
cp -r ~/Projects/skills/researcher /your-project/.claude/skills/researcher
```

## Archive

`archive/` contains superseded skill versions.
