---
name: goals
description: Elicit or revise project goals and operating principles into docs/GOALS.md (mission, strategy, metrics, autonomy boundaries). Use when starting a project, pivoting strategy, or governance feels unclear.
user-invocable: true
disable-model-invocation: true
effort: medium
---

# Goals & Governance Elicitation

You are helping the human clarify what they want from this project (goals: WHAT to optimize for) AND how agents should operate within it (governance: HOW to behave). Both dimensions go into a single `docs/GOALS.md`. CLAUDE.md / AGENTS.md gets at most a short pointer.

**Why one doc:** Two governance documents expressing related ideas with no sync mechanism diverge over time. One source of truth wins.

## Modes

Invoke as `/goals [mode] [topic]`. Mode is optional.

| Mode | When | Emphasis |
|------|------|----------|
| (default) | New project, or comprehensive revision | Full coverage: mission, strategy, metrics, principles, autonomy, governance |
| `mission` | "Let's rethink what we're doing" | WHAT-side: mission, success metrics, deferred scope, exit conditions |
| `principles` | "Let's rethink how agents behave here" | HOW-side: operating principles, autonomy boundaries, pre-registered tests, governance |
| `revise` | Existing GOALS.md, targeted update | Compare stated vs actual, ask only about drift |

Modes are emphasis filters, not different outputs. Skip irrelevant questions; the output template is unified.

## When to Use

- New project without a GOALS.md
- Existing project where strategy or operating principles have drifted
- After a significant pivot, new capability, or repeated agent corrections that suggest a missing principle
- When the human says "I'm not sure what I'm optimizing for", "let's refocus", or "agents keep doing X and I have to correct it"

## Phase 0: Mine Steering Intelligence

Before reading any files, extract what the user has actually been correcting for. Run:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/steering-signals.py --days 30 --project <current_project> --json
```

If the script is unavailable, fall back to `git log --oneline -30` — but the steering report is far richer.

The report reveals the **live system's contradictions** — not just files disagreeing with files, but the live system disagreeing with the files:

- **Explicit feedback** (`#f` tags) — ground-truth corrections the user made during sessions
- **Corrections** — "no", "don't", "stop", "wrong" — agent behavior the user pushed back on. Each correction is evidence of a missing principle.
- **Redirects** — "actually", "instead", "let's not" — softer course corrections that reveal preference GOALS.md hasn't captured.
- **Recurring themes** — what words keep appearing in corrections (these are the real priorities)
- **Topic distribution** — time and cost allocation across projects (revealed preferences)
- **Hook signals** — systematic blocks/warnings (architectural steering already in place)
- **Cost allocation** — where money actually goes vs. where GOALS.md says it should

The corrections ARE the goals — or at least, the delta between stated goals and real ones. Every correction is the user steering the system toward what they actually want.

Works across Claude Code, Codex, and Gemini sessions (all indexed in `~/.claude/agentlogs.db`; query via `uv run agentlogs`).

## Phase 1: Reconnaissance

Read everything that reveals intent — both human-side and agent-side:

<exploration_checklist>
- `docs/GOALS.md` (if exists — this is a revision, not creation)
- CLAUDE.md / AGENTS.md (note which is the symlink target)
- `.claude/rules/` (all files — domain-specific rules, not governance)
- `.claude/settings.json` (hooks — these are architectural enforcement)
- `.claude/skills/` and `.claude/agents/` (operational extensions)
- README, docs/, project description
- MEMORY.md or persistent memory (prior decisions, prior elicitation results)
- Recent git log (what has the human actually been working on?)
- `$HOME/Projects/agent-infra/memory/MEMORY.md` (cross-project decisions)
- **Phase 0 steering report** (corrections, feedback, topic drift, cost allocation)
</exploration_checklist>

For documented agent failure modes, read `~/Projects/agent-infra/agent-failure-modes.md`.

Pay attention to the gap between stated and revealed: if GOALS.md says "X is primary" but the last 20 commits / recent corrections target Y, that gap matters more than either statement alone.

## Phase 2: Tension Detection

Identify every tension, contradiction, or ambiguity that would cause an autonomous agent to make inconsistent decisions. Mine three sources:

**A. Files vs. files** — contradictions within the existing instruction surface.
**B. Files vs. behavior** — steering-report corrections that contradict stated principles. If GOALS.md says "be autonomous" but the user keeps correcting agent behavior, the autonomy boundary is wrong.
**C. Files vs. allocation** — stated priorities vs. where time/money actually goes.

Common tensions across both dimensions:

<tension_categories>
**Goals-side (WHAT):**
1. **Identity/Scope** — Is the project trying to be multiple things? Which identity wins when resources are scarce?
2. **Success criteria** — What does "working" look like in 12 months? What's measurable?
3. **Time horizon** — When should metrics show results?
4. **Resource allocation** — What's actually scarce? Where does compute / attention go?
5. **Deferred scope** — What is explicitly NOT being done? Is the boundary holding?
6. **Exit/pivot** — Under what circumstances does this change radically or end?

**Governance-side (HOW):**
7. **Autonomy** — What can the agent do without asking? Where are the hard limits?
8. **Epistemics** — How are claims verified? What standard of evidence?
9. **Adversarial stance** — How skeptical is the default? Domain-dependent?
10. **Self-improvement** — Can agents update their own rules? Which rules? What evidence standard?
11. **Feedback mechanisms** — How does the system know if it's getting better?
12. **Cross-project** — Does this project share principles with siblings? How much divergence?
13. **Human-in-loop** — What requires human approval vs auto-commit?
</tension_categories>

