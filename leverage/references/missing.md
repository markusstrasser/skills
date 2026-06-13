# Leverage mode: `missing` — negative-space sweep

> Divergent discovery of what's MISSING from an optimized system. Not "what should we
> improve?" but "what entire categories have we not even considered?" Fire when a domain is
> heavily optimized and you suspect blind spots: "what am I missing?", "blind spots", "negative
> space". This is the absence-detection mode of `/leverage` — the core mode hunts 10-100x on a
> *known* surface; this mode hunts the surfaces you never put on an axis at all.

**This is NOT:** the core leverage loop (which 10x's a known surface), `/brainstorm` (ideas
within a frame), `/critique` (critiques existing work), or `/research` (investigates a known
question). It is the systematic search for the unframed.

## Phase 0: Pre-Flight (MANDATORY)

### 0a. Build the Exclusion List

The exclusion list IS the methodology. Without it, you'll "discover" what's already there.

```
1. Identify ALL docs where the domain's items live (protocol, recommendations, parking lot, dropped items, frontier)
2. Extract every item mentioned — active, parked, dropped, deferred, rejected
3. This is the exclusion list. Every search query must exclude these items.
```

**Retro-driven rule:** After building the exclusion list, grep the target docs for each
candidate BEFORE claiming it as a "find." Items get "discovered" that were already in the
parking lot. Check first.

### 0b. Check Meta-Knowledge / prior art

Before designing the sweep methodology for a domain, check for existing frameworks: Smithson's
ignorance taxonomy, pertinent negatives (Hsu et al.), via negativa are documented prior art —
use them instead of reinventing. For a science domain, check the project corpus + `decisions/`
first.

### 0c. Check the user's own research history

The user's past curiosity is the highest-signal discovery channel — search prior sessions /
notes for the domain before searching the world. Things get researched twice and fall through
when this step is skipped.

## Phase 1: Define Axes and Perspectives

**Axes** are the optimization dimensions of the domain (health: kynurenine, sleep,
inflammation…; codebase: performance, security, reliability, DX…). Extract them from existing
docs — they're already defined. The negative space is what's NOT covered by these axes, AND
what's on an axis but was never searched.

**Perspectives (STORM-style):** choose N professional perspectives that would ask DIFFERENT
QUESTIONS about the domain. Different perspectives generate different questions, which reach
different literatures — this is the primary coverage mechanism (Stanford STORM, NAACL 2024).

Rules: perspectives from different professional domains (not 3 types of doctor); at least one
adversarial ("what's overhyped?"); at least one from a completely adjacent field; each
perspective generates its own queries.

Codebase example: 1) SRE → failure modes, observability gaps; 2) Security researcher → attack
surface, supply chain; 3) End user → UX pain nobody measures; 4) Performance engineer → cold
paths, tail latency; 5) New hire → onboarding friction, undocumented assumptions.

## Phase 2: Search with Exclusion

For each axis × perspective combination:

```
"FROM THE PERSPECTIVE OF A [perspective]: What [items/interventions/approaches]
have [evidence type] for [axis], EXCLUDING: [exclusion list]?
Looking for overlooked candidates. Include [dose/details/specs]."
```

Tool routing: use the `/research` skill's tool table (Perplexity for factual lookups, S2 for
papers, Exa for semantic web search, Brave for news). Budget ~3-5 queries per perspective;
don't shotgun — each query is shaped by the perspective.

## Phase 3: Safety / feasibility gate (domain-specific)

Every candidate passes the domain's gate before being listed. Health: G6PD + CYP interaction +
current-stack overlap. Codebase: breaking-change risk + dependency evaluation + maintenance
cost. Financial: regulatory + tax + counterparty. Failures are listed as "rejected" with the
reason, not silently dropped.

## Phase 4: Document Pertinent Negatives

**This is half the value of the sweep.** Document what you searched for and DID NOT find:

```markdown
## Pertinent Negatives (Expected but NOT Found)
| Expected | Result | Diagnostic value |
|----------|--------|-----------------|
| Pink noise for slow-wave enhancement | NO PSG data | Don't buy |
| PEMF devices for recovery | NO human evidence | Don't buy |
```

Pertinent negatives are negative knowledge — more durable than positive (Taleb, via negativa).
They prevent future wasted purchases, research time, and conversation loops.

## Phase 5: Output

```markdown
# Negative-Space Sweep: [Domain]
**Date / Category / Perspectives / Exclusion list:** [N items from M docs]

## Tier 1: Strong Candidates (multi-axis fit, evidence > threshold)
[candidate, axes hit, evidence grade, safety gate, cost, action]

## Tier 2: Conditional Candidates  [same format, conditions noted]

## Pertinent Negatives  [expected, result, diagnostic value]

## Method Notes — perspectives used (which found what); category gaps (→ next sweep); axes gaps
```

Save to `docs/research/negative_space_[domain]_[date].md` (or return inline for a quick tier).

## Phase 6: Category Rotation

After a sweep, note which category was searched and suggest the next. **Don't sweep the same
category twice in a row** — same category = convergent within frame. Supplements → devices →
dietary patterns → environment.

## Anti-Patterns

- **"Discovering" items already in the parking lot.** Always grep first.
- **Single-perspective search.** One perspective = one frame = convergent. 5 perspectives ≈ 3×
  genuine unknowns (empirical: sweep #1 found 1, sweep #2 found 3).
- **Searching the same category twice.** Not divergent.
- **Skipping pertinent negatives.** Half the value is documenting what DOESN'T exist.
- **No exclusion list.** Without it you'll find what's already there and call it a discovery.
- **Evaluating during search.** Search broadly first, gate second.

## Evidence

- STORM (Stanford, NAACL 2024): perspective diversity → +25% organization, +10% breadth.
- Pertinent negatives (Hsu et al., Cognitive Science 2016): absence of expected findings is
  diagnostic, r=0.90-0.95.
- Smithson's ignorance taxonomy: structures "unknown" into actionable categories.
