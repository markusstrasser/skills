---
name: brainstorm
description: Multi-model divergent ideation via llmx. Dispatches to Gemini 3.1 Pro (wild generator) and GPT-5.4 (structured ideation), then runs a denial round to break Artificial Hivemind convergence. For convergent critique, use /model-review instead.
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

# Multi-Model Brainstorming

You are orchestrating divergent ideation across models. The goal is novelty — ideas that no single model would produce alone. Same-model brainstorming converges to the same ideas (Artificial Hivemind). Cross-model with denial prompting breaks this.

**This skill is DIVERGENT only.** For convergent critique (find errors, verify claims), use `/model-review`.

## Prerequisites

- `llmx` CLI installed (`which llmx`)
- API keys configured for Google (Gemini) and OpenAI (GPT)

## Dispatch Models

| Role | Model | Why |
|------|-------|-----|
| **Wild generator** | Gemini 3.1 Pro (`gemini-3.1-pro-preview`) | Maximize novelty, ignore feasibility. Large context for cross-domain mapping. |
| **Structured ideation** | GPT-5.4 (`gpt-5.4 --reasoning-effort medium --stream --timeout 600`) | Feasibility-assessed ideas. Medium reasoning = broader exploration, less tunnel vision. |
| **Denial round** | Gemini 3.1 Pro | Cheapest deep model for counter-proposals against dominant paradigms. |
| **Extraction** | Flash / GPT-5.3 Instant | Mechanical extraction in Step 4 — fast models do this equally well. |

## Pre-Flight: Constitutional Check

Before building context, check if the project has constitutional documents:

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

- **If found:** Inject as preamble. Instruct models to brainstorm within project principles, not their own priors.
- **If neither exists:** Proceed — brainstorming still has value without constitutional grounding.

## The Process

### Step 1: Define the Design Space

State clearly what's being explored: `$ARGUMENTS`

Identify:
- **The question or design space** to explore
- **Current approach** (if any) — what exists that we're looking beyond
- **Constraints** — hard limits vs soft preferences
- **What "good" looks like** — how will ideas be evaluated?

### Step 2: Bundle Context

Build compact context. Brainstorming needs enough context to understand the design space, not full codebases.

**Output directory setup:**
```bash
TOPIC_SLUG=$(echo "$TOPIC" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//;s/-$//' | cut -c1-40)
REVIEW_ID=$(openssl rand -hex 3)
BRAINSTORM_DIR=".brainstorm/$(date +%Y-%m-%d)-${TOPIC_SLUG}-${REVIEW_ID}"
mkdir -p "$BRAINSTORM_DIR"
```

**Constitutional prefix (if found):**
```bash
if [ -n "$CONSTITUTION" ]; then
  for f in "$BRAINSTORM_DIR/gemini-context.md" "$BRAINSTORM_DIR/gpt-context.md"; do
    echo -e "# PROJECT CONSTITUTION\nBrainstorm within these principles.\n" > "$f"
    cat "$CONSTITUTION" >> "$f"
    [ -n "$GOALS" ] && { echo -e "\n# PROJECT GOALS\n" >> "$f"; cat "$GOALS" >> "$f"; }
  done
fi
```

Append only the relevant context (current approach, constraints, related code) to both context files. Summarize — don't dump full files.

**CRITICAL — Context size:** Compact context before dispatch. 50K context = 5-10 min API calls (get killed). 2K summary = fast. Summarize key points rather than concatenating full files.

### Step 3: Dispatch Brainstorms (Parallel)

**CRITICAL: Fire both Bash calls in a SINGLE message (two parallel tool calls).** Both models run independently — dispatch simultaneously to halve wall-clock time.

**IMPORTANT — Bash timeout:** Set `timeout: 360000` (6 minutes) on the Bash tool call. The default 120s kills the process before llmx finishes.

**Output capture:** Use `--output FILE` (or `-o FILE`). Never use `> file` shell redirects with llmx.

**NEVER downgrade models on failure.** If Pro or GPT-5.4 fails, diagnose (stderr, exit code, `llmx --debug`). Never swap to Flash or GPT-5.3 — you lose the deep thinking.

```bash
GEMINI_MODEL="gemini-3.1-pro-preview"
GEMINI_MAX_TOKENS="--max-tokens 65536"

GPT_MODEL="gpt-5.4"
GPT_EFFORT="--reasoning-effort medium --stream"
GPT_TIMEOUT="--timeout 600"
```

