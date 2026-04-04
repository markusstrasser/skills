---
name: brainstorm
description: Divergent ideation via systematic perturbation — denial cascades, domain forcing, constraint inversion. Multi-model dispatch optional (volume, not diversity). For convergent critique, use /model-review.
argument-hint: "[--quick|--deep] [--axes denial,domain,constraint] [--domains 'jazz, geology, ...'] [--n-ideas N] design space to explore"
effort: high
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

**Late-stage warning:** When a frontier is mature, this skill should produce fewer, sharper ideas, not preserve the same idea count with weaker variants. One strong perturbation survivor is enough. If forced-domain rounds only yield reframings, stop and hand back to convergent filtering.

## Parameters

Parse `$ARGUMENTS` for these optional flags (order doesn't matter, remaining text is the topic):

| Flag | Values | Default | Effect |
|------|--------|---------|--------|
| `--quick` | — | off | 1 denial round, 2 domains, skip constraint inversion. ~5 ideas. |
| `--deep` | — | off | 3 denial rounds, 4 domains, 4 inversions. Maximum divergence. |
| `--axes` | comma-separated: `denial`, `domain`, `constraint` | all three | Run only specified perturbation axes |
| `--domains` | quoted comma-separated domain names | auto-select | Override domain forcing domains (e.g., `--domains "jazz, geology, packet switching"`) |
| `--n-ideas` | integer | 15 | Target idea count per generation round |
| `--no-llmx` | — | off | Run everything locally, no external model dispatch |

**Effort presets:**
- **default:** 2 denial rounds, 3 domains, 3 inversions, ~15 ideas/round
- **`--quick`:** 1 denial round, 2 domains, no inversions, ~5 ideas/round. Good for scoping or when you need fast directional options.
- **`--deep`:** 3 denial rounds, 4 domains, 4 inversions, ~20 ideas/round. Full exploration.

## Prerequisites

- `llmx` CLI optional — skill works without it (you run all rounds). With llmx, perturbation rounds run in parallel for speed. Use `--no-llmx` to force local-only.

## Pre-Flight

### Dedup Check

Before starting, check for recent brainstorms on overlapping topics:

```bash
RECENT=$(find .brainstorm/ -name "synthesis.md" -mtime -1 2>/dev/null)
if [ -n "$RECENT" ]; then
  echo "Recent brainstorm(s) found:"
  for f in $RECENT; do echo "  $f"; head -5 "$f"; echo "---"; done
fi
```

If a brainstorm from the last 24h covers the same domain, read the existing synthesis first and brainstorm only for gaps. Do not re-run the full perturbation pipeline on an already-explored topic.

Also check git for cross-session brainstorms (parallel sessions won't see each other's uncommitted directories):

```bash
git log --oneline -10 --all | grep -i "brainstorm"
```

If recent commits mention brainstorm on the same topic, read those results before starting a new run.

If the space has already been explored heavily, switch your target from "volume" to "one non-duplicate survivor or clean exhaustion proof."

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

### Step 2: Initial Generation

Generate `$N_IDEAS` approaches (default 15, or per `--n-ideas`). Cast wide — no evaluation yet. Optimize for volume and diversity over individual brilliance — research confirms LLMs are competitive with humans on creative volume but not at distribution extremes (Nature Human Behaviour 2025). More seeds = more raw material for perturbation.

If the user included seed ideas in their prompt, use those as starting points and diversify from there.

**With llmx (and not `--no-llmx`):** Dispatch to an external model for parallel volume while you also generate your own set.

```bash
llmx chat -m gemini-3.1-pro-preview \
  ${CONSTITUTION:+-f "$BRAINSTORM_DIR/context.md"} \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/external-generation.md" "
<system>
Generate approaches to the design space below. Maximize breadth — $N_IDEAS genuinely different approaches, not variations on a theme. No feasibility filtering yet. It is $(date +%Y-%m-%d).
</system>

[Design space + constraints + user-provided seeds if any]

For each approach: one paragraph on the mechanism and why it differs from the others."
```

Simultaneously, generate your own `$N_IDEAS` approaches. Write to `$BRAINSTORM_DIR/claude-generation.md`.

**Without llmx (or `--no-llmx`):** Generate `$N_IDEAS` approaches yourself. Write to `$BRAINSTORM_DIR/initial-generation.md`.

### Step 3: Perturbation Rounds (The Core Mechanism)

Run the perturbation axes specified by `--axes` (default: all three). **With llmx, dispatch active axes in parallel** (multiple Bash calls in one message, `timeout: 360000`). Without llmx, run them sequentially yourself.

**Skip an axis entirely if excluded by `--axes`.** With `--quick`, reduce each axis (see preset table above).

**Knowledge injection (before perturbation):** Query 2-3 tangential domain examples via Exa (if available) to expand the solution space before running perturbation rounds. E.g., if brainstorming about memory architectures, search for how biology, common law, or supply chain logistics handles memory/persistence. Feed retrieved examples as context into the perturbation rounds. This primes the search space with real-world mechanisms that denial alone might not surface.

After one forced-domain pass on a mature frontier, hand off to a convergent step:
- discard duplicates
- discard ideas with no caller
- discard ideas that are just tighter phrasing for an existing operator

Do not keep forcing more domains just because the first forced pass returned something interesting.

First: identify the 3-5 dominant paradigms from Step 3. These are what we're escaping.

#### 3a: Denial Cascade

Default: 2 rounds. `--quick`: 1 round. `--deep`: 3 rounds. Novelty rises continuously with denial depth (NEOGAUGE, NAACL 2025). This is the primary divergence mechanism.

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

#### 3b: Domain Forcing

If `--domains` specified, use those. Otherwise pick 3 domains **unrelated** to the problem (`--quick`: 2, `--deep`: 4). Distant domains, not adjacent ones — the discomfort is the mechanism.

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

#### 3c: Constraint Inversion

**Skipped in `--quick` mode.** Default: 3 inversions. `--deep`: 4 inversions.

Identify key assumptions of the current approach. Flip them. This forces the model into a different feasibility landscape where different solutions are optimal — and those solutions often transfer back.

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

### Step 4: Extract & Enumerate (Anti-Loss Protocol)

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

### Step 5: Synthesize

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

### Step 5.5: Pain-Point Gate (MANDATORY before implementation)

Before offering to plan or implement ANY explore item, verify it solves a real problem:

1. `git log --oneline --all | grep -i "<topic keywords>"` — actual incidents
2. `grep -r "<topic>" ~/.claude/projects/*/memory/` — session pain moments
3. For each EXPLORE item: "This would have prevented [specific incident] on [date]"
4. If no incident: mark `SPECULATIVE` in disposition. Default to PARK, not EXPLORE.

**Why this exists:** Brainstorm session (2026-03-26) generated 47 ideas → 12 explored → 7 planned → 1 built. 6/7 layers defended against hypothetical problems with zero incident history. The brainstorm correctly generated ideas; the failure was bridging to implementation without checking if the problems were real. Absence of a feature ≠ presence of a problem.

### Step 6: Bridge to Action

If EXPLORE items survive the pain-point gate:

> "Brainstorm identified N ideas worth exploring (M survived pain-point gate). Want a plan for the top 1-2, or `/model-review` to stress-test a specific idea?"

Don't auto-implement — divergent ideas need convergent validation first.

## Anti-Patterns

- **Evaluating during generation.** Steps 2-3 generate. Steps 4-5 evaluate. Don't mix.
- **Skipping denial rounds.** Initial generation IS the attractor basin. Denial is how you escape it.
- **"Related" domains for domain forcing.** Adjacent fields converge to the same basin. Pick distant domains.
- **Implementing brainstorm output directly.** Prototype cheaply or stress-test with `/model-review` first.
- **Synthesizing without extracting.** Drops ideas silently. Always extract first.
- **Treating model choice as the diversity mechanism.** The prompting structure (denial, domains, inversions) produces divergence. Model choice is for volume and availability.

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Duplicate runs — brainstorm dispatched 3x to same model when parallel subagent calls failed silently. Check subagent output before re-dispatching.**
