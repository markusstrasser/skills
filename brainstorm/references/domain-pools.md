<!-- Reference file for brainstorm skill. Loaded on demand. -->
# Domain Pools & Perturbation Axis Details

## Domain Forcing Pools

Pick distant domains, not adjacent ones — the discomfort is the mechanism.

| Row | Domains |
|-----|---------|
| **Natural systems** | evolutionary biology, immunology, ecology, neuroscience, geology, mycorrhizal networks |
| **Human institutions** | common law, military logistics, jazz improvisation, kitchen brigade, air traffic control, insurance underwriting |
| **Engineering** | civil engineering, control theory, materials science, packet switching, compiler design, wastewater treatment |

Pick one from each row. Record the row label in `matrix.json` as `domain_row`. If `--domains`
is specified, use those instead and still preserve the closest row or mark `domain_row: "custom"`.

## Knowledge Injection (before perturbation)

Query 2-3 tangential domain examples via Exa (if available) to expand the solution space before running perturbation rounds. E.g., if brainstorming about memory architectures, search for how biology, common law, or supply chain logistics handles memory/persistence. Feed retrieved examples as context into the perturbation rounds. This primes the search space with real-world mechanisms that denial alone might not surface.

## Perturbation Axis Presets

| Axis | `--quick` | Default | `--deep` |
|------|-----------|---------|----------|
| Denial rounds | 1 | 2 | 3 |
| Domain forcing domains | 2 | 3 | 4 |
| Constraint inversions | skip | 3 | 4 |
| Ideas per round | ~5 | ~15 | ~20 |

## Mature-Frontier Behavior

After one forced-domain pass on a mature frontier, hand off to a convergent step:
- discard duplicates
- discard ideas with no caller
- discard ideas that are just tighter phrasing for an existing operator

Do not keep forcing more domains just because the first forced pass returned something interesting.