In `mission` mode, focus questionnaire on tensions 1-6. In `principles` mode, focus on 7-13. In default / revise modes, cover whatever the steering report and reconnaissance flag as actually-contested.

## Phase 3: Questionnaire

Generate 6-12 questions targeting the ambiguous tensions. **Fewer questions, more inference from existing files.** Each question must:

- Identify a specific tension found in Phase 2 (not generic)
- Offer 3-4 concrete options (letter-coded for quick answers)
- Include "Something else: ___" as last option

Question design principles:

- Infer from existing files when possible — don't ask about what's already clear
- **Prioritize tradeoff questions over principle questions.** Principles are easy ("be good"). Tradeoffs reveal actual preferences. Present specific binary scenarios that force a choice, then abstract from examples to principles.
- Reference specific files/lines where you found the contradiction
- Front-load the most consequential questions (identity → autonomy → metrics)
- Two rounds is fine: first round captures preferences, second round refines based on answers
- For revision mode: focus on what changed, not what's stable

## Phase 4: Synthesis

Produce ONE artifact: `docs/GOALS.md` (or `GOALS.md` at root if there's no `docs/`). Do NOT create a separate constitution file or a `## Constitution` section in CLAUDE.md.

CLAUDE.md / AGENTS.md should contain at most a short pointer:

```markdown
## Goals & Governance

> **Human-protected.** Agent may propose changes but must not modify without explicit approval.

Canonical text lives in `docs/GOALS.md`. Covers: [1-line summary].
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

Session-level operating principles (action-default, no-early-stop, plan-before-architecture) belong in CLAUDE.md, not here. These are about HOW the engine works, not how a session works.]

## Architecture Boundary
[What the project owns vs. doesn't own. Include a diagram if the boundary is architectural. Hard limits — data exposure, destructive actions, cross-repo edits — go here as a subsection.]

## Success Metrics
[Ranked table of metrics, each with "Measures" and "Why it matters" columns. Include priority order when metrics conflict.]

### Pre-Registered Tests
[6-10 falsifiable observables that measure whether the engine is getting more trustworthy over time. Regression on any is a signal to reassess.]

## Time Horizon
[When should metrics show results? Near term / ongoing / when-X-arrives.]

## Resource Constraints
[Table of resources with status + implication. Autonomous-spend threshold goes here.]

## Deferred Scope
[Things explicitly NOT being done yet. Link to exit conditions if applicable.]

## Secondary Artifacts
[What else does the infrastructure enable, even if it's not the primary goal? Optional section.]

## Governance
[Autonomous changes vs. changes requiring explicit human approval. Short.]

## Exit / Pivot Conditions
[When does this project pivot or end?]

---
*Revision log: dated entries. Non-trivial revisions should include a one-line rationale.*
</goals_template>

Mark the file as human-owned: agent may propose changes but must not modify without explicit approval.

**Process improvement:** Before writing the final doc, draft it and dispatch to `/critique model` for critique. Model review works better on proposals than open questions. When model review disagrees with the user's expressed preference, surface the disagreement explicitly and let the user decide — don't silently adjudicate.

## Revision Mode

When `docs/GOALS.md` already exists:

1. Read it fully
2. Compare stated content against recent activity (steering report, git log, entity files, analysis output)
3. Identify drift: where reality diverged from the plan
4. Ask targeted questions about the drift only (not the whole questionnaire)
5. Update only the sections that changed
6. Add a dated entry to the revision log explaining what changed and why

## Cross-Project Awareness

If `$HOME/Projects/agent-infra/memory/MEMORY.md` exists, read it for cross-project decisions. Goals in one project may constrain goals in another:

- Shared entity graph means shared data investments
- Shared epistemics means compatible evidence standards
- Time/attention is zero-sum across projects

Surface these constraints when relevant. "You allocated X to intel and Y to genomics — is that still the right split?"

## Key Research Constraints

Empirically validated — apply to every elicitation:

1. **Instructions alone = 0% reliable** (EoG, arXiv:2601.17915). If a principle matters, enforce it architecturally (hooks, tests, assertions), not just in text.
2. **Documentation helps +19 pts for novel knowledge, +3.4 for known APIs** (Agent-Diff, arXiv:2602.11224). Only document what the model doesn't already know.
3. **Consistency is flat over 18 months** (Princeton, r=0.02). Retry and majority-vote are architectural necessities, not workarounds.
4. **Simpler beats complex under stress** (ReliabilityBench, arXiv:2601.06112). ReAct > Reflexion under perturbations.
5. **Context degrades with length even with perfect retrieval** (Du et al., arXiv:2510.05381). 15-turn sessions with Document & Clear > 40-turn marathons.
6. **Text alignment =/= action alignment** (Mind the GAP, arXiv:2602.16943). Models refuse in text but execute via tools. Hooks are the enforcement mechanism.
7. **The generative principle concept** (Askell, arXiv:2310.13798): A single well-internalized principle derives all behavior better than 50 pages of rules.
8. **Single-doc governance reduces drift.** Split governance documents diverge over time without a sync mechanism. Empirically observed across genomics + evo before the 2026-04-24 merge.

## Prompting Notes (Model-Agnostic)

Designed to work when pasted into any frontier model:

- XML tags for structure (Claude-native, GPT/Gemini tolerate)
- Instructions explicit and at the end (Gemini drops early constraints)
- No "think step by step" (hurts GPT-5.4 thinking mode)
- Options are letter-coded for quick human response
- Templates use concrete field names, not vague categories
