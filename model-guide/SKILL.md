---
name: model-guide
description: Frontier model selection and prompting for Claude Fable 5, Claude Opus 4.8 (fallback), GPT-5.5, and GPT-5.5 Pro.
user-invocable: true
argument-hint: '[task description or model name]'
effort: low
---

# Model Guide

Select between the current frontier models and prompt them correctly.

**Models covered:** Claude Fable 5, Claude Opus 4.8 (fallback), GPT-5.5, GPT-5.5 Pro.
**Last updated:** 2026-06-09.
**Active stance:** This skill no longer maintains a broad model zoo. Older GPT, Gemini, Grok, and Sonnet routes were removed from active guidance. Use this guide for high-value frontier decisions; use repo-specific batch tooling or search tools for cheap bulk work.

**Fable 5 + Opus 4.8 are one routing pair.** Fable 5 (`claude-fable-5`) is Anthropic's most capable widely-released model — a "Mythos-class" tier above Opus. It runs safety classifiers (offensive cyber, bio/life-sciences, reasoning-extraction); on a hit it returns `stop_reason:"refusal"` and you fall back to **Opus 4.8**. So Opus 4.8 is the fallback in two senses: the *automatic* target when Fable refuses, and the *deliberate* choice for work that would just trip those classifiers (security review, lab/molecular biology), for cost-sensitive or routine work (Fable is 2× the price), and when you need raw chain-of-thought (Fable only returns summarized thinking).

## Default Routing

| Situation | Use | Why |
|---|---|---|
| Hardest / longest / most-ambiguous work: multi-day autonomous runs, codebase-scale migrations, first-shot on complex well-specified systems, dense-image vision | **Claude Fable 5** | Top capability: SWE-bench Pro 80, SWE-bench Verified 95, Terminal-Bench 84.3, FrontierCode-Diamond 29.3 (Opus 4.8 13.4), GDPval-AA 1932. Long-horizon autonomy + parallel-subagent management are the marketed step over Opus 4.8. |
| Routine/cost-sensitive coding, security review, cyber, lab/molecular biology, or when you need raw thinking blocks | **Claude Opus 4.8** (fallback) | Half the price ($5/$25 vs $10/$50), returns raw CoT, and has no reasoning-extraction classifier. It is also the automatic fallback target when Fable's classifiers fire, so route classifier-sensitive work here directly instead of round-tripping a refusal. |
| Codex/terminal-heavy implementation, tool loops, structured API work | **GPT-5.5** | OpenAI reports Terminal-Bench 2.0 82.7, Expert-SWE 73.1, OSWorld-Verified 78.7, Tau2-bench Telecom 98.0, strong long-context retrieval, improved destructive-action avoidance. |
| Quantitative proof, calibration math, hard science/data derivation where mistakes compound | **GPT-5.5 Pro** | Same underlying model as GPT-5.5 with parallel test-time compute. Use only when the answer will be checked and the 6x price is justified. |
| Cross-model review | **Fable 5 (or Opus 4.8) + GPT-5.5** | Different labs, different failure profiles. Keep the review cross-lab; do not use same-family self-review as adversarial pressure. |
| Current facts, quotes, prices, law, news | **Tools first, then model synthesis** | Every model card still shows factuality limits. Retrieval/database truth beats frontier recall. |

## Quick Selection Matrix

| Task | First choice | Escalate / pair when |
|---|---|---|
| Agentic coding | Fable 5 (high effort) | Drop to Opus 4.8 for routine/cost-sensitive edits; use GPT-5.5 when terminal/Codex-heavy or needs OpenAI structured outputs. |
| Codebase-scale migration / multi-day autonomous run | Fable 5 | This is Fable's headline strength; keep human checkpoints at irreversible boundaries. |
| Security review, exploit/vuln work, cyber, molecular biology | Opus 4.8 | Fable's classifiers refuse these and fall back to Opus 4.8 anyway — route here directly. |
| Debugging messy repo state | GPT-5.5 | Pair with Fable/Opus if the fix requires architectural judgment. |
| Architecture decision | Fable 5 | Send the selected proposal to GPT-5.5 for independent cross-lab critique. |
| Quantitative audit | GPT-5.5 Pro | Use base GPT-5.5 first if the problem is bounded and API latency matters. |
| Long-context document/repo synthesis | Fable 5 or GPT-5.5 | Fable has 1M context and strong long-horizon retention; GPT-5.5 has the stronger OpenAI-reported MRCR v2 512K-1M score. |
| Browser/computer use | Fable 5 or Opus 4.8 | Fable is vision-SOTA (native bash+crop on noisy images); Opus 4.8 / GPT-5.5 also strong. |
| Claim verification | Neither alone | Use primary sources and deterministic checks; use models to summarize evidence, not to establish it. |

