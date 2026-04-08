<!-- Reference file for causal-dag skill. Loaded on demand. -->

# Output Templates

## Specification Template (Phase 5)

Only produce after Phases 1-4 pass clean.

```
Model:      Y ~ X + C1 + C2
Treatment:  X
Controls:   C1 (pre-treatment confounder: causes both X and Y via ...),
            C2 (pre-treatment confounder: causes both X and Y via ...)
Excluded:   M (mediator — on causal path X -> M -> Y),
            D (descendant of X — collider bias)
Estimand:   Average causal effect of X on Y, conditional on {C1, C2}
Assumptions:
  1. No unmeasured confounding given {C1, C2}
  2. DAG is correctly specified (edges and directions)
  3. [any functional form assumptions — linearity, additivity]
Threats:    [what unmeasured variables could invalidate this]
```

## Consensus Mode (--consensus)

When multiple agents or analysts independently specify DAGs for the same treatment/outcome, use consensus mode to vote on edge structure:

```bash
echo '[spec1, spec2, spec3, ...]' | uv run python3 dag_check.py --consensus
```

Consensus votes on **edge agreement** (what fraction of specs include each edge), NOT on adjustment-set validity. This avoids rewarding under-specified DAGs that omit real confounders.

- Edges with >=60% agreement form the consensus DAG
- Contested edges (<60%) are flagged for review
- The consensus DAG is then validated for adjustment-set correctness
- Adjustment variables are classified: must-adjust / optional / forbidden
