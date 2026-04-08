<!-- Reference file for causal-dag skill. Loaded on demand. -->

# Worked Example: The Bad-Control Trap

Research question: "What is the causal effect of sex on cognitive test scores?"

A naive agent might specify: `Test_Score ~ Sex + Education + Items_Complete + Room_ID`

## Phase 1 catches it:

| Variable | Classification | Temporal Order | Justification |
|----------|---------------|----------------|---------------|
| Sex | Treatment (X) | Fixed at birth | Exposure of interest |
| Test_Score | Outcome (Y) | At test time | What we're measuring |
| Education | Pre-treatment confounder (C) | Before test | Affects both opportunity and score |
| Items_Complete | Descendant of treatment (D) | During test | Sex -> engagement -> items completed |
| Room_ID | Nuisance | At test time | Affects score, not caused by sex |

## Phase 4 catches it:

| Variable | In DAG? | Classification | In adjustment set? | Problem? |
|----------|---------|---------------|-------------------|----------|
| Sex | Yes | Treatment | N/A | - |
| Education | Yes | Confounder | Yes | OK |
| Items_Complete | Yes | Descendant of X | NO | **COLLIDER BIAS** |
| Room_ID | Yes | Nuisance | Yes | OK (not on causal path, not a descendant) |

**STOP.** Remove `Items_Complete`. It is caused by Sex (via engagement, stamina, strategy differences). Conditioning on it opens a spurious path: `Sex -> Items_Complete <- Other_Causes_of_Completion -> Test_Score`.

**Correct specification:** `Test_Score ~ Sex + Education + Room_ID`
