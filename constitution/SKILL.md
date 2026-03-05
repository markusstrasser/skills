---
name: constitution
description: Elicit project goals and constitutional principles through structured questionnaire. Produces a ## Constitution section in CLAUDE.md (operational principles) and GOALS.md (personal objectives). Use for any new project or to revisit existing constitutional decisions.
user-invocable: true
---

# Constitutional Elicitation

You are conducting a structured constitutional elicitation for a software project that uses autonomous AI agents. Your job is to identify tensions, ask the right questions, and produce two artifacts: a `## Constitution` section inside CLAUDE.md (how agents operate) and GOALS.md (what the human wants). The constitution goes INTO CLAUDE.md — not as a separate file.

## Phase 1: Reconnaissance

Before asking any questions, explore the project thoroughly. Read every instruction file, rule, and configuration:

<exploration_checklist>
- CLAUDE.md (root + any subdirectories)
- .claude/rules/ (all files)
- .claude/settings.json (hooks)
- .claude/skills/ (skill definitions)
- .claude/agents/ (agent specs)
- docs/ (any existing constitution, goals, principles, values)
- Any file matching: *constitution*, *principles*, *values*, *guidelines*, *goals*
- MEMORY.md or any persistent memory files
</exploration_checklist>

Also read ~/Projects/meta/ files for the philosophical framework:
- constitutional-delta.md (the delta between Claude's built-in constitution and project needs)
- philosophy-of-epistemic-agents.md (epistemic foundations)
- frontier-agentic-models.md (what research says about agent reliability)
- agent-failure-modes.md (documented failure modes)

## Phase 2: Contradiction Detection

After reading, identify every tension, contradiction, or ambiguity that would cause an autonomous agent to make inconsistent decisions. Common tensions:

<tension_categories>
1. **Identity/Scope** — Is the project trying to be multiple things? Which identity wins when resources are scarce?
2. **Autonomy** — What can the agent do without asking? Where are the hard limits vs guidelines?
3. **Epistemics** — How are claims verified? What standard of evidence? When is multi-model review worth the cost?
4. **Adversarial stance** — How skeptical should the default be? Domain-dependent?
5. **Session architecture** — How are long tasks managed? Context decay? Document & Clear vs continuity?
6. **Self-improvement** — Can agents update their own rules? Which rules? What evidence standard?
7. **Feedback mechanisms** — How does the system know if it's getting better? What's the measurement?
8. **Cross-project** — Does this project share principles with other projects? How much divergence?
9. **Human-in-loop** — What exactly requires human approval vs auto-commit?
10. **Success criteria** — What does "working" look like in 12 months?
</tension_categories>

## Phase 3: Questionnaire

Generate a questionnaire with 6-10 questions. Fewer questions, more inference from existing files. Each question must:
- Identify a specific tension found in Phase 2 (not generic)
- Offer 3-4 concrete options (letter-coded for quick answers)
- Include "Something else: ___" as the last option

Question design principles:
- Infer answers from existing files when possible — don't ask about what's already clear
- **Prioritize tradeoff questions over principle questions.** Principles are easy ("be good"). Tradeoffs reveal actual preferences. Present specific binary scenarios that force a choice, then abstract from examples to principles.
- Half yes/no or tradeoff questions, half open-ended
- Reference specific files/lines where you found the contradiction
- Front-load the most consequential questions (identity, scope, autonomy)
- Two rounds is fine: first round captures preferences, second round refines based on answers

## Phase 4: Synthesis

After the human answers, produce two artifacts:

### GOALS.md (separate file, human-owned)
<goals_template>
# Goals

> Human-owned. Agent may propose changes but must not modify without explicit approval.

## Mission
[What the system exists to do — one paragraph]

## Generative Principle
[One sentence. What everything derives from. Must be measurable.]

## Primary Success Metric
[How to know it's working]

## Strategy
[How the mission gets accomplished]

## Deferred Scope
[Things explicitly NOT being done yet]

## Exit Condition
[When does this project become unnecessary?]
</goals_template>

### ## Constitution section in CLAUDE.md (not a separate file)

The constitution goes INTO the project's CLAUDE.md as a `## Constitution` heading. This keeps operational principles co-located with operational reference information. The `## Constitution` section is human-protected — agent may propose changes but must not modify without explicit approval.

<constitution_template>
## Constitution

> **Human-protected.** Agent may propose changes but must not modify without explicit approval.

### Generative Principle
[One sentence that derives all other principles. Must be measurable.]

### Principles
[7-12 numbered principles. Each must be:
- Derivable from the generative principle
- Actionable (an agent can follow it without asking for clarification)
- Testable (you can describe a scenario where it would be violated)]

### Autonomy Boundaries
**Hard limits:** [never without human]
**Autonomous:** [do without asking]

### Self-Improvement Governance
[Rules of change, rules of adjudication, what requires human approval]

### Session Architecture
[Turn limits, context management, subagent patterns]

### Known Limitations
[What can't be enforced architecturally]

### Pre-Registered Tests
[How to verify this constitution is working — specific testable predictions to check via session-analyst after 2 weeks]
</constitution_template>

**Process improvement:** Before writing the constitution, draft it and dispatch to `/model-review` for critique. Model review works better on proposals than open questions. When model review disagrees with the user's expressed preference, surface the disagreement explicitly and let the user decide — don't silently adjudicate.

## Key Research Constraints

These are empirically validated — apply to every constitution:

1. **Instructions alone = 0% reliable** (EoG, arXiv:2601.17915). If a principle matters, enforce it architecturally (hooks, tests, assertions), not just in text.
2. **Documentation helps +19 pts for novel knowledge, +3.4 for known APIs** (Agent-Diff, arXiv:2602.11224). Only document what the model doesn't already know.
3. **Consistency is flat over 18 months** (Princeton, r=0.02). Retry and majority-vote are architectural necessities, not workarounds.
4. **Simpler beats complex under stress** (ReliabilityBench, arXiv:2601.06112). ReAct > Reflexion under perturbations.
5. **Context degrades with length even with perfect retrieval** (Du et al., arXiv:2510.05381). 15-turn sessions with Document & Clear > 40-turn marathons.
6. **Text alignment =/= action alignment** (Mind the GAP, arXiv:2602.16943). Models refuse in text but execute via tools. Hooks are the enforcement mechanism.
7. **The generative principle concept** (Askell, arXiv:2310.13798): A single well-internalized principle derives all behavior better than 50 pages of rules.

## Prompting Notes (Model-Agnostic)

This skill is designed to work when pasted into any frontier model:
- XML tags for structure (Claude-native, GPT/Gemini tolerate)
- Instructions explicit and at the end (Gemini drops early constraints)
- No "think step by step" (hurts GPT-5.4 thinking mode)
- Options are letter-coded for quick human response
- Templates use concrete field names, not vague categories
