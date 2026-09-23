# Hypotheses/ACH Lens

Use when there are multiple plausible explanations and the task needs
adversarial disambiguation.

1. Inventory the observations as bare facts, stripped of any explanation that
   arrived with them; mark the most surprising one. A proposed explanation that
   came with the question is one hypothesis, not the frame.
2. Generate before ranking, one or more per slot: measurement/artifact,
   selection/composition, chance/base rate, the favored mechanism, a competing
   mechanism (different causal path or confounder), and `H_other` (a cause not
   listed). Each named alternative must be one you would credit at >=10%; a
   strawman does not debias.
3. Drop or repair any hypothesis that fails to explain an inventoried
   observation; record which observation killed it.
4. For each survivor, list supporting findings, contradicting findings, and
   findings it predicts that are absent.
5. Build an evidence matrix: evidence item -> supports/contradicts each
   hypothesis. Prefer disconfirming evidence over narrative fit.
6. If the leader leaves an inventoried observation unexplained, reopen
   generation instead of picking the least-bad listed hypothesis. If generation
   yields only variants, stop enumerating: run the cheapest probe that splits
   the space and induce from its result.
7. Before committing, name the cheapest unexamined evidence that separates the
   leader from the top alternative; get it if it is within budget.
8. If the matrix is large, use `references/evidence-matrix-template.md` and
   `references/ibe-dominance-format.md`.

Why: recall of the true explanation is set at generation; selection, debate
and scoring reorder the set but rarely add the missing cause (arXiv 2608.16645:
tournament precision 2.4x, success@5 55.1% -> 57.1%). Facts-first extraction
removes narrative anchoring that debiasing instructions only dent (arXiv
2607.27384). Diagnostic agents close before requesting the discriminating data
(arXiv 2607.10275). Step 4's columns are the part of guided reflection that
works; "be careful" instructions alone are inert (Norman 2014: 45.0% vs 44.5%;
Staal 2022 meta g=0.20). Subjects who could not guess the rule found it by
generalizing from experiments (Klahr & Dunbar 1988).

Output:

- leading hypothesis
- strongest disconfirming evidence
- top alternative
- discriminating evidence still needed
- decision impact