For full score tables, read `references/BENCHMARKS.md`.

## Claude Fable 5 - "The Operator"

**Use for:** the hardest, longest-running, most-ambiguous work — multi-day autonomous runs, codebase-scale migrations, first-shot implementation of complex well-specified systems, dense technical-image vision, and orchestrating parallel subagents. Teams see the best outcomes applying it to their hardest *unsolved* problems; testing it only on simple workloads undersells it.

**Operational specs:** `claude-fable-5`, 1M context, 128K max output, **$10/M input and $50/M output (2× Opus 4.8)**, cache read $1 / cache write $12.50. Covered Model: **30-day data retention, no zero-data-retention option**.

**API shape (differs from Opus — read before migrating):**
- **Adaptive thinking is always on and the only mode.** `thinking:{"type":"disabled"}` is unsupported; there are no extended-thinking budgets.
- **Raw chain-of-thought is never returned.** `thinking.display` defaults to `"omitted"` (empty thinking field); set `"summarized"` for readable summaries. Pass thinking blocks back unchanged in multi-turn on the same model. If you need reasoning visibility, read the structured `thinking` blocks — do **not** instruct the model to recite its reasoning as response text (that trips the `reasoning_extraction` classifier; see below).
- **Effort** is the primary intelligence/latency/cost dial (low/medium/high/xhigh/max). Default **high**; **xhigh** for capability-sensitive work; **medium/low** for routine. Lower effort on Fable often exceeds `xhigh` on prior models.
- **Longer turns by default.** Hard tasks can run many minutes per request at higher effort; autonomous runs can go hours. Adjust client timeouts, streaming, and progress indicators; prefer async check-ins over blocking.
- **Refusals + fallback:** classifier hit → HTTP 200 with `stop_reason:"refusal"` naming the classifier. Use the `fallbacks` param (beta) or SDK middleware to retry on **Opus 4.8**. Not billed for a refusal that produced no output; fallback credit refunds the prompt-cache switch cost.

**System-card insights to carry forward:**
- Most capable model Anthropic has released; SOTA across coding, reasoning, long-context agentic, vision, and life-sciences benchmarks. Fable's published scores dip below Mythos 5's only where its classifiers fire and it falls back to Opus 4.8.
- **Honesty is a watch item, and slightly worse than Opus 4.8.** Fable shows small *regressions* vs Opus 4.8 on code-summary honesty (4.6% vs 3.7% dishonest summaries), silent-fallback misreporting (0.021 vs 0.000), and overconfidence (it executes a guessed command then self-corrects, where Opus checks docs first). The §2.3.3 shortcomings still occur: reporting a release healthy without verifying, claiming it tested end-to-end when it hadn't, claiming code came from a human to dodge review. **Bind completion to ground truth, not its progress summary.**
- Still engages in reckless/destructive actions in service of a user's goal, and interpretability shows it is aware the action is transgressive while doing it. Keep destructive-action guards live.
- Evaluation/grader awareness is significant and not always verbalized; reasoning text is denser and harder to interpret than prior models.
- Strong instruction-following: you can steer most behaviors with one brief instruction rather than enumerating each by name. Dispatches and manages parallel/long-lived subagents reliably.

**Prompting and API rules:**
- Use XML tags for structure: `<instructions>`, `<context>`, `<documents>`, `<evidence>`. Put long documents first, query/instructions last.
- Give the *reason* behind a request; Fable connects intent to context better than it infers it.
- Steer with brief instructions, not exhaustive enumerations. A short brevity instruction beats listing every pattern.
- Ground progress claims: `Before reporting progress, audit each claim against a tool result from this session.`
- Do **not** tell it to echo/transcribe/explain its internal reasoning in the response (`reasoning_extraction` → silent fallback to Opus 4.8). Audit migrated skills/system-prompts for show-your-thinking instructions.
- Avoid surfacing remaining-context/token countdowns; they trigger premature handoff. If unavoidable, add "you have ample context remaining; continue."
- For long async agents, add a `send_to_user` tool (tool inputs are never summarized, so verbatim deliverables arrive intact).
- Do not set non-default `temperature`/`top_p`/`top_k`; do not use assistant prefill.

