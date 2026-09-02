<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 2H: Harness Mode Prompts

Harness mode should not re-describe dispatch internals. It should consume the
shared review packet contract and focus on enforcement gaps.

## Required Inputs

- `CLAUDE.md` plus the project-specific vetoed decisions / data-sources rules
- recent git history
- a packet built from the relevant codebase chunks

Use the shared packet builders and the shared review surface:

- `shared/context_packet.py` for packet assembly
- shared review/dispatch contract for multi-axis execution and extraction
- `review/lenses/adversarial-review.md` for the axis responsibilities

## Harness Angles

The harness prompts should focus on:

1. Import-time checks
2. Runtime assertions at construction boundaries
3. AST-based lint rules
4. Type narrowing and protocols
5. Unification opportunities that reduce drift

The canonical prompt wording lives with the review skill. This file only says
what the harness mode should optimize for and which shared contracts it should
use.
