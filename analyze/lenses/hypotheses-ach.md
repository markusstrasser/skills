# Hypotheses/ACH Lens

Use when there are multiple plausible explanations and the task needs
adversarial disambiguation.

1. List mutually exclusive hypotheses, including error/artifact.
2. For each hypothesis, predict evidence that should be present and absent.
3. Build an evidence matrix: evidence item -> supports/contradicts each
   hypothesis.
4. Prefer disconfirming evidence over narrative fit.
5. If the matrix is large, use `references/evidence-matrix-template.md` and
   `references/ibe-dominance-format.md`.

Output:

- leading hypothesis
- strongest disconfirming evidence
- top alternative
- discriminating evidence still needed
- decision impact
