<!-- Reference file for brainstorm skill. Loaded on demand by the contradiction axis (Step 3d). -->
# TRIZ Inventive Principles — Contradiction Axis Lookup

Provenance: the 40 principles are Altshuller's classic canon (stable, public). The
software/agent glosses and the pair-routing table below are OUR semantic adaptation —
they are NOT a reproduction of the classic 39×39 contradiction matrix. Cite as
"TRIZ-derived", never as Altshuller's matrix cells.

## Procedure (Step 3d)

1. Restate the problem as 2-3 contradictions: "improve **X** without worsening **Y**."
   Use the parameter vocabulary below; name real system parameters, not abstractions.
2. For each pair, look up the routing table. Pair not listed → scan the full 40 and pick
   3-5 whose *mechanism* plausibly bites. The table is a routing cache, not the authority.
3. Generate **one idea per principle**. The idea must instantiate the principle's
   mechanism in the actual system — citing the principle name is not applying it.
4. Keep only resolutions (contradiction dissolves), not tradeoff points.

## Contradiction parameters (agent/software systems)

capability depth · maintenance surface · autonomy · error blast-radius · context richness ·
token cost · latency · throughput · determinism · flexibility · observability ·
verification cost · coupling · human attention · recall/coverage · precision · generality ·
per-case quality

## Pair routing table (seed mappings — semantic, not matrix cells)

| Improve X | Without worsening Y | Candidate principles |
|---|---|---|
| capability depth | maintenance surface | 1 segmentation · 5 merging · 6 universality · 40 composites |
| autonomy | error blast-radius | 9 prior anti-action · 11 cushioning · 23 feedback · 24 intermediary |
| context richness | token cost | 2 taking out · 3 local quality · 7 nesting · 17 another dimension |
| latency / speed | verification confidence | 10 prior action · 16 partial/excessive · 19 periodic action · 21 skipping |
| flexibility | determinism | 13 inversion · 15 dynamization · 35 parameter change |
| recall / coverage | precision | 16 partial/excessive · 22 harm→benefit · 27 cheap disposables |
| throughput | human attention | 12 equipotentiality · 23 feedback · 25 self-service |
| generality | per-case quality | 3 local quality · 33 homogeneity · 40 composites |
| observability | performance / cost | 26 copying · 28 sensing substitution · 32 visibility change |
| decoupling | end-to-end coherence | 7 nesting · 24 intermediary · 34 discard & recover |

## The 40 principles (agent/software glosses)

| # | Principle | Gloss for agent/software systems |
|---|-----------|----------------------------------|
| 1 | Segmentation | Split the monolith into independent parts; make stages/agents separable and independently replaceable |
| 2 | Taking out | Extract the interfering part (the expensive check, the noisy context) and run it elsewhere — subagent, offline, precomputed |
| 3 | Local quality | Stop treating the system uniformly; give each part the properties its local job needs (per-stage models, per-path budgets) |
| 4 | Asymmetry | Break a symmetric design; if already asymmetric, sharpen it (read path ≠ write path, hot ≠ cold lane) |
| 5 | Merging | Fuse identical/adjacent operations in space or time (batch, coalesce, shared pass) |
| 6 | Universality | One component absorbs several functions so others can be deleted |
| 7 | Nested doll | Put one structure inside another (layered caches, wrapped contexts, progressive detail) |
| 8 | Counterweight | Offset a liability by coupling it to something that lifts it (pair a costly pass with value it subsidizes) |
| 9 | Preliminary anti-action | Pre-apply the counter-stress before acting (pre-register the prediction, stage the rollback, adversarial pre-mortem) |
| 10 | Preliminary action | Do the required change before it's needed (precompute, warm, stage) so the critical moment is cheap |
| 11 | Cushioning | Prepare compensation for low-reliability steps in advance (checkpoints, fallbacks that fail loud) |
| 12 | Equipotentiality | Remove the need to move between levels (meet the data/decision where it is; no lift-and-shift between stores) |
| 13 | The other way round | Invert the action/roles (pull→push, caller→callee, generate-then-verify → verify-then-generate) |
| 14 | Curvature | Replace the straight path with a curved/cyclic one (linear pipeline → loop with feedback) |
| 15 | Dynamization | Make the rigid thing adaptive; let parts move relative to each other (runtime-tunable params, swappable stages) |
| 16 | Partial or excessive action | If exact is hard, deliberately under- or over-shoot then correct (overgenerate + filter, sample + extrapolate) |
| 17 | Another dimension | Add an axis: stack layers, use the orthogonal view (multi-view index, time as a dimension, hierarchy over flat) |
| 18 | Resonance | Match the intervention's frequency to the system's natural rhythm (align cadence to when state actually changes) |
| 19 | Periodic action | Replace continuous with periodic/pulsed action; use the pauses for other work |
| 20 | Continuity of useful action | Eliminate idle strokes; every part works all the time (pipeline the waits, background the grinds) |
| 21 | Skipping | Run the harmful/risky phase at maximum speed (fast destructive window, quick cutover instead of long coexistence) |
| 22 | Harm to benefit | Use the harmful factor as the resource (failures become training data, noise becomes a probe) |
| 23 | Feedback | Introduce/strengthen the feedback loop; if it exists, change its sign or gain |
| 24 | Intermediary | Insert a mediating carrier that can be removed later (gateway, outbox, broker) |
| 25 | Self-service | The system serves/repairs itself using its own by-products (self-indexing, self-describing, exhaust-fed loops) |
| 26 | Copying | Use a cheap copy instead of the fragile/expensive original (shadow run, replica, simulation, dry-run) |
| 27 | Cheap disposables | Replace one expensive durable with many cheap short-lived ones (throwaway scouts, ephemeral worktrees) |
| 28 | Sensing substitution | Replace direct mechanics with fields/signals (watch events instead of polling state; measure, don't inspect) |
| 29 | Fluidity | Replace rigid links with flowing ones (streams over batches, queues over calls) |
| 30 | Flexible membranes | Thin isolating boundary instead of a thick wall (narrow interface, permission seam, sandbox skin) |
| 31 | Porosity | Deliberate holes that let selected things pass (allowlists, escape hatches, sampling ports) |
| 32 | Visibility change | Change how visible things are (color/tag/annotate state; make the invisible failure loud) |
| 33 | Homogeneity | Interacting parts made of the same material (one schema/vocabulary across producers and consumers) |
| 34 | Discard & recover | Parts that dissolve after use or regenerate in place (auto-cleanup, rederivable artifacts, no residue) |
| 35 | Parameter change | Change the phase/concentration/state of the thing itself (sync→async, text→structured, eager→lazy) |
| 36 | Phase transitions | Exploit the effects AT the transition point (act on compaction, session boundary, deploy moment) |
| 37 | Relative expansion | Exploit parts responding differently to the same driver (tiered responses to load: cheap lane grows, expensive lane holds) |
| 38 | Enriched atmosphere | Run in an enriched environment (inject curated context/priors instead of raw ambient input) |
| 39 | Inert atmosphere | Run in a neutralized environment (isolation, clean-room repro, frozen deps) |
| 40 | Composites | Combine dissimilar materials where one uniform one fails (heterogeneous ensemble: rules + model + human gate) |
