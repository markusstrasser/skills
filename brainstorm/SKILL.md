---
name: brainstorm
description: Divergent ideation via systematic perturbation — denial cascades, domain forcing, constraint inversion. Multi-model dispatch optional (volume, not diversity). For convergent critique, use /model-review.
argument-hint: [design space to explore — e.g., "memory architecture alternatives", "how to structure the feedback loop"]
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
---

# Divergent Ideation via Perturbation

You are orchestrating divergent ideation. The goal is ideas that escape the default attractor basin — the high-probability outputs that any model (including you) produces first.

**Core mechanism:** Systematic perturbation of the search space (denial, domain forcing, constraint inversion), not model diversity. Models trained on similar data converge on similar ideas regardless of vendor. The prompting structure does the work.

**This skill is DIVERGENT only.** For convergent critique, use `/model-review`.

## Prerequisites

- `llmx` CLI optional — skill works without it (you run all rounds). With llmx, perturbation rounds run in parallel for speed.

## Pre-Flight

### Constitutional Check

```bash
CONSTITUTION=$(find . -maxdepth 3 -name "CONSTITUTION.md" 2>/dev/null | head -1)
if [ -z "$CONSTITUTION" ]; then
  CLAUDE_MD=$(find . -maxdepth 1 -name "CLAUDE.md" | head -1)
  if [ -n "$CLAUDE_MD" ] && grep -q "^## Constitution" "$CLAUDE_MD"; then
    CONSTITUTION="$CLAUDE_MD"
  fi
fi
GOALS=$(find . -maxdepth 3 -name "GOALS.md" 2>/dev/null | head -1)
```

If found, inject as preamble so generation stays within project principles.

### llmx & Output Setup

```bash
LLMX_AVAILABLE=$(which llmx 2>/dev/null && echo "yes" || echo "no")
TOPIC_SLUG=$(echo "$TOPIC" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//;s/-$//' | cut -c1-40)
BRAINSTORM_ID=$(openssl rand -hex 3)
BRAINSTORM_DIR=".brainstorm/$(date +%Y-%m-%d)-${TOPIC_SLUG}-${BRAINSTORM_ID}"
mkdir -p "$BRAINSTORM_DIR"
```

## The Process

### Step 1: Define the Design Space

State clearly what's being explored: `$ARGUMENTS`

Identify:
- **The question or design space**
- **Current approach** (if any) — what we're looking beyond
- **Constraints** — hard limits vs soft preferences
- **What "good" looks like** — evaluation criteria

### Step 2: Human Seed

Before any generation, ask the user:

> "What's your weirdest or half-baked idea for this, even if it seems wrong? Your tacit knowledge is the only genuinely independent input — models share training data, you don't."

If the user provides seeds, use them as starting points. If they say "just run it," proceed without.

### Step 3: Initial Generation

Generate 15-20 approaches. Cast wide — no evaluation yet. Optimize for volume and diversity over individual brilliance — research confirms LLMs are competitive with humans on creative volume but not at distribution extremes (Nature Human Behaviour 2025). More seeds = more raw material for perturbation.

**With llmx:** Dispatch to an external model for parallel volume while you also generate your own set.

```bash
# Model choice is pragmatic, not for "diversity" — any deep model works
llmx chat -m gemini-3.1-pro-preview \
  ${CONSTITUTION:+-f "$BRAINSTORM_DIR/context.md"} \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/external-generation.md" "
<system>
Generate approaches to the design space below. Maximize breadth — 15-20 genuinely different approaches, not variations on a theme. No feasibility filtering yet. It is $(date +%Y-%m-%d).
</system>

[Design space + constraints + human seeds if any]

For each approach: one paragraph on the mechanism and why it differs from the others."
```

Simultaneously, generate your own 15-20 approaches. Write to `$BRAINSTORM_DIR/claude-generation.md`.

**Without llmx:** Generate 15-20 approaches yourself. Write to `$BRAINSTORM_DIR/initial-generation.md`.

