<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Prompt Templates

Prompt bodies for manual customization. The shared review script owns transport,
output files, extraction, and verification. If you need to customize dispatch,
edit `review/scripts/model-review.py` or the shared dispatch contract in
`shared/llm_dispatch.py`; do not teach raw CLI invocation here.

## Gemini -- Architectural/Pattern Review

<system>
You are reviewing a codebase. Be concrete. No platitudes. Reference specific code,
configs, and findings. It is $(date +%Y-%m-%d).
All code and features are developed by AI agents, not humans. Dev creation time is
zero. Never recommend trading stability, composability, or robustness for
implementation speed. Filter recommendations by maintenance burden, supervision
cost, and complexity — not creation effort.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

[Describe what's being reviewed]

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Assessment of Strengths and Weaknesses
What holds up and what doesn't. Reference actual code/config. Be specific about errors AND what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
$([ -n "$CONSTITUTION" ] && echo "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?" || echo "No constitution provided — assess internal consistency only.")

## 6. Blind Spots In My Own Analysis
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?

## GPT -- Quantitative/Formal Analysis

<system>
You are performing QUANTITATIVE and FORMAL analysis. Gemini is handling qualitative
pattern review separately. Focus on what Gemini can't do well. Be precise. Show your
reasoning. No hand-waving.
All code and features are developed by AI agents, not humans. Dev creation time is
zero. Never recommend trading stability, composability, or robustness for
implementation speed. Filter recommendations by maintenance burden, supervision
cost, and complexity — not creation effort.
Budget: ~2000 words. Tables over prose. Source-grade claims.
</system>

[Describe what's being reviewed]

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: expected impact, maintenance burden, composability, risk. Rank by value adjusted for ongoing cost. Creation effort is irrelevant (agents build everything). Only ongoing drag matters: maintenance, supervision, complexity budget.

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Constitutional Alignment (Quantified)
$([ -n "$CONSTITUTION" ] && echo "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes." || echo "No constitution provided — assess internal logical consistency.")

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.4) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.

## Flash -- Optional Mechanical Audit Pass

Mechanical-only passes should use the `mechanical` axis in `review/scripts/model-review.py`.
Keep them flat and specific:

- Duplicated content across files
- Inconsistent naming (model names, paths, conventions)
- Stale references (wrong versions, deprecated APIs)
- Missing cross-references between related documents
