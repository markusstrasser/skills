<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 2: Standard Model Prompts

`upgrade` should not teach raw provider CLI recipes. Phase 2 owns the review
question and the bounded packet, then hands both to the shared dispatch/review
surface.

## Shared Contract

Inputs:

- a bounded codebase artifact such as `codebase.md`
- project context from `CLAUDE.md` or `README.md`
- recent git history so reviewers can skip already-fixed issues
- optional pre-scan output such as Ruff statistics

Outputs:

- `findings.json`
- `coverage.json`
- `disposition.md` when extraction runs

If those artifacts are missing, the dispatch path is incomplete.

## Context Requirements

Before dispatch, assemble:

- `PROJECT_CONTEXT`: short operating brief from `CLAUDE.md` or `README.md`
- `RECENT_COMMITS`: `git log --oneline -10`
- `RUFF_PRESCAN`: small pre-scan snippet when relevant

Feed those into the packet or prompt body. They are part of the review context,
not optional embellishments.

## Prompt Roles

Keep the review roles distinct even when the transport is shared:

- Gemini / architecture pass:
  - concrete, verifiable codebase issues
  - majority-pattern violations
  - broken references, swallowed errors, duplication, coupling
- GPT / formal pass:
  - harness and enforcement opportunities
  - type-safety architecture
  - agent-DX and composability risks
  - quantified impact and verification criteria

The canonical prompt bodies live in the shared review layer. If you need to
change wording, change it there once instead of copying a second prompt stack
into `upgrade`.

## Dispatch Pattern

Preferred sequence:

1. Build or reuse one bounded packet/dump artifact.
2. Call the shared review surface with GPT-inclusive axes.
3. Read `findings.json` and `coverage.json`.
4. Triaging starts from those artifacts, not raw model transcripts.

For user-facing upgrade work, the safe defaults are:

- `standard` for most audits
- `deep` for structural or domain-dense audits
- `full` for shared infra or high-stakes changes

Do not revive the old Gemini-only `simple` preset in upgrade guidance.

## Convergence Analysis

After dispatch:

- treat convergent findings across models as highest-confidence candidates
- verify model-unique findings against code before accepting them
- inspect `coverage.json` for dropped packet blocks, axis failures, and low
  extraction coverage before trusting the findings set
