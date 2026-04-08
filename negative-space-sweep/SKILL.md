---
name: negative-space-sweep
description: "Divergent discovery of what's MISSING from an optimized system. Multi-perspective search with exclusion lists, pertinent negatives, and category rotation. Use when a domain has been heavily optimized (health protocol, codebase, investment portfolio) and you suspect blind spots. The anti-convergence tool — finds the saffron, not more of the same."
argument-hint: "[domain to sweep] [--perspectives N] [--category override]"
effort: high
---

# Negative-Space Sweep

Systematic search for what's missing from an optimized system. Not "what should we improve?" but "what entire categories have we not even considered?"

**Trigger on:** "what am I missing?", "blind spots", "what else should I be doing?", "negative space", "divergent search"

**Companion skills:** `researcher` for deep-diving individual finds, `brainstorm` for ideation within a known space, `epistemics` for bio/medical claim verification.

**This is NOT:** brainstorm (which generates ideas within a frame), model-review (which critiques existing work), or researcher (which investigates a known question).

## Parameters

| Flag | Values | Default | Effect |
|------|--------|---------|--------|
| `--perspectives` | integer | 5 | Number of STORM-style professional perspectives |
| `--category` | string | auto | Override the search category (supplements, devices, exercise, environment, etc.) |
| `--quick` | — | off | 1 perspective, no pertinent negatives. ~3 queries. |
| `--axes` | comma-separated | auto-detect from domain | Override the search axes |

## Phase 0: Pre-Flight (MANDATORY)

### 0a. Build the Exclusion List

The exclusion list IS the methodology. Without it, you'll "discover" what's already there.

```
1. Identify ALL docs where the domain's items live (protocol, recommendations, parking lot, dropped items, frontier)
2. Extract every item mentioned — active, parked, dropped, deferred, rejected
3. This is the exclusion list. Every search query must exclude these items.
```

**Retro-driven rule:** After building the exclusion list, grep the target docs for each candidate BEFORE claiming it as a "find." PEA-LUT and NR were "discovered" in selve's first sweep — both were already in the parking lot. Embarrassing. Check first.

### 0b. Check Meta-Knowledge

Before designing the sweep methodology for a domain:
```
search_meta("negative space [domain]")
search_meta("systematic review [domain]")
```

Smithson's ignorance taxonomy, pertinent negatives (Hsu et al.), and via negativa are already documented in meta-knowledge. Use them instead of reinventing.

### 0c. Check User's Research History

Search for the user's own prior research on the domain:
```
./selve search "[domain] [keywords]" -s chatgpt,claude,raycast -k 10
```

The user's past curiosity is the highest-signal discovery channel. Saffron was researched TWICE and fell through because this step didn't exist.

## Phase 1: Define Axes and Perspectives

### Axes

Axes are the optimization dimensions of the domain. For health: kynurenine, sleep, inflammation, testosterone, etc. For a codebase: performance, security, reliability, developer experience, etc.

Extract axes from the existing docs — they're already defined (the system has been optimized along them). The negative space is what's NOT covered by these axes, AND what's on the axes but was never searched.

### Perspectives (STORM-style)

Choose N professional perspectives that would ask DIFFERENT QUESTIONS about the domain. The key insight (Stanford STORM, NAACL 2024): different perspectives generate different questions, which reach different literatures. This is the primary coverage mechanism.

**Rules:**
- Perspectives must come from different professional domains (not 3 types of doctor)
- At least one perspective should be adversarial ("what's overhyped?")
- At least one should be from a completely adjacent field
- Each perspective generates its own search queries

**Example (health domain):**
1. POTS specialist → asks about devices, PT protocols
2. Sleep medicine specialist → asks about airway, positional therapy
3. Sports physiologist → asks about exercise modalities, BFR
4. Biohacker community → asks about devices, hype vs evidence
5. Environmental medicine → asks about light, air, temperature

**Example (codebase domain):**
1. SRE → asks about failure modes, observability gaps
2. Security researcher → asks about attack surface, supply chain
3. End user → asks about UX pain points nobody measures
4. Performance engineer → asks about cold paths, tail latency
5. New hire → asks about onboarding friction, undocumented assumptions