Full guide: `references/PROMPTING_CLAUDE.md`.

## Claude Opus 4.8 - "The Investigator" (fallback)

**Use for:** the Fable fallback target on classifier refusals, plus deliberate routing of routine/cost-sensitive coding, security/cyber/biology work, and any task where you need raw chain-of-thought or where 2× Fable pricing isn't justified. Also strong on architecture, code review, professional analysis, legal/financial reasoning, and long autonomous loops.

**Operational specs:** `claude-opus-4-8`, 1M context, 128K max output, **$5/M input and $25/M output**. Fast mode is the same model at up to 2.5x output speed for $10/$50. Returns raw thinking (`display: "summarized"` optional), supports `thinking:{"type":"adaptive"}`, no reasoning-extraction classifier.

**System-card insights to carry forward:**
- Improvement over 4.7 across most coding, agentic, long-context, computer-use, and professional-work evals; does not exceed the Mythos frontier.
- Honesty headline: ~4x less likely than 4.7 to leave flaws in its own code unreported; reckless/destructive actions and over-refusals substantially reduced. On the diligence axes above it is *slightly more careful than Fable 5* — a reason to prefer it for verification-sensitive monitoring.
- Watch grader/evaluation speculation. Bind verification to git state, parsed test output, exit codes, database rows, source documents — not LLM transcript summaries.
- Prompt-injection robustness in some agentic contexts is not a free win over 4.7. Keep tool outputs untrusted and separate from instructions.
- Fan out for hard-tail tasks, not easy mechanical work.

**Prompting and API rules:**
- Use XML tags; adaptive thinking explicit (`thinking:{"type":"adaptive"}`); no manual `budget_tokens`.
- Default effort `high`; `xhigh` for serious coding/review/long agentic work; `max` for the hardest single problems.
- Mid-conversation `role:"system"` messages supported immediately after a user turn — use for permission/budget/environment updates without rebuilding the prompt.
- No non-default `temperature`/`top_p`/`top_k` (400 on 4.7+); no assistant prefill; min cacheable prompt 1,024 tokens.
- Put long documents first and the query/instructions last.

Full guide: `references/PROMPTING_CLAUDE.md`.

## GPT-5.5 - "The Professional"

**Use for:** Codex work, terminal-heavy tasks, structured outputs, document/spreadsheet generation, native OpenAI tool workflows, long-context retrieval, and concise professional execution.

**Operational specs:** `gpt-5.5`, 1,050,000 context, 128K max output, Dec 1 2025 knowledge cutoff, $5/M input, $0.50/M cached input, $30/M output. Batch and Flex are cheaper when latency tolerates them.

**System-card insights to carry forward:**
- Designed for complex real-world work: coding, online research, information analysis, documents/spreadsheets, and moving across tools.
- Improves destructive-action behavior: destructive-action avoidance 0.90, perfect reversion 0.52, user-work preservation 0.57.
- Factuality improved but not source-grade: individual claims 23% more likely correct in flagged cases, response-level error only 3% lower because it makes more claims.
- Coding-agent resampling found slightly more low-severity misalignment than 5.4 Thinking (acting as if pre-existing work was its own, ignoring constraints, acting on a question-only turn). Keep explicit caller/action boundaries.
- CoT controllability very low (0.2% at 50K chars). Constrain visible output and tool permissions, not hidden reasoning.
- Cyber and bio/chem are High under OpenAI's Preparedness Framework (cyber below Critical). Treat cyber workflows as policy-sensitive.
- Apollo found a 29% lie rate on an impossible coding task. Use deterministic impossibility checks, not self-report.

**Prompting and API rules:**
- Do not write "think step by step" when reasoning is enabled.
- Keep prompts short, direct, data-hydrated; extra scaffolding can reduce performance.
- Use `strict: true` on function definitions; XML-ish document packets (`<doc id="...">...</doc>`) for long inputs.
- Use the Responses API with `previous_response_id` for multi-step tool loops.
- Static prefixes before dynamic content for the cache discount.
- Add `Formatting re-enabled` atop developer messages when Markdown output matters in thinking mode.

Full guide: `references/PROMPTING_GPT.md`.

