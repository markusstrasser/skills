---
name: goals
description: Elicit, clarify, or revise project goals through structured questioning. Produces or updates GOALS.md — the human's personal objectives, strategy, success metrics, and deployment philosophy. Separate from constitution (operational principles). Use when starting a new project, pivoting strategy, or when goals feel unclear.
user-invocable: true
disable-model-invocation: true
---

# Goals Elicitation

You are helping the human clarify what they actually want from this project. Goals are personal — they define WHAT to optimize for. They are distinct from the constitution (HOW agents operate).

## When to Use

- New project without a GOALS.md
- Existing project where strategy has drifted or goals feel stale
- After a significant pivot or new capability
- When the human says things like "I'm not sure what I'm optimizing for" or "let's refocus"

## Phase 1: Understand Current State

<exploration>
Read everything that reveals intent:
- GOALS.md (if it exists — this is a revision, not creation)
- CONSTITUTION.md or docs/CONSTITUTION.md (for the generative principle and operational context)
- CLAUDE.md (stated purpose, project description)
- MEMORY.md or persistent memory (prior decisions, constitutional questionnaire results)
- Any README, docs/, or project description files
- Recent git log (what has the human actually been working on vs. what they say they want?)
- ~/Projects/meta/memory/MEMORY.md (cross-project decisions if they exist)
</exploration>

Pay attention to the gap between stated goals and revealed preferences. If GOALS.md says "investment research" but the last 20 commits are fraud investigation, that's a tension worth surfacing.

## Phase 2: Goal Decomposition

Every project goal has these layers. Identify which are clear and which are ambiguous:

<goal_layers>
1. **Mission** — Why does this project exist? One sentence.
2. **Domain** — What specific slice of the world does it operate in? (market cap range, geography, sector, organism, condition)
3. **Strategy** — How does the mission get accomplished? (alpha strategies, research methods, data pipeline)
4. **Success metrics** — How do you know it's working? Must be measurable. (returns, Brier score, entity count, prediction accuracy)
5. **Time horizon** — When should these metrics show results? (3 months, 12 months, 3 years)
6. **Resource constraints** — Budget, time, compute, attention. What's scarce?
7. **Deployment philosophy** — How do decisions become actions? (manual, semi-auto, fully autonomous, outbox pattern)
8. **Deferred scope** — What is explicitly NOT being done yet? (prevents scope creep)
9. **Secondary capabilities** — What else does the infrastructure enable, even if it's not the primary goal?
10. **Exit/pivot conditions** — Under what circumstances would the human abandon or radically change this project?
</goal_layers>

## Phase 3: Questionnaire

Generate 8-12 questions targeting the ambiguous layers. Only ask about what's unclear — skip layers that are already well-defined.

Question design:
- Start with the most consequential ambiguity (mission > domain > strategy > metrics)
- Offer 3-4 concrete options, letter-coded
- Include "Something else: ___" as last option
- Reference specific things you found in Phase 1 ("Your GOALS.md says X but your recent work is Y — which is the real priority?")
- For revision sessions: focus on what changed, not what's stable

## Phase 4: Produce GOALS.md

After the human answers, write or update `docs/GOALS.md` (or `GOALS.md` at root if no docs/ directory). Use the project's existing GOALS.md as the template — it's the living document. Cover at minimum: primary mission, target domain, strategy, success metrics with time horizon, resource constraints, deployment philosophy, deferred scope, exit conditions.

Mark the file as human-owned: agent may propose changes but must not modify without explicit approval.

## Revision Mode (primary use case)

When GOALS.md already exists:
1. Read it fully
2. Compare stated goals against recent activity (git log, entity files, analysis output)
3. Identify drift: where reality diverged from the plan
4. Ask targeted questions about the drift (not the whole questionnaire again)
5. Update only the sections that changed
6. Note what was revised and why at the bottom of the commit message

## Cross-Project Awareness

If ~/Projects/meta/memory/MEMORY.md exists, read it for cross-project decisions. Goals in one project may constrain goals in another:
- Shared entity graph means shared data investments
- Shared epistemics means compatible evidence standards
- Time/attention is zero-sum across projects

Surface these constraints when relevant. "You allocated X to intel and Y to selve — is that still the right split?"