**Gemini — Wild Generator (maximize novelty):**

Gemini's role is the *wild generator* — maximize novelty, ignore feasibility. This is asymmetric by design: Gemini goes wide, GPT goes deep.

```bash
llmx chat -m $GEMINI_MODEL \
  -f "$BRAINSTORM_DIR/gemini-context.md" \
  $GEMINI_MAX_TOKENS --timeout 300 \
  -o "$BRAINSTORM_DIR/gemini-brainstorm.md" "
<system>
You are the wild generator. Maximize novelty. Ignore feasibility, cost, and practicality — another model handles that. Your job is ideas that nobody else would propose. Challenge every assumption. What would a completely different paradigm look like? It is $(date +%Y-%m-%d).
</system>

[Describe the design space to explore]

## 1. Alternative Architectures
3 fundamentally different approaches. Not variations — genuinely different paradigms.

## 2. What Adjacent Fields Do Differently
Patterns from other domains that could apply here. Cite specific systems or papers.

## 3. The Unconventional Idea
The approach that seems wrong but might work. Explain why it could succeed despite looking odd.

## 4. What's Being Over-Engineered
Where is complexity not earning its keep? What could be radically simplified?

## 5. Blind Spots
What am I (Gemini) missing because of my training distribution? Where should my creativity be distrusted?
"
```

**GPT — Structured Ideation:**
```bash
llmx chat -m $GPT_MODEL \
  -f "$BRAINSTORM_DIR/gpt-context.md" \
  $GPT_EFFORT $GPT_TIMEOUT \
  -o "$BRAINSTORM_DIR/gpt-brainstorm.md" "
<system>
Generate novel approaches with feasibility assessment.
</system>

[Describe the design space to explore]

## 1. Idea Generation (10 ideas)
Quick-fire: 10 approaches ranked by novelty. For each: one sentence + feasibility (High/Medium/Low).

## 2. Deep Dive on Top 3
For each: architecture sketch, estimated effort, risk, what makes it non-obvious.

## 3. Combination Plays
Ideas that work poorly alone but well together. Cross-pollinate from the list above.

## 4. What Would Break Each Approach
Pre-mortem: for the top 3, what's the most likely failure mode?

## 5. Where I'm Likely Wrong
What am I (GPT-5.4) probably biased toward? Where should my suggestions be distrusted?
"
```

### Step 3b: Denial Round (Mandatory)

After receiving both outputs, identify the 2-3 dominant paradigms across both responses. Re-query Gemini to catch Artificial Hivemind convergence — both models often propose the same paradigms despite generating independently:

```bash
llmx chat -m $GEMINI_MODEL \
  -f "$BRAINSTORM_DIR/gemini-brainstorm.md" \
  $GEMINI_MAX_TOKENS --timeout 300 \
  -o "$BRAINSTORM_DIR/denial-round.md" "
<system>
You are generating COUNTER-proposals. The ideas below have already been proposed. Your job is to find what was MISSED. It is $(date +%Y-%m-%d).
</system>

The following paradigms were proposed by two independent models:
[List the 2-3 dominant paradigms from both outputs]

Now propose 3 approaches that do NOT use any of these paradigms. What fundamentally different angle has been missed? Think from adjacent domains, adversarial perspectives, or radical simplification.
"
```

### Step 4: Extract & Enumerate (Anti-Loss Protocol)

**Do this BEFORE writing any synthesis.** Single-pass synthesis drops ideas silently.

Use fast models from a *different family* than the generator for extraction (cross-family avoids self-preference bias):

```bash
# Extract Gemini's ideas with GPT-5.3 Instant
llmx chat -m gpt-5.3-chat-latest --stream --timeout 120 \
  -f "$BRAINSTORM_DIR/gemini-brainstorm.md" \
  -o "$BRAINSTORM_DIR/gemini-extraction.md" "
<system>
Extract every discrete idea, approach, or insight as a numbered list. One item per line. Do not evaluate or filter — extract mechanically.
</system>

Extract all discrete ideas from this brainstorm."

# Extract GPT's ideas with Flash
llmx chat -m gemini-3-flash-preview --timeout 120 \
  -f "$BRAINSTORM_DIR/gpt-brainstorm.md" \
  -o "$BRAINSTORM_DIR/gpt-extraction.md" "
<system>
Extract every discrete idea, approach, or insight as a numbered list. One item per line. Do not evaluate or filter — extract mechanically.
</system>

Extract all discrete ideas from this brainstorm."

# Extract denial round with Flash
llmx chat -m gemini-3-flash-preview --timeout 120 \
  -f "$BRAINSTORM_DIR/denial-round.md" \
  -o "$BRAINSTORM_DIR/denial-extraction.md" "
<system>
Extract every discrete idea as a numbered list. One item per line.
</system>

Extract all discrete ideas."
```

