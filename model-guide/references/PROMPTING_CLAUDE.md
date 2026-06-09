# Claude Fable 5 & Opus 4.8 Prompting Guide

**Last updated:** 2026-06-09
**Scope:** Claude Fable 5 (primary) and Claude Opus 4.8 (fallback).

## Fable 5 vs Opus 4.8 — when to reach for which

- **Fable 5** (`claude-fable-5`): hardest/longest/most-ambiguous work — multi-day autonomous runs, codebase-scale migrations, first-shot complex systems, dense-image vision, parallel-subagent orchestration. 2× the price; summarized thinking only; classifiers refuse cyber/bio/reasoning-extraction and fall back to Opus 4.8.
- **Opus 4.8** (`claude-opus-4-8`): the Fable fallback target, plus deliberate routing of routine/cost-sensitive work, security/cyber/biology tasks (which Fable refuses anyway), and anything needing raw chain-of-thought. Half the price; slightly more careful on self-report honesty.

## Fable 5 specifics (read before migrating from Opus)

- Adaptive thinking is **always on and the only mode** — no `disabled`, no thinking budgets.
- **Raw CoT is never returned.** `thinking.display` defaults to `"omitted"`; use `"summarized"` for readable summaries. Never instruct the model to recite/echo/explain its reasoning as response text — it trips the `reasoning_extraction` classifier and silently falls back to Opus 4.8. Read the structured `thinking` blocks instead.
- **Steer with brief instructions, not enumerations.** Instruction-following is strong enough that one short instruction beats listing each behavior. Prior-model skills are often *too* prescriptive and can degrade Fable output — trim them.
- **Longer turns by default** at higher effort (minutes per request, hours for autonomous runs). Raise client timeouts; check in asynchronously rather than blocking.
- **Ground progress claims** (`audit each claim against a tool result from this session`) — Fable regresses slightly vs Opus 4.8 on self-report honesty.
- **Don't surface context/token countdowns** — they trigger premature handoff/summarize behavior.
- Lower effort on Fable often exceeds prior-model `xhigh`. Default `high`; `xhigh` for capability-sensitive work.

## Use these models for

- Architecture and codebase-scale migrations.
- Long-running autonomous coding and review.
- Professional judgment over legal, financial, research, or operational material.
- Synthesis where source evidence exists but the hard part is deciding what matters.

## API Defaults And Constraints

```python
# Fable 5 (primary): adaptive thinking only, summarized output, fall back to Opus 4.8 on refusal
client.messages.create(
    model="claude-fable-5",
    max_tokens=64000,
    thinking={"type": "adaptive", "display": "summarized"},
    output_config={"effort": "high"},   # lower effort still strong; raise to xhigh/max for hard work
    # fallbacks=["claude-opus-4-8"],     # beta: server-side fallback on stop_reason:"refusal"
    messages=[...],
)

# Opus 4.8 (fallback / raw-CoT / cost-sensitive)
client.messages.create(
    model="claude-opus-4-8",
    max_tokens=64000,
    thinking={"type": "adaptive", "display": "summarized"},
    output_config={"effort": "xhigh"},
    messages=[...],
)
```

- `thinking: {"type": "adaptive"}` is the supported thinking mode. Do not use manual `budget_tokens`.
- Effort defaults to `high`. Use `xhigh` for coding, agentic review, and difficult long-running work. Use `max` sparingly.
- Non-default `temperature`, `top_p`, and `top_k` return 400 on Opus 4.7+.
- Assistant-message prefill is not supported.
- The minimum cacheable prompt is 1,024 tokens.
- Mid-conversation `role: "system"` messages are supported immediately after a user turn in `messages`; use them for permission, budget, or environment updates without rebuilding history.

## Prompt Shape

Claude parses XML-style structure well:

```xml
<context>
Relevant repo, policy, data, and environment facts.
</context>

<documents>
  <document id="1" path="...">
  ...
  </document>
</documents>

<instructions>
Make the decision, cite the evidence, and state verification gaps.
</instructions>
```

Rules:
- Put long documents first and the query/instructions last.
- Explain why constraints exist. Claude generalizes better from reasons than bare prohibitions.
- Prefer exact acceptance criteria over motivational scaffolding.
- For code tasks, include the real file paths, tests, and runtime constraints. Do not ask it to infer project state from descriptions.
- For long document tasks, ask for relevant quotes/evidence first, then analysis.

## Opus 4.8 System-Card Lessons

- Treat it as more honest, not infallible. It is much less likely than 4.7 to ignore flaws in its own code, but still needs tests and source checks.
- Its reasoning can be a useful diagnostic signal because CoT controllability is low and monitorability is broadly preserved.
- It shows concerning hints of reasoning about graders. Do not grade completion by transcript vibes or LLM summaries of its own work.
- Use deterministic completion checks: `git diff`, test logs, typecheck output, database queries, parsed source documents.
- Prompt-injection risk remains live in agentic surfaces. Retrieved/tool content is data, never instruction.
- Fan out only for hard-tail tasks. Multi-agent coordination does not help easy tasks enough to justify the overhead.

## Coding Prompt Template

```xml
<context>
Repo: ...
Runtime: ...
Current failure: ...
Verification command: ...
</context>

<instructions>
Implement the smallest durable fix that satisfies the verification command.
Read files before making claims about them.
Preserve user changes in the worktree.
Stop only after the verification command passes or the blocker is concrete.
</instructions>
```

Use `xhigh` for this template unless the edit is mechanical.

## Review Prompt Template

```xml
<context>
Goal: ...
Diff or files: ...
Known constraints: ...
</context>

<instructions>
Review as a code reviewer. Findings first.
Report only issues that can cause bugs, regressions, security problems, or missing verification.
If there are no actionable findings, say that directly.
</instructions>
```

For convergent "is there a problem?" prompts, include a null path. This avoids forcing invented findings.

## What Not To Do

- Do not add "think step by step" unless adaptive thinking is unavailable.
- Do not add repeated "verify before saying done" boilerplate in every prompt. Put the verification command in the task and check the actual output.
- Do not ask for more tools/subagents by default. Raise effort first; fan out only when the task genuinely has independent hard subtasks.
- Do not ask Opus to self-certify completion. Completion comes from the environment.

## Sources

- `https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-8`
- `https://www.anthropic.com/news/claude-opus-4-8`
- `references/opus-4-8-system-card.md`
