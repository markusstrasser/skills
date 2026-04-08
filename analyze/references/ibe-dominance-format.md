<!-- Reference file for competing-hypotheses skill. Loaded on demand. -->

# IBE Dominance Comparison Format

## Criteria Table

For each surviving hypothesis (posterior > 0.10), evaluate on 5 dimensions:

| Criterion | Question |
|-----------|----------|
| **Explanatory scope** | How many of the observations does this hypothesis actively explain (not just "consistent with")? |
| **Specificity** | Does this hypothesis predict the EXACT pattern observed, or just "something like it"? |
| **Parsimony** | How many independent assumptions does this hypothesis require? Fewer = better. |
| **Unification** | Does this hypothesis connect previously unrelated observations? |
| **Fertility** | What NEW testable predictions does this hypothesis generate? More = better. |

## Dominance Rules

- Compare hypotheses pairwise on each criterion: H1 > H2, H1 = H2, or H1 < H2
- **Dominance:** H1 dominates H2 if H1 >= H2 on all criteria and H1 > H2 on at least one
- **Non-dominance:** if neither dominates, state the tradeoff explicitly ("H1 is more parsimonious but H2 has broader scope")
- **Fertility is the tiebreaker.** When tradeoffs are close, the hypothesis generating more NEW checkable predictions wins -- it's more falsifiable

## Why Not Numeric Totals

Equal-weight additive scoring (scope + specificity + ...) assumes interval scales, commensurable dimensions, and equal weights -- none of which are justified. Dominance comparison avoids these assumptions.

## Output Example

```
IBE Dominance:
  H1 vs H2: H1 wins on scope (8/10 vs 4/10), specificity (exact pattern vs vague),
             unification (links 3 prior findings). H2 wins on parsimony (2 vs 4 assumptions).
             H1 dominates on 3/5, loses on 1. -> H1 preferred.
  H1 vs H3: H1 wins on scope, unification. H3 wins on parsimony.
             Tied on specificity, fertility. -> H1 preferred (broader explanatory reach).
  H2 vs H3: Neither dominates. H2 more parsimonious, H3 more fertile.
             -> Non-dominated pair; both survive for further evidence.
```

## Integration with Bayesian Scoring

IBE does NOT override posteriors. It supplements them. If Bayesian posterior says H1=0.45, H2=0.35, and IBE says H1 is also the best explanation, that's converging evidence. If they disagree (high posterior but poor explanation), flag for investigation -- the hypothesis may be fitting noise.
