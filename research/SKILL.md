---
name: research
description: "One-shot source-grounded research: /research, 'find papers about', 'what's known about', literature reviews, and science/benchmark memos. Match depth to the question. Not implementation; recurring research and compilation use /research-ops."
user-invocable: true
argument-hint: '[question] [--quick | --deep] [--adversarial]'
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent, WebSearch, WebFetch]
effort: high
---

# Research

Answer the user's question with traceable evidence and explicit uncertainty. Match the requested scope and deliverable; a factual lookup needs an inline answer, not a compulsory memo. Research alone does not authorize implementation, new spending, or external contacts. When research is part of already authorized work, preserve that authorization for the next step.

For recurring cycles, compilation, training-data diffs, or coordinated research dispatch, use [research-ops](../research-ops/SKILL.md). If the result calls for a new benchmark, [eval](../eval/SKILL.md) owns its design. Do not silently turn a research question into an experiment.

## Choose depth

Honor `--quick`, `--deep`, and the user's requested depth. Briefly state the chosen tier when a substantial search is needed.

| Mode | Use for | Read when selected | Result |
|---|---|---|---|
| **Quick** | A fact, source, or single claim | No additional workflow required | Direct answer with supporting source and any material limit |
| **Standard** | Topic review, comparison, "what do we know?" | [Topic review](references/topic-review.md) | Focused synthesis; memo when useful or requested |
| **Deep** | Literature review, novel question, broad investigation | [Topic review](references/topic-review.md), including its Deep section | Report with disconfirmation and a reproducible search/verification record |
| **Adversarial** | `--adversarial`, challenge, debunk, stress-test, "call BS on" | [Adversarial review](references/adversarial.md) | Labeled case brief testing the strongest critique; usually Deep, but honor a bounded single-claim request |

If no question is given, use the active conversation or a relevant project `schemas/open_questions.md` / `.claude/rules/research-depth.md`; ask only if the target is still missing. Read a project depth rule when it applies to this task.

## Evidence constraints

- Discovery results locate evidence. Read the primary document, official database record, or full paper supporting the claim. Verify that identifiers and titles match; never invent citations, authors, sample sizes, or numbers.
- Before citing a paper as support, read its relevant full text and apply [paper evidence checks](references/paper-evidence.md). If only an abstract is available, identify that limit and do not imply a full-text assessment.
- Keep retrieved evidence, reproducible analysis, inference, estimates, and training knowledge distinct. Cite empirical claims at the claim; label an unresolved claim instead of promoting it to fact.
- For date-sensitive questions, state the date anchor and verify source dates. A backend failure or empty search is not evidence that the claim is false or no source exists.
- Put exact source wording in quotation marks with its citation; paraphrase the rest. If retrieved evidence does not answer the question, report what is known and what remains unsupported.

## Routes to detail

Read only the references needed for the current question:

- **Find a source:** use a known primary source directly; for discovery, prefer Exa then Brave when available. Academic metadata uses `search_papers`; database facts use the database. [Tool routing](references/tool-routing.md) covers tool choices and retrieval recovery. Inspect the current tool schema before relying on a remembered name or argument.
- **Clinical or biological evidence synthesis:** [shared epistemics](../references/epistemics/SKILL.md). **Investigation / OSINT:** [shared source grading](../references/source-grading/SKILL.md); Admiralty grades replace duplicate provenance tags.
- **Domain-specific pitfalls:** read the applicable section of [DOMAINS.md](DOMAINS.md).
- **Writing a reusable memo:** [output formats and provenance](references/memo-output.md). For numbers doing argumentative work, use the [quantitative bias checklist](references/quant-bias-checklist.md): construction items 1–33, plus section I when an institution produced the number.
- **"What is missing?" / novelty / missed discovery:** [gap audits](references/gap-audits.md).
- **A dead route, broken pointer, or other skill defect:** [known issues](references/known-issues.md), the append-only history. Log a new issue with `~/Projects/skills/hooks/append-skill-memento.sh research '<one-line issue>'`; the helper writes to that reference.

$ARGUMENTS