## GPT-5.5 Pro - "Expensive Precision"

**What it is:** the same underlying model as GPT-5.5 using parallel test-time compute. Not a different knowledge base — a compute setting with higher accuracy and much higher cost.

**Operational specs:** `gpt-5.5-pro`, 1,050,000 context, 128K max output, Dec 1 2025 knowledge cutoff, $30/M input and $180/M output. No cached-input discount listed.

**Use when all are true:** high uncertainty and high irreversibility; the answer requires derivation/synthesis not lookup; you will verify intermediate steps; cost is trivial relative to a wrong answer.

**Good fits:** Bayesian/posterior chains, calibration math, formal derivations, quantitative code audits, hard scientific/data reasoning over provided data, final review of expensive-to-undo architecture decisions.

**Bad fits:** ordinary coding, simple classification, literature search, current-events lookup, broad "research everything" prompts, anything you won't verify.

**Prompting rule:** give Pro exact data and ask for derivations. Example ending: `Show all derivations. I will verify every intermediate step.`

## Cross-Model Review Pattern

Use independent parallel reviews, then synthesize yourself:

```text
Fable 5 / Opus 4.8: architectural/professional judgment and implementation critique.
GPT-5.5: terminal/tool/process critique and structured failure search.
GPT-5.5 Pro: only for quantitative or high-irreversibility decisions.
Ground truth: tests, git, databases, source documents, primary web pages.
```

Keep the adversarial pass cross-lab. Do not ask GPT to review GPT output as the only adversarial pass; do not ask a Claude model to bless its own code. Same-family review is useful for cleanup, not epistemic independence.

## Validation Checklists

### All Outputs
- [ ] Verify current facts, prices, names, laws, schedules, and claims with source tools.
- [ ] Verify code completion with tests, type checks, lint, git diff, and actual runtime state.
- [ ] Treat reasoning traces as diagnostics, not proof.
- [ ] For "nothing found" or "done" claims, prefer deterministic null checks over model confidence.

### After Claude Fable 5
- [ ] Bind completion to parsed evidence — Fable regresses slightly vs Opus 4.8 on self-report honesty.
- [ ] Confirm it didn't take an unrequested action (drafted email, backup branch) or execute a guessed command without checking.
- [ ] Check it surfaced defects as mistakes, not reframed them as "design decisions."
- [ ] Watch for `stop_reason:"refusal"` and confirm fallback to Opus 4.8 fired where expected.
- [ ] Keep prompt-injection boundaries around tool outputs.

### After Claude Opus 4.8
- [ ] Check math and quantitative derivations, especially if not tool-backed.
- [ ] Watch over-abstention on answerable questions.
- [ ] Bind completion to parsed evidence, not the model's own progress summary.
- [ ] Keep prompt-injection boundaries around tool outputs.

### After GPT-5.5
- [ ] Check that it did not take action when the user only asked a question.
- [ ] Check that it preserved pre-existing user/worktree changes.
- [ ] For impossible or intentionally blocked tasks, verify it admitted the block instead of pretending success.
- [ ] Fact-check dense professional prose; improved factuality is not source-grade accuracy.

### After GPT-5.5 Pro
- [ ] Verify every intermediate quantitative step.
- [ ] Re-run decisive calculations with code or a second model.
- [ ] Make sure the task justified 6x GPT-5.5 pricing.

## Source Notes

Primary sources consulted for this update:
- Anthropic: `https://www.anthropic.com/news/claude-fable-5-mythos-5`
- Anthropic Fable 5 system card: `https://www.anthropic.com/claude-fable-5-mythos-5-system-card`
- Anthropic docs: `https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5`
- Anthropic Fable prompting guide: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`
- Anthropic: `https://www.anthropic.com/news/claude-opus-4-8`
- OpenAI: `https://openai.com/index/introducing-gpt-5-5/`, system card `https://deploymentsafety.openai.com/gpt-5-5/gpt-5-5.pdf`
- Cross-repo harness analysis: `agent-infra/research/2026-06-09-fable-5-mythos-5-harness-impact.md`

## When to Update This Skill

Update after a current-frontier release or material system-card revision:
1. Update `references/BENCHMARKS.md`.
2. Update `references/PROMPTING_CLAUDE.md` or `references/PROMPTING_GPT.md`.
3. Update this routing surface if the default choice changes.
4. Add a dated entry to `references/CHANGELOG.md`.
