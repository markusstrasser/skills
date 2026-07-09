# GPT-5.6 Prompting Guide

**Last updated:** 2026-07-09
**Scope:** GPT-5.6 Sol / Terra / Luna (+ Pro mode). GPT-5.5 removed.

## Use Sol / Terra / Luna For

- **Sol** (`gpt-5.6-sol`): Codex and terminal-heavy implementation; formal/cross-lab; architecture GPT side.
- **Terra** (`gpt-5.6-terra`): Mid-tier opt-in between Luna and Sol.
- **Luna** (`gpt-5.6-luna`): Everyday GPT (≈ prior 5.5 perf at ~½ price) + mechanical/lint at low effort.
- Structured outputs and strict tool schemas.
- Document, spreadsheet, and slide generation inside OpenAI/Codex workflows.
- Long-context retrieval where OpenAI-reported MRCR performance matters.

## Use Pro Mode For

Pro is **not** a separate slug — set API `reasoning.mode=pro` on Sol/Terra/Luna (same $/MTok, more tokens). Use only when the task is worth the cost:

- Hard quantitative derivation.
- Calibration math or Bayesian chains.
- Formal proof or precise data-analysis reasoning.
- Final review of decisions that are expensive to undo.
- Scientific/technical reasoning over provided data where extra test-time compute is likely to matter.

Do not use Pro for ordinary coding, broad web research, simple classification, or current-fact lookup.

## Model And API Facts

| Variant | What differs | Price | Context | Max output |
|---|---|---:|---:|---:|
| `gpt-5.6-sol` | Flagship | $5/M input, $30/M output | 1.05M | 128K |
| `gpt-5.6-terra` | Balanced | $2.50/M input, $15/M output | 1.05M | 128K |
| `gpt-5.6-luna` | Cheap/fast | $1/M input, $6/M output | 1.05M | 128K |
| Pro mode | Same model + parallel test-time compute | Same $/MTok (more tokens) | 1.05M | 128K |

Cutoff Feb 16 2026. Support Responses, Chat Completions, Batch, streaming, function calling, structured outputs, and image input. Effort includes `max`.

## Prompting Rules

### Do Less Prompt Theater

Do not use:

```text
Think step by step.
Plan before acting.
Check your work.
Iterate until done.
```

GPT-5.5 already reasons internally. Over-scaffolding spends tokens on obeying your process text instead of solving the problem.

Use:

```text
Task: ...
Inputs: ...
Constraints: ...
Output format: ...
Verification: ...
```

### Hydrate With Real Data

GPT-5.5 and Pro are strongest when the prompt contains the actual code, logs, JSON, metrics, or evidence.

Bad:

```text
Audit my variant scoring method.
```

Good:

```text
Here is the scoring function, current distribution, parameter ranges, and failing cases.
Find mathematical or implementation errors. Show derivations for every numerical claim.
```

### Use Strict Schemas

For function calling, set `strict: true` and make parameters precise. Do not rely on prose to enforce schema shape.

### Use XML-Style Document Packets

```xml
<doc id="policy" title="Policy">
...
</doc>
<doc id="log" title="Failure log">
...
</doc>
```

The format is easier for the model to segment than raw concatenated prose or deeply nested JSON.

### Preserve Reasoning State

Use the Responses API with stored state and `previous_response_id` for multi-turn tool loops. Chat Completions-style reconstruction loses reasoning items and can increase token usage.

### Cache Deliberately

Put static instructions and tool descriptions first, dynamic task material later. GPT-5.5 pricing rewards cached input, but only if your prefix is stable.

### Re-enable Formatting

When using thinking mode and Markdown matters, put this at the top of the developer message:

```text
Formatting re-enabled
```

## Pro Prompt Pattern

```text
Task: Derive/check ...

Data:
[exact values, code, logs, or tables]

Constraints:
- ...
- ...

Show all derivations. I will verify every intermediate step.
Return final answer plus a table of assumptions, formulas, and computed values.
```

Pro needs exact material. It is not a substitute for retrieval.

## System-Card Lessons

- GPT-5.5 understands task intent earlier, asks for less guidance, uses tools more effectively, and keeps going longer than earlier models.
- Destructive-action behavior improved, but the model still needs worktree safeguards. OpenAI reports destructive-action avoidance 0.90, perfect reversion 0.52, user-work preservation 0.57.
- Factuality improved but remains insufficient for source-grade claims: in flagged factual-error cases, claims were 23% more likely correct, but response-level factual errors fell only 3%.
- Coding-agent resampling found slightly more low-severity misalignment than GPT-5.4 Thinking, including taking credit for pre-existing work, ignoring constraints, and acting when the user only asked a question. Spell out action permissions.
- CoT controllability is very low. OpenAI reports 0.2% control success for 50K-character CoTs. Do not try to micromanage hidden reasoning.
- Apollo found no deferred-subversion sandbagging, but GPT-5.5 lied about completing an impossible coding task in 29% of samples. Impossible-task harnesses need deterministic checks.
- GPT-5.5 is High capability for bio/chem and High but below Critical for cybersecurity. Cyber prompts need policy-aware routing and source/tool boundaries.

## Verification Checklist

- [ ] Current facts come from sources or tools, not model recall.
- [ ] Tool use and code changes are checked against actual logs and git state.
- [ ] Pre-existing work/user changes are preserved.
- [ ] "Done" claims are backed by tests or parsed artifacts.
- [ ] Pro outputs have every decisive calculation rechecked.

## Sources

- `https://openai.com/index/introducing-gpt-5-5/`
- `https://deploymentsafety.openai.com/gpt-5-5/gpt-5-5.pdf`
- `https://openai.com/api/pricing/`
- `https://developers.openai.com/api/docs/models/compare`
