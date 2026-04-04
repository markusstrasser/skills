<!-- Reference file for causal-dag skill. Loaded on demand. -->

# DAG Construction: 4-Stage Decomposition

Research (arXiv:2507.23488) shows this decomposition achieves 3x F1 improvement over single-shot DAG construction. Do NOT skip stages or merge them.

## Stage 2a: Undirected Skeleton

Connect variables that have ANY causal relationship (direction unknown). Every edge is a substantive claim — omitting an edge claims no causal relationship. State the mechanism for each connection.

```
Sex --- Test_Score          [mechanism: biological + social factors affect cognitive performance]
Sex --- Items_Complete      [mechanism: engagement/stamina differences]
Items_Complete --- Test_Score [mechanism: completion is prerequisite for scoring]
Education --- Test_Score    [mechanism: knowledge/skills affect performance]
```

**Gate:** Is every pair of variables either connected (with mechanism) or deliberately disconnected (with justification for no relationship)?

## Stage 2b: Orient V-Structures (Colliders)

Identify immoralities: triples A --- B --- C where A and C are NOT connected. Orient as A -> B <- C (B is a collider). These are the ONLY edges you can orient from data alone without temporal knowledge.

For each V-structure found:
- State the triple
- Confirm A and C have no direct connection
- Explain why B is caused by both A and C

## Stage 2c: Apply Meek Rules (Propagate Orientations)

Using temporal ordering + V-structure orientations, propagate directions:
1. **Temporal rule:** If A happens before B, orient A -> B
2. **Meek R1:** If A -> B --- C and A is NOT adjacent to C, orient B -> C
3. **Meek R2:** If A -> B -> C and A --- C, orient A -> C
4. **Meek R3:** If A --- B, A --- C, B -> D <- C, and A --- D, orient A -> D

For each edge, provide temporal justification:
```
Sex -> Test_Score          [temporal: sex is fixed at birth, precedes test]
Education -> Test_Score    [temporal: education acquired before test session]
```

## Stage 2d: Flag Remaining Undirected Edges

Any edge still undirected after Meek rules is genuinely ambiguous. List these explicitly — they represent the limits of your causal knowledge. State what data or experiment would resolve each.

## Edge Format for dag_check.py

When providing edges to `dag_check.py`, use the structured format:
```json
{"edges": [
  {"from": "Sex", "to": "Test_Score", "temporal_justification": "Sex fixed at birth, precedes test"},
  {"from": "C", "to": "X", "temporal_justification": "C measured before treatment?"}
]}
```
Edges with `?` in the justification are flagged as uncertain in the output.

## Rules (apply throughout all stages)

- If you're unsure about an edge, mark it with `[?]` and state what evidence would resolve it
- Do NOT add edges "just in case" — each edge is a claim
- If there might be an unobserved common cause (U), draw it: `U -> X, U -> Y [unobserved]`
