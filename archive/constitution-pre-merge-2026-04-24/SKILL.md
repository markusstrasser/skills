---
name: constitution
description: Elicit project goals and constitutional principles through structured questionnaire. Produces a single expanded GOALS.md covering mission, principles, autonomy boundaries, and governance — one source of truth, not split between CLAUDE.md and GOALS.md. Use for any new project or to revisit existing constitutional decisions.
user-invocable: true
effort: medium
---

# Constitutional Elicitation

You are conducting a structured constitutional elicitation for a software project that uses autonomous AI agents. Your job is to identify tensions, ask the right questions, and produce a single consolidated `docs/GOALS.md` that covers both what the human wants (mission, success metrics, scope) and how agents operate (principles, autonomy boundaries, governance). CLAUDE.md gets a short pointer to GOALS.md, not a duplicate constitution section.

**Single-doc rationale:** Split governance (Constitution in CLAUDE.md + GOALS.md) created drift — two documents expressing the same ideas with no mechanism to keep them in sync. Rolled out as one doc across genomics + evo on 2026-04-24. New projects should start this way. Existing projects with split governance should merge (see the `/merge-constitution` playbook at the bottom of this file).

## Phase 0: Mine Steering Intelligence

Before reading any files, extract what the user has actually been correcting for. Run:
```bash
uv run python3 ~/Projects/skills/goals/scripts/steering-signals.py --days 30 --json
```

If project-scoped: add `--project <name>`. If the script is unavailable, skip to Phase 1.

This report reveals the **live system's contradictions** — not just files disagreeing with files, but the live system disagreeing with the files:
- **Corrections** — where the user said "no", "don't", "stop" to agent behavior. Each correction is evidence of a principle the constitution should encode but doesn't.
- **Redirects** — softer course corrections ("actually", "instead") that reveal preference the constitution hasn't captured.
- **`#f` feedback** — explicit ground-truth corrections the user tagged during sessions.
- **Hook signals** — blocks and warnings show where architectural enforcement is already steering behavior. The constitution should be consistent with these.
- **Topic distribution** — time/cost allocation reveals real priorities vs. stated priorities.
- **Recurring correction themes** — if "cli" and "api" keep appearing in corrections, there's a missing principle about tool selection.

Works across Claude Code, Codex, and Gemini sessions (all stored in runlogs.db).

## Phase 1: Reconnaissance

Before asking any questions, explore the project thoroughly. Read every instruction file, rule, and configuration:

<exploration_checklist>
- CLAUDE.md / AGENTS.md (root + any subdirectories; note which is the symlink target)
- docs/GOALS.md if it exists
- .claude/rules/ (all files; flag any named `constitution*` — these are legacy, will be merged)
- .claude/settings.json (hooks)
- .claude/skills/ (skill definitions)
- .claude/agents/ (agent specs)
- docs/ (any existing goals, principles, values docs)
- Any file matching: *constitution*, *principles*, *values*, *guidelines*, *goals*
- MEMORY.md or any persistent memory files
- **Phase 0 steering report** — corrections, feedback, hook signals
</exploration_checklist>

