---
name: competing-hypotheses
description: Analysis of Competing Hypotheses (ACH). Use when investigating any entity, anomaly, root cause, or claim that could have multiple explanations — fraud vs error, bug vs design, correlation vs causation. Dispatches parallel agents with opposing hypotheses, then synthesizes the surviving explanation. Based on Richards Heuer's CIA methodology.
argument-hint: [entity, anomaly, or claim to evaluate]
---

# Analysis of Competing Hypotheses (ACH)

You are evaluating a claim, entity, or anomaly. Your job is NOT to confirm the most likely explanation. Your job is to **systematically destroy every possible explanation** and see what survives.

## Core Principle

> "Truth is whatever is left standing after you have relentlessly tried to destroy every possible explanation." — Richards Heuer, *Psychology of Intelligence Analysis*

Evidence consistent with multiple hypotheses is **diagnostically useless**. Only evidence that **eliminates** a hypothesis has value.

## The Process

### Step 1: Generate Hypotheses

For the target `$ARGUMENTS`, generate at minimum THREE competing hypotheses:

| Hypothesis | Description |
|------------|-------------|
| **H1: Wrongdoing** | The anomaly reflects intentional fraud, abuse, or corruption |
| **H2: Legitimate** | There is a lawful, non-fraudulent explanation |
| **H3: Artifact** | The anomaly is a data error, reporting change, or measurement artifact |

Add domain-specific sub-hypotheses as needed.

### Step 2: Dispatch Competing Agents

Launch **three parallel agents** (Task tool with subagent_type="general-purpose"):

- **Agent A — Prosecution:** Search for enforcement history, ownership anomalies, financial pressure, fraud signatures. Tag all claims [SOURCE: url] or [INFERENCE].
- **Agent B — Defense:** Search for policy changes, industry trends, M&A, comparable clean entities. Find the BEST innocent explanation.
- **Agent C — Artifact Investigator:** Search for data reporting changes, known data issues, system migrations, whether anomaly appears in multiple independent sources.

### Step 3: Build the Diagnosticity Matrix

```
| Evidence                  | H1 | H2 | H3 |
|---------------------------|:--:|:--:|:--:|
| [evidence item]           | C  | I  | N  |

C = Consistent, I = Inconsistent, N = Neutral
```

**Key rule:** Evidence that is C/C/C has **zero diagnostic value**. Focus on evidence that eliminates hypotheses.

### Step 4: Score and Synthesize

Count strong inconsistencies per hypothesis (weight by source grade: A1 = strongest, F6 = weakest). The surviving hypothesis has the fewest strong inconsistencies.

```markdown
## ACH Result: [Entity/Anomaly]

**Surviving Hypothesis:** [H1/H2/H3 + description]
**Confidence:** [0-100]%
**Key Discriminating Evidence:**
- [Most diagnostic item] — eliminates [H2/H3] because [reason]

**Residual Uncertainty:**
- [What evidence would flip the conclusion]
- [What data we don't have]
```

### Step 5: Red Team (recommended for high stakes)

Dispatch a fourth agent to ATTACK the surviving conclusion: find missed evidence, alternative explanations, source quality weaknesses, what a defense attorney would argue.

## When NOT to Use

- Simple factual lookups
- Clearly confirmed findings with A1-rated sources
- Time-critical situations where speed > rigor

$ARGUMENTS
