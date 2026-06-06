---
name: model-guide
description: Frontier model selection and prompting for Claude Opus 4.8, GPT-5.5, and GPT-5.5 Pro.
user-invocable: true
argument-hint: '[task description or model name]'
effort: low
---

# Model Guide

Select between the current frontier pair and prompt them correctly.

**Models covered:** Claude Opus 4.8, GPT-5.5, GPT-5.5 Pro.
**Last updated:** 2026-06-06.
**Active stance:** This skill no longer maintains a broad model zoo. Older GPT, Gemini, Grok, and Sonnet routes were removed from active guidance. Use this guide for high-value frontier decisions; use repo-specific batch tooling or search tools for cheap bulk work.

## Default Routing

| Situation | Use | Why |
|---|---|---|
| Large codebase work, architecture, migrations, professional judgment | **Claude Opus 4.8** | Best overall agentic coding/professional-work profile in the Opus 4.8 system card: SWE-bench Verified 88.6, SWE-bench Pro 69.2, GDPval-AA 1890, OSWorld-Verified 83.4. |
| Codex/terminal-heavy implementation, tool loops, structured API work | **GPT-5.5** | OpenAI reports Terminal-Bench 2.0 82.7, Expert-SWE 73.1, OSWorld-Verified 78.7, Tau2-bench Telecom 98.0, strong long-context retrieval, and improved destructive-action avoidance. |
| Quantitative proof, calibration math, hard science/data derivation where mistakes compound | **GPT-5.5 Pro** | Same underlying model as GPT-5.5 with parallel test-time compute. Use only when the answer will be checked and the 6x price is justified. |
| Cross-model review | **Opus 4.8 + GPT-5.5** | Different labs, different failure profiles. Do independent reviews; do not use same-family self-review as adversarial pressure. |
| Current facts, quotes, prices, law, news | **Tools first, then model synthesis** | Both model cards still show factuality limits. Retrieval/database truth beats frontier recall. |

## Quick Selection Matrix

| Task | First choice | Escalate / pair when |
|---|---|---|
| Agentic coding | Opus 4.8 | Use GPT-5.5 when the task is terminal/Codex-heavy or needs OpenAI structured outputs. |
| Debugging messy repo state | GPT-5.5 | Pair with Opus if the fix requires architectural judgment. |
| Architecture decision | Opus 4.8 | Send the selected proposal to GPT-5.5 for independent critique. |
| Quantitative audit | GPT-5.5 Pro | Use base GPT-5.5 first if the problem is bounded and API latency matters. |
| Long-context document/repo synthesis | Opus 4.8 or GPT-5.5 | GPT-5.5 has the stronger OpenAI-reported MRCR v2 512K-1M score; Opus has stronger professional-work judgment. |
| Browser/computer use | Opus 4.8 or GPT-5.5 | Opus leads OSWorld-Verified in the 4.8 card; GPT-5.5 has native Codex/computer-use product integration. |
| Claim verification | Neither alone | Use primary sources and deterministic checks; use models to summarize evidence, not to establish it. |

For full score tables, read `references/BENCHMARKS.md`.

## Claude Opus 4.8 - "The Investigator"

**Use for:** large-scale code changes, architecture, code review, professional analysis, legal/financial document reasoning, long autonomous loops, and synthesis where judgment matters.

**Operational specs:** `claude-opus-4-8`, 1M context by default on Claude API/Amazon Bedrock/Vertex AI, 128K max output, $5/M input and $25/M output. Fast mode is the same model at up to 2.5x output speed for $10/$50.

**System-card insights to carry forward:**
- Opus 4.8 is an improvement over 4.7 across most coding, agentic, long-context, computer-use, and professional-work evaluations, but it does not exceed Anthropic's Mythos Preview frontier-risk model.
- Honesty is the practical headline: Anthropic reports it is around 4x less likely than 4.7 to leave flaws in its own code unreported, and the system card says reckless/destructive actions and over-refusals are substantially reduced.
- The new watch item is grader/evaluation speculation. Do not let an LLM judge transcript summaries decide completion. Bind verification to git state, parsed test output, exit codes, database rows, and source documents.
- Prompt-injection robustness in some agentic contexts is not a free win over 4.7. Keep tool outputs untrusted and separate them from instructions.
- Multi-agent fan-out helps hard-tail tasks, not easy mechanical work. Use fan-out when pass rate is uncertain and latency is dominated by hard subtasks.

**Prompting and API rules:**
- Use XML tags for structure: `<instructions>`, `<context>`, `<documents>`, `<evidence>`.
- Use adaptive thinking explicitly: `thinking: {"type": "adaptive"}`.
- Default effort is `high`. Use `xhigh` for serious coding, review, and long-running agentic work; reserve `max` for the hardest single problems.
- Mid-conversation system messages are now supported immediately after a user turn in `messages`; use them to update permissions, budgets, or environment context without rebuilding the prompt.
- Do not set non-default `temperature`, `top_p`, or `top_k`; 4.7+ rejects them. Do not use assistant prefill.
- Put long documents first and the query/instructions last.

Full guide: `references/PROMPTING_CLAUDE.md`.

## GPT-5.5 - "The Professional"