## Phase 2: Search with Exclusion

For each axis × perspective combination:

```
"FROM THE PERSPECTIVE OF A [perspective]: What [items/interventions/approaches]
have [evidence type] for [axis], EXCLUDING: [exclusion list]?
Looking for overlooked candidates. Include [dose/details/specs]."
```

**Tool routing:** Use the `researcher` skill's tool routing table. Perplexity for factual lookups, S2 for papers, Exa for semantic web search, Brave for news.

**Budget:** ~3-5 queries per perspective. Total: perspectives × 3-5 queries. Don't shotgun — each query should be shaped by the perspective.

## Phase 3: Safety Gate (domain-specific)

Every candidate must pass the domain's safety gate before being listed as a find.

**Health domain:** G6PD safety + CYP interaction check + current stack overlap assessment.
**Codebase domain:** Breaking change risk + dependency evaluation + maintenance cost.
**Financial domain:** Regulatory compliance + tax implications + counterparty risk.

Candidates that fail the safety gate are listed as "rejected" with the reason, not silently dropped.

## Phase 4: Document Pertinent Negatives

**This is half the value of the sweep.** Document what you searched for and DID NOT FIND:

```markdown
## Pertinent Negatives (Expected but NOT Found)
| Expected | Result | Diagnostic value |
|----------|--------|-----------------|
| Pink noise for slow-wave enhancement | NO PSG data | Don't buy |
| PEMF devices for recovery | NO human evidence | Don't buy |
```

Pertinent negatives prevent future wasted purchases, research time, and conversation loops. They're negative knowledge — more durable than positive (Taleb, via negativa principle from meta-knowledge).

## Phase 5: Output

```markdown
# Negative-Space Sweep: [Domain]

**Date:** YYYY-MM-DD
**Category:** [supplements | devices | exercise | environment | ...]
**Perspectives:** [list]
**Exclusion list:** [N items from M docs]

## Tier 1: Strong Candidates (multi-axis fit, evidence > threshold)
[Table: candidate, axes hit, evidence grade, safety gate, cost, action]

## Tier 2: Conditional Candidates
[Table: same format, with conditions noted]

## Pertinent Negatives
[Table: expected, result, diagnostic value]

## Method Notes
- Perspectives used: [which found what]
- Category gaps: what categories were NOT searched (→ next sweep)
- Axes gaps: what axes had no candidates (→ may indicate the axis is already well-covered OR the exclusion list is too broad)
```

Save to `docs/research/negative_space_[domain]_[date].md` (project-specific) or return inline (quick tier).

## Phase 6: Category Rotation

After completing a sweep, note which category was searched and suggest the next:

```
Last 3 sweeps:
- 2026-03-31: supplements (health)
- 2026-03-31: non-pharma devices/exercise (health)
- Next: dietary patterns? lifestyle? non-health vertical?
```

**Rule:** Don't sweep the same category twice in a row. The point is divergence — same category = convergent within frame.

## Anti-Patterns

- **"Discovering" items already in the parking lot.** Always grep first. (Retro finding #1)
- **Single-perspective search.** One perspective = one frame = convergent. 5 perspectives = 3x genuine unknowns. (Empirical: sweep #1 found 1 unknown, sweep #2 found 3.)
- **Searching the same category twice.** Supplements → supplements is not divergent. Supplements → devices → dietary patterns → environment.
- **Skipping pertinent negatives.** Half the value is documenting what DOESN'T exist. Prevents future wasted research.
- **No exclusion list.** Without exclusion, you'll find what's already there and call it a discovery.
- **Evaluating during search.** Search broadly first, safety-gate second. Don't pre-filter by feasibility during the search phase.

## Evidence: Why This Works

- STORM (Stanford, NAACL 2024): perspective diversity → +25% organization, +10% breadth
- Pertinent negatives (Hsu et al., Cognitive Science 2016): absence of expected findings is diagnostic, r=0.90-0.95 Bayesian model
- Smithson's ignorance taxonomy: structures "unknown" into actionable categories (absence → collect, inaccuracy → verify, vagueness → define)
- Session empirical (2026-03-31): 5-perspective sweep found 3 genuine unknowns vs 1 with single perspective