### Step 4: Perturbation Rounds (The Core Mechanism)

Three independent perturbation axes. **With llmx, dispatch all three in parallel** (three Bash calls in one message, `timeout: 360000`). Without llmx, run them sequentially yourself.

**Knowledge injection (before perturbation):** Query 2-3 tangential domain examples via Exa (if available) to expand the solution space before running perturbation rounds. E.g., if brainstorming about memory architectures, search for how biology, common law, or supply chain logistics handles memory/persistence. Feed retrieved examples as context into the perturbation rounds. This primes the search space with real-world mechanisms that denial alone might not surface.

First: identify the 3-5 dominant paradigms from Step 3. These are what we're escaping.

#### 4a: Denial Cascade (2 rounds)

Round 1 forbids the dominant paradigms. Round 2 forbids Round 1's output too. Novelty rises continuously with denial depth (NEOGAUGE, NAACL 2025). This is the primary divergence mechanism.

```bash
# Round 1
llmx chat -m gemini-3.1-pro-preview \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/denial-r1.md" "
<system>
DENIAL ROUND. The approaches below are FORBIDDEN — you cannot use them or their variants. Propose 5 fundamentally different approaches that share no paradigm with the forbidden list. It is $(date +%Y-%m-%d).
</system>

## Forbidden Paradigms
[List 3-5 dominant paradigms from initial generation with brief descriptions]

## Design Space
[Original design space description]

For each: the mechanism, why it differs from ALL forbidden paradigms, one reason it might work."
```

```bash
# Round 2
llmx chat -m gemini-3.1-pro-preview \
  -f "$BRAINSTORM_DIR/denial-r1.md" \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/denial-r2.md" "
<system>
DENIAL ROUND 2. Everything above is now ALSO forbidden. Go deeper — what paradigm hasn't been touched at all? What would someone from a completely unrelated field propose? 3+ approaches. It is $(date +%Y-%m-%d).
</system>

## Also Forbidden Now
[Paradigms from Round 1]

3+ approaches sharing no paradigm with anything above."
```

#### 4b: Domain Forcing

Pick 3 domains **unrelated** to the problem. Distant domains, not adjacent ones — the discomfort is the mechanism.

**Domain pools** (pick one from each row):
- **Natural systems:** evolutionary biology, immunology, ecology, neuroscience, geology, mycorrhizal networks
- **Human institutions:** common law, military logistics, jazz improvisation, kitchen brigade, air traffic control, insurance underwriting
- **Engineering:** civil engineering, control theory, materials science, packet switching, compiler design, wastewater treatment

```bash
llmx chat -m gpt-5.4 \
  --reasoning-effort medium --stream --timeout 600 \
  -o "$BRAINSTORM_DIR/domain-forcing.md" "
<system>
Map a design challenge to three unrelated domains. For each domain: what's the analogous problem, how does that domain solve it, what transfers back. It is $(date +%Y-%m-%d).
</system>

## Design Challenge
[Original design space description]

## Domain 1: [chosen domain]
Analogous problem? How does this domain solve it? What transfers back?

## Domain 2: [chosen domain]
Same.

## Domain 3: [chosen domain]
Same."
```

#### 4c: Constraint Inversion

Identify 2-3 key assumptions of the current approach. Flip them. This forces the model into a different feasibility landscape where different solutions are optimal — and those solutions often transfer back.

```bash
llmx chat -m gpt-5.4 \
  --reasoning-effort medium --stream --timeout 600 \
  -o "$BRAINSTORM_DIR/constraint-inversion.md" "
<system>
For each inverted assumption, design the best solution under that altered constraint. Then identify what transfers back to reality. It is $(date +%Y-%m-%d).
</system>

## Design Space
[Original description]

## Inversion 1: [e.g., 'What if compute were free but storage cost \$1/byte?']
Best design under this constraint. What transfers back?

## Inversion 2: [e.g., 'What if we had 1000x the data but couldn't iterate?']
Best design. What transfers?

## Inversion 3: [e.g., 'What if this had to work for 50 years without updates?']
Best design. What transfers?"
```