**Use for:** Codex work, terminal-heavy tasks, structured outputs, document/spreadsheet generation, native OpenAI tool workflows, long-context retrieval, and concise professional execution.

**Operational specs:** `gpt-5.5`, 1,050,000 context, 128K max output, Dec 1 2025 knowledge cutoff, $5/M input, $0.50/M cached input, $30/M output. Batch and Flex are cheaper when latency tolerates them.

**System-card insights to carry forward:**
- GPT-5.5 is designed for complex real-world work: coding, online research, information analysis, documents/spreadsheets, and moving across tools.
- It improves destructive-action behavior over prior Codex/Thinking models: destructive-action avoidance 0.90, perfect reversion 0.52, user-work preservation 0.57 in OpenAI's eval.
- Its factuality improved but did not become source-grade. OpenAI reports individual claims were 23% more likely to be correct in flagged factual-error cases, while responses contained factual errors only 3% less often because the model makes more claims.
- In coding-agent resampling, OpenAI found slightly more low-severity misalignment than GPT-5.4 Thinking, including acting as if pre-existing work was its own, ignoring user constraints, and taking action when the user only asked a question. Keep explicit caller/action boundaries.
- CoT controllability is very low: OpenAI reports only 0.2% control success at 50K-character CoTs. Do not waste prompt budget trying to steer hidden reasoning; constrain the visible output and tool permissions.
- Cyber and bio/chem are classified High capability under OpenAI's Preparedness Framework, with cyber below Critical and strengthened safeguards. Treat cyber workflows as policy-sensitive.
- Apollo found no sandbagging on deferred-subversion tasks, but did find a 29% lie rate on an impossible coding task. Impossible-task evals need deterministic impossibility checks, not model self-report.

**Prompting and API rules:**
- Do not write "think step by step" when reasoning is enabled.
- Keep prompts short, direct, and data-hydrated. The model reasons internally; extra scaffolding can reduce performance.
- Use `strict: true` on function definitions.
- Use XML-ish document packets (`<doc id="...">...</doc>`) for long inputs.
- Use the Responses API with stored state / `previous_response_id` for multi-step tool loops.
- Put static prompt prefixes before dynamic content to capture the cache discount.
- Add `Formatting re-enabled` at the top of developer messages when Markdown output matters in thinking mode.

Full guide: `references/PROMPTING_GPT.md`.

## GPT-5.5 Pro - "Expensive Precision"

**What it is:** OpenAI says GPT-5.5 Pro is the same underlying model as GPT-5.5 using parallel test-time compute. It is not a different knowledge base. It is a compute setting with higher accuracy and much higher cost.

**Operational specs:** `gpt-5.5-pro`, 1,050,000 context, 128K max output, Dec 1 2025 knowledge cutoff, $30/M input and $180/M output. No cached-input discount is listed in the current model comparison page.

**Use when all are true:**
- The problem is high uncertainty and high irreversibility.
- The answer requires derivation or synthesis, not just lookup.
- You will verify intermediate steps.
- The cost is trivial relative to a wrong answer.

**Good fits:** Bayesian/posterior chains, calibration math, formal derivations, quantitative code audits, hard scientific or data-analysis reasoning over provided data, final review of architecture decisions that would be expensive to undo.

**Bad fits:** ordinary coding, simple classification, literature search, current-events lookup, broad "research everything" prompts, and any output you will not verify.

**Prompting rule:** Give Pro exact data and ask for derivations. Example ending: `Show all derivations. I will verify every intermediate step.`

## Cross-Model Review Pattern

Use independent parallel reviews, then synthesize yourself:

```text
Opus 4.8: architectural/professional judgment and implementation critique.
GPT-5.5: terminal/tool/process critique and structured failure search.
GPT-5.5 Pro: only for quantitative or high-irreversibility decisions.
Ground truth: tests, git, databases, source documents, primary web pages.
```

Do not ask GPT to review GPT output as the only adversarial pass. Do not ask Opus to bless its own code. Same-family review is useful for cleanup, not for epistemic independence.

## Validation Checklists

### All Outputs
- [ ] Verify current facts, prices, names, laws, schedules, and claims with source tools.
- [ ] Verify code completion with tests, type checks, lint, git diff, and actual runtime state.
- [ ] Treat reasoning traces as diagnostics, not proof.
- [ ] For "nothing found" or "done" claims, prefer deterministic null checks over model confidence.

### After Opus 4.8
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
- Anthropic: `https://www.anthropic.com/news/claude-opus-4-8`
- Anthropic: `https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-8`
- Anthropic system-card registry: `https://www.anthropic.com/system-cards`
- OpenAI: `https://openai.com/index/introducing-gpt-5-5/`
- OpenAI system card: `https://deploymentsafety.openai.com/gpt-5-5/gpt-5-5.pdf`
- OpenAI pricing: `https://openai.com/api/pricing/`
- OpenAI model comparison: `https://developers.openai.com/api/docs/models/compare`

## When to Update This Skill

Update after a current-frontier release or material system-card revision:
1. Update `references/BENCHMARKS.md`.
2. Update `references/PROMPTING_CLAUDE.md` or `references/PROMPTING_GPT.md`.
3. Update this routing surface if the default choice changes.
4. Add a dated entry to `references/CHANGELOG.md`.
