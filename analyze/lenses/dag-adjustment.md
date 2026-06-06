# DAG Adjustment Lens

Use before regression, controls, confounders, causal effects, or adjustment-set
claims.

1. Classify variables: treatment, outcome, pre-treatment confounder, mediator,
   descendant, instrument, collider.
2. Draw the directional DAG in text.
3. Identify valid adjustment set.
4. Audit proposed controls for mediators, descendants, colliders, and
   post-treatment variables.
5. If needed, read `references/dag-construction.md`,
   `references/adjustment-algorithms.md`, and
   `references/output-templates.md`.

Stop if any control is a descendant of treatment or a collider opened by
conditioning.