**Disposition table.** Every extracted item gets a verdict:

```markdown
## Disposition Table
| ID  | Idea (short) | Source | Disposition | Reason |
|-----|-------------|--------|-------------|--------|
| G1  | Event-sourced memory | Gemini | EXPLORE | Novel, low effort to prototype |
| G2  | Biological immune system model | Gemini | PARK | Interesting but no clear path |
| P1  | Append-only log + views | GPT | EXPLORE | Feasible, overlaps G1 |
| D1  | No memory at all | Denial | EXPLORE | Radical simplification worth testing |
| P5  | Kubernetes operator | GPT | REJECT | Scale mismatch |
```

Valid dispositions: `EXPLORE` (worth pursuing), `PARK` (interesting, not now), `REJECT` (bad fit), `MERGE WITH [ID]` (dedup).

**Coverage check:** Count total extracted, explore, park, reject, merged. Every ID must have a disposition. Save to `$BRAINSTORM_DIR/extraction.md`.

### Step 5: Synthesize

Build synthesis from the disposition table. Group EXPLORE items by paradigm family.

**Output format:**

```markdown
## Brainstorm: [topic]
**Date:** YYYY-MM-DD
**Models:** Gemini 3.1 Pro (wild), GPT-5.4 (structured), Gemini 3.1 Pro (denial)
**Constitutional anchoring:** Yes/No
**Extraction:** N items extracted, E explore, P parked, R rejected

### Ideas to Explore (ranked by novelty x feasibility)
| Rank | ID(s) | Idea | Why It's Non-Obvious | Effort | Risk |
|------|-------|------|---------------------|--------|------|

### Parked (interesting, not now)
| ID | Idea | Why Parked |

### Rejected
| ID | Idea | Why Rejected |

### Paradigm Gaps
What design space was NOT covered by any model? What domains weren't consulted?

### Suggested Next Step
Which 1-2 ideas should be prototyped first? What's the cheapest validation?
```

Save synthesis to `$BRAINSTORM_DIR/synthesis.md`.

### Step 6: Bridge to Action (Optional)

If EXPLORE items suggest concrete implementation:

> "Brainstorm identified N ideas worth exploring. Want me to write a plan for the top 1-2, or run `/model-review` on a specific idea to stress-test it?"

Don't auto-implement brainstorm output — divergent ideas need convergent validation first.

## Known Model Biases (Brainstorming Context)

| Model | Bias | Countermeasure |
|-------|------|----------------|
| **Gemini 3.1 Pro** | Enterprise-pattern gravity — "wild" ideas still look like Google architecture | Watch for Kubernetes, Spanner, Pub/Sub showing up as "unconventional" |
| **Gemini 3.1 Pro** | Self-recommendation — suggests Gemini/Google services | Flag any self-serving suggestions |
| **GPT-5.4** | Feasibility conservatism — kills novel ideas too early with "but scaling..." | Medium reasoning-effort helps; still watch for premature narrowing |
| **GPT-5.4** | Production-grade creep — adds auth, monitoring, CI/CD to brainstorm sketches | Remind: brainstorm, not architecture review |
| **Both** | Artificial Hivemind — same paradigms despite independent generation | Denial round is the countermeasure. If denial round ALSO converges, flag it. |

## Anti-Patterns

- **Mixing brainstorming with critique.** This skill generates ideas. Don't evaluate feasibility during generation (that's GPT's structured role). Don't ask "what's wrong with this codebase" — use `/model-review`.
- **Skipping the denial round.** The denial round catches the 2-3 paradigms both models converge on. Without it, you get the Artificial Hivemind — two models producing the same ideas with different words.
- **Implementing brainstorm output directly.** Divergent ideas need convergent validation. Prototype the cheapest version or stress-test with `/model-review` before building.
- **Synthesizing without extracting.** Same anti-pattern as model-review — single-pass synthesis drops ideas. Always extract first.
- **Dumping full codebases as context.** Brainstorming needs design space understanding, not line-by-line code. Summarize the current approach and constraints.

$ARGUMENTS