### Step 5: Extract & Enumerate (Anti-Loss Protocol)

**Do this BEFORE synthesis.** Single-pass synthesis drops ideas.

Mechanically extract every discrete idea from all artifacts:

```bash
cat "$BRAINSTORM_DIR"/*generation*.md \
    "$BRAINSTORM_DIR"/denial-r*.md \
    "$BRAINSTORM_DIR"/domain-forcing.md \
    "$BRAINSTORM_DIR"/constraint-inversion.md \
    > "$BRAINSTORM_DIR/all-raw.md" 2>/dev/null
```

If llmx available, dispatch extraction to a fast model:

```bash
llmx chat -m gemini-3-flash-preview --timeout 120 \
  -f "$BRAINSTORM_DIR/all-raw.md" \
  -o "$BRAINSTORM_DIR/extraction.md" "
<system>
Extract every discrete idea, approach, or insight as a numbered list. One per line. Tag the source (initial/denial-r1/denial-r2/domain/constraint). Do not evaluate — extract mechanically.
</system>

Extract all discrete ideas from the brainstorm artifacts."
```

If no llmx, extract yourself. Then build the disposition table:

```markdown
## Disposition Table
| ID  | Idea (short) | Source | Disposition | Reason |
|-----|-------------|--------|-------------|--------|
| I3  | Event-sourced memory | Initial | EXPLORE | Novel, low maintenance |
| D1  | Append-only log | Denial R1 | MERGE w/ I3 | Same paradigm |
| D5  | No memory at all | Denial R2 | EXPLORE | Radical simplification |
| F2  | Immune system model | Domain | PARK | Interesting, no path yet |
| C1  | Offline-first design | Constraint | EXPLORE | Transfers well |
```

Dispositions: `EXPLORE` (pursue), `PARK` (not now), `REJECT` (bad fit), `MERGE WITH [ID]` (dedup).

For EXPLORE items, note which technique generated it (initial/denial/domain/constraint/knowledge-injection) to track which methods produce the most useful ideas across sessions.

**Coverage check:** Every extracted item must have a disposition. Count totals.

### Step 6: Synthesize

```markdown
## Brainstorm: [topic]
**Date:** YYYY-MM-DD
**Perturbation:** Denial ×2, Domain forcing ×3, Constraint inversion ×3
**Human seeds:** [yes/no]
**Extraction:** N items total → E explore, P parked, R rejected

### Ideas to Explore (ranked by novelty × feasibility)
| Rank | ID(s) | Idea | Why Non-Obvious | Maintenance | Composability |
|------|-------|------|----------------|--------|------|

### Parked
| ID | Idea | Why Parked |

### Rejected
| ID | Idea | Why Rejected |

### Paradigm Gaps
What design space was NOT covered? What domains or constraints went unexplored?

### Suggested Next Step
Which 1-2 ideas to prototype first? Cheapest validation?
```

Save to `$BRAINSTORM_DIR/synthesis.md`.

### Step 7: Bridge to Action

If EXPLORE items suggest implementation:

> "Brainstorm identified N ideas worth exploring. Want a plan for the top 1-2, or `/model-review` to stress-test a specific idea?"

Don't auto-implement — divergent ideas need convergent validation first.

## Anti-Patterns

- **Evaluating during generation.** Steps 3-4 generate. Steps 5-6 evaluate. Don't mix.
- **Skipping denial rounds.** Initial generation IS the attractor basin. Denial is how you escape it.
- **"Related" domains for domain forcing.** Adjacent fields converge to the same basin. Pick distant domains.
- **Implementing brainstorm output directly.** Prototype cheaply or stress-test with `/model-review` first.
- **Synthesizing without extracting.** Drops ideas silently. Always extract first.
- **Treating model choice as the diversity mechanism.** The prompting structure (denial, domains, inversions) produces divergence. Model choice is for volume and availability.

$ARGUMENTS