Also read ~/Projects/agent-infra/ files for the philosophical framework:
- constitutional-delta.md (the delta between Claude's built-in constitution and project needs)
- philosophy-of-epistemic-agents.md (epistemic foundations)
- frontier-agentic-models.md (what research says about agent reliability)
- agent-failure-modes.md (documented failure modes)

## Phase 2: Contradiction Detection

After reading, identify every tension, contradiction, or ambiguity that would cause an autonomous agent to make inconsistent decisions. Mine three sources of contradiction:

**A. Files vs. files** — existing contradictions within instruction surface (the original approach)
**B. Files vs. behavior** — steering report corrections that contradict stated principles. If the constitution says "be autonomous" but the user keeps correcting agent behavior, the autonomy boundary is wrong.
**C. Files vs. allocation** — stated priorities vs. where time/money actually goes. If GOALS.md says "intel is primary" but genomics gets 2x the sessions, there's a drift.

Common tensions:

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

After the human answers, produce ONE artifact: `docs/GOALS.md`. Do NOT create a separate constitution file or a `## Constitution` section in CLAUDE.md.

CLAUDE.md / AGENTS.md should contain at most a short pointer:

```markdown
## Goals & Governance

> **Human-protected.** Agent may propose changes but must not modify without explicit approval.

Canonical text lives in `docs/GOALS.md`. Covers: [1-line summary of what's in it].
```

### `docs/GOALS.md` template

<goals_template>
# Goals & Governance

> Human-owned. Agents may propose changes but must not modify without explicit approval.

## Mission
[What the system exists to do — one paragraph. State the cardinal rule if there is one.]

## Generative Principle
[One sentence. What everything derives from. Must be measurable.]

## Domain
[What the system operates on; what scale; what assumptions about input.]

## Strategy
[Numbered sections covering how the mission gets accomplished. 4-8 typical.]

## Operating Principles
[5-10 principles, each:
- Derivable from the generative principle
- Actionable (an agent can follow without asking for clarification)
- Testable (you can describe a scenario where it would be violated)

Session-level principles (action-default, no-early-stop, plan-before-architecture)
belong in CLAUDE.md, not here. These are about HOW the engine works, not how a
session works.]

## Architecture Boundary
[What the project owns vs. doesn't own. Include a diagram if the boundary is
architectural. Hard limits — data exposure, destructive actions, cross-repo
edits — go here as a subsection.]

## Success Metrics
[Ranked table of metrics, each with "Measures" and "Why it matters" columns.
Include priority order when metrics conflict.]

### Pre-Registered Tests
[6-10 falsifiable observables that measure whether the engine is getting more
trustworthy over time. Regression on any is a signal to reassess.]

## Resource Constraints
[Table of resources with status + implication. Autonomous-spend threshold goes
here.]

## Deferred Scope
[Things explicitly NOT being done yet. Link to exit conditions if applicable.]

## Governance
[Autonomous changes vs. changes requiring explicit human approval. Short.]

## Exit / Pivot Conditions
[When does this project pivot or end?]

---
*Revision log: dated entries as the doc evolves. Non-trivial revisions should
include a one-line rationale.*
</goals_template>

**Process improvement:** Before writing the final doc, draft it and dispatch to `/critique model` for critique. Model review works better on proposals than open questions. When model review disagrees with the user's expressed preference, surface the disagreement explicitly and let the user decide — don't silently adjudicate.

## Merging Legacy Split-Governance Projects

For projects that currently have BOTH a separate constitution (either `.claude/rules/constitution.md` or inline `## Constitution` section in CLAUDE.md) AND a `docs/GOALS.md`:

1. **Identify unique content in each.** Most of the constitution will already be expressed in GOALS.md under Strategy or Success Metrics. Usually only 3-6 items are genuinely unique (fail-loud-on-drift, architectural-enforcement, delete-superseded-paths, etc.).
2. **Fold uniques into GOALS.md** under the appropriate sections: new ones become an "Operating Principles" section; hard limits go under Architecture Boundary; pre-registered tests under Success Metrics; autonomy/change-control under Governance.
3. **Drop redundant content.** Mission/strategy duplicates, session-level principles (move to CLAUDE.md if not already there).
4. **Delete the standalone constitution file OR replace the `## Constitution` section in CLAUDE.md** with a short pointer.
5. **Update the auto-load table** in CLAUDE.md if the constitution was in `.claude/rules/`.
6. **Commit with evidence.** Commit message should cite the specific overlap that justified the merge.

Reference implementations: genomics (2026-04-24, commit `6a8c094f`), evo (2026-04-24, commit `5978d661`).

## Key Research Constraints

These are empirically validated — apply to every constitution:

1. **Instructions alone = 0% reliable** (EoG, arXiv:2601.17915). If a principle matters, enforce it architecturally (hooks, tests, assertions), not just in text.
2. **Documentation helps +19 pts for novel knowledge, +3.4 for known APIs** (Agent-Diff, arXiv:2602.11224). Only document what the model doesn't already know.
3. **Consistency is flat over 18 months** (Princeton, r=0.02). Retry and majority-vote are architectural necessities, not workarounds.
4. **Simpler beats complex under stress** (ReliabilityBench, arXiv:2601.06112). ReAct > Reflexion under perturbations.
5. **Context degrades with length even with perfect retrieval** (Du et al., arXiv:2510.05381). 15-turn sessions with Document & Clear > 40-turn marathons.
6. **Text alignment =/= action alignment** (Mind the GAP, arXiv:2602.16943). Models refuse in text but execute via tools. Hooks are the enforcement mechanism.
7. **The generative principle concept** (Askell, arXiv:2310.13798): A single well-internalized principle derives all behavior better than 50 pages of rules.
8. **Single-doc governance reduces drift.** Split governance documents diverge over time without a sync mechanism. Empirically observed across genomics + evo before the 2026-04-24 merge.

## Prompting Notes (Model-Agnostic)

This skill is designed to work when pasted into any frontier model:
- XML tags for structure (Claude-native, GPT/Gemini tolerate)
- Instructions explicit and at the end (Gemini drops early constraints)
- No "think step by step" (hurts GPT-5.4 thinking mode)
- Options are letter-coded for quick human response
- Templates use concrete field names, not vague categories
