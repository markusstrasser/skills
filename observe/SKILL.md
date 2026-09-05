---
name: observe
description: "Analyze agent sessions and improve shared workflows or codebases through /observe modes. Excludes ordinary edits, single bugs, diff reviews and session-end digests."
user-invocable: true
argument-hint: <mode> [target] [options...]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: medium
---

# Observe

Use the mode that answers the requested system-level question. A small fix or local retrospective
does not require a codebase audit, frontier scan, or broad review. Diff/PR review belongs to
`/code-review`, plans/findings to `/critique`, one bug to `/analyze`, ideation to `/brainstorm`,
literature work to `/research`, and the session-end digest to `/rsi close`.

## Select and load a workflow

The first positional argument is the mode; the rest are the target and options. Default to `retro`
for an explicit retrospective at session wrap-up, otherwise `sessions`. Read the selected workflow
below before acting, including after compaction or resumption. Load its supporting references only
when the current step needs them; do not load every mode. Options, defaults, and fleet scope are in
[scope and arguments](references/scope-and-arguments.md).

| Mode | Question / result | Workflow |
|------|-------------------|----------|
| `all` | Full RSI pass with every deterministic lane and scope-aware triangulation | [All lanes](references/all.md) |
| `sessions` | Behavioral anti-patterns; `--corrections` mines user corrections | [Sessions](references/sessions.md) |
| `architecture` | Repeated workflows and emerging abstractions; proposal memo | [Architecture](references/architecture.md) |
| `supervision` | Human correction load and its direction | [Supervision](references/supervision.md) |
| `drift` | Slow patterns across many sessions | [Drift](references/drift.md) |
| `retro` | This session's failures; local capture only, no dispatch or fixes | [Retro](references/retro.md) |
| `failures` | Tools/CLIs broken in actual use | [Failures](references/failures.md) |
| `blindspot` | Loop misses the human had to catch | [Blindspot](references/blindspot.md) |
| `harvest` | Consume producers' artifacts, dedup, rank, and drain | [Harvest](references/harvest.md) |
| `suggest` | Repeated workflows worth a skill/tool; scaffold after approval | [Suggest](references/suggest.md) |
| `maintain` | One highest-priority action this tick | [Maintain](references/maintain-workflow.md) |
| `lever` | Order-of-magnitude improvement on a known surface; shipped, measured change | [Lever](references/lever.md) |
| `missing` | Categories never placed on an axis | [Missing](references/missing.md) |
| `generators` | A better set of discovery mechanisms when wins arrive off-trail | [Generators](references/generators.md) |
| `audit` | Code correctness; verified fixes (`--quick`: findings only) | [Audit pipeline](references/audit-pipeline.md) |
| `harness` | Enforcement gaps causing future bug classes | [Harness workflow](references/audit-pipeline.md#harness-mode) |
| `discover` | Missing codebase capabilities; gated inventory through implementation | [Discovery gates and phases](references/discover-gates.md) |
| `pliability` | File discovery; approved splits, renames, and indexing | [Pliability](references/pliability.md) |
| `forensics` | How code and rules evolve, decay, or survive | [Forensics](references/forensics.md) |
| `conventions` / `sweep` | Consistency across code; mechanical checks before model residue | [Conventions](references/conventions.md) |

Retrospective modes see failures. `lever`, `missing`, and `generators` cover unused capabilities
and successful work that falls short of what is possible; use them when that is the actual gap.

## Shared boundaries

- Keep raw transcripts read-only and human/institutional evidence append-only. Read raw turns before
  grading a session; model output, extracted signals, and summaries need verification against source.
- Report miner denominators: scanned, parsed, matched. `parsed 0` is a broken source, not a clean run.
  Verify session IDs, quotations, tool sequences, and file paths before retaining model findings.
- For candidate staging or backlog work, read [candidate lifecycle](references/candidate-lifecycle.md).
  It defines dedup, observation/action streams, ranking, promotion, and proposal-queue backpressure.
  Before creating a steward proposal or pending question, enforce its queue gate.
- Follow the selected mode's [artifact contract](references/artifact-contract.md). `manifest.json`,
  `signals.jsonl`, and `candidates.jsonl` are working artifacts; `improvement-log.md` is a promotion
  sink. Run `observe_gates.py preflight` before any promotion write.
- A mode is not additional authorization. Continue work the user already authorized; self-directed
  work stays within the mode's limits. Capital, external contacts, protected changes, and shared
  infrastructure deployment retain their existing approval boundaries. Architecture and retro
  produce proposals/capture; `maintain` escalates boundary-crossing work as reviewable drafts.

For an unfamiliar command, use the native [recipe and script entry points](references/recipes.md)
and inspect `--help`. Dispatch details belong to [analysis dispatch](references/analysis-dispatch.md)
only when the selected workflow actually requires a model.

If a run exposes a defect in this skill, consult the [append-only issue history](references/known-issues.md)
and log it with `~/Projects/skills/hooks/append-skill-memento.sh observe '<one-line issue>'`.
The helper appends to that history, keeping accumulated incidents out of this router.

$ARGUMENTS
