<!-- Reference file for causal-dag skill. Loaded on demand. -->

# Adjustment Set Identification

## Back-Door Criterion

Find a set of variables S such that:
1. No variable in S is a descendant of X
2. S blocks every back-door path from X to Y (paths with an arrow into X)

## Procedure

1. List all paths from X to Y
2. Mark which are causal (follow arrow direction from X to Y) — leave these OPEN
3. Mark which are back-door (have an arrow into X) — these must be BLOCKED
4. Find the minimal set S that blocks all back-door paths without opening collider paths

## Exclusion Rules

Do NOT include in S:
- **Mediators** — blocks the causal path, gives you the direct effect instead of the total effect
- **Descendants of treatment** — collider bias
- **Descendants of outcome** — biases the estimate
- **Colliders on non-causal paths** — conditioning opens the path (M-bias)

## Required Output

- **Valid adjustment set:** {C1, C2, ...}
- **Excluded and why:** M (mediator — blocks causal path), D (descendant of X — collider bias), ...
- **Remaining open back-door paths:** [any unblocked non-causal paths, or "none"]
- **Unobserved threats:** [any U variables that would invalidate the adjustment set if they exist]
