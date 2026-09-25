# Forms and tools

Lookup tables for step 3 of `/figure`. The principles in SKILL.md decide; these tables only
shorten the search. Sources are in `agent-infra/research/2026-09-25-information-display-craft.md`.

## Sentence, table or chart

| The content is... | Use |
|---|---|
| One or two numbers, or a claim with no shape | **A sentence.** Numbers in the prose. |
| A trend that supports a sentence | Sentence + **inline sparkline**, labelled first/last/min/max, line weight matched to the type (Tufte) |
| Exact values the reader will look up; few rows | **Table**, sorted by the value that matters. Text beats charts for recalling exact values (Kim, Reinecke & Hullman 2017). |
| Many cells to compare | **Table with in-cell encoding** (shading, dots, bars) rather than a separate chart (Saket 2018; Price 2016) |
| Every combination of a few assumptions (multiverse) | **Table-heatmap**: numbers in cells, shade by value, main case outlined |
| Shape: crossing, spread, gradient, cluster, outlier | **Chart** |
| The reader is an agent or script | **Table or JSON**, never a chart |

## Form by job

`/dataviz` covers magnitude, trend, part-to-whole, deltas and stat tiles. The forms it lacks:

| Job | Form | Avoid |
|---|---|---|
| Distribution of one variable | histogram, ECDF, beeswarm/strip (n < ~500), density only with a rug | bar of means |
| Compare distributions | small-multiple histograms, box + jittered points, ridgeline for many groups | bar + error whisker (within-the-bar bias, Correll & Gleicher 2014) |
| Estimate with uncertainty, expert readers | point + interval, **forest plot**, CI band; name the interval (SD / SE / 95% CI / predictive) | a bare line with no interval |
| Uncertainty for lay readers | **quantile dotplot** (20-100 dots) or **icon array** with a shared denominator; show the *predictive* interval when the question is "what happens to a case" (Kay 2016; Hofman 2020) | 95% CI of the mean alone (readers overestimate the effect) |
| Relationship of two variables | scatter (+ fitted line with band); hexbin when dense | dual-axis line |
| Robustness to assumptions | **multiverse table-heatmap** or **specification curve** (sorted estimates over a dot-matrix of choices) | showing only the main case |
| One assumption at a time | **sensitivity strip / tornado**: each row slides one input over its range, coloured by sign | a spaghetti of lines |
| Accumulation of parts | **waterfall / staircase** with a running total column | stacked bar |
| Rank change between two points | **slope chart** or dumbbell | grouped bars |
| Many series over time | **small multiples** on shared axes, constant design; one highlighted, rest grey; horizon charts when very many | 8+ coloured lines; animation |
| Trend at several time scales | one panel per scale, each banked near 45° (Heer & Agrawala 2006) | one panel squashing both |
| Part of one whole, 2-5 slices | stacked bar, or a plain pie (task-dependent; Saket 2018, Kosara & Skau 2016) | exploded/3D/donut variants; comparing across pies |
| Flow between states | Sankey/alluvial, only for <= ~15 nodes | chord diagrams |
| Network | adjacency matrix when dense; node-link only when sparse and the topology is the point | hairball |
| Geography | choropleth normalised per capita; dots or proportional symbols for counts, with a rate beside them (Snow's map lacked a denominator) | raw counts on a choropleth |
| Process, algorithm, model | the state drawn at each step beside the sentence for that step (Victor, *Sequential Art*) | prose that makes the reader "play computer" |
| One run of a system with a parameter | the whole family (all runs / all parameter values) faint, one concrete case highlighted (Victor, *Ladder*) | a single snapshot |
| Intrinsic 3D (molecules, terrain, point clouds) | interactive three.js / 3Dmol / py3Dmol with a sensible default camera | 3D bars, 3D pies |

## Motion

Default to static: small multiples beat animation for analysis and were more accurate
(Robertson et al. 2008); animation's apparent wins came from giving it more information
(Tversky et al. 2002). Animate only:
- sampling uncertainty (hypothetical outcome plots, Hullman 2015);
- object constancy when the same marks regroup across views (Bostock; NYT budget piece);
- a narrated presentation whose data tells a clean story (Robertson's presentation arm), via `/manim-animations`.

## Tool by medium

| Medium | Default | When else |
|---|---|---|
| Terminal / chat answer | markdown table, a sentence, unicode sparkline `▁▂▃▅▇` | nothing heavier |
| HTML artifact or web page | **Observable Plot** + `/dataviz` tokens | **d3** for bespoke forms (staircase, sensitivity strip, custom multiverse); Vega-Lite when a lintable JSON spec must render in several media |
| Svelte/React app | plain SVG in components, scales by hand or d3-scale (the immigration figures page uses no chart library) | LayerCake if many charts share scaffolding |
| Paper / PDF | **matplotlib** with a house style (figures4papers reference: `pdf.fonttype=42`, column widths 89/183 mm) | pgfplots only when the document is LaTeX and font matching matters |
| Diagram, not data | `/scientific-drawing` (Typst/CeTZ, TikZ, D2) | — |
| Motion that explains | `/manim-animations` | — |
| True 3D | three.js (web), py3Dmol (molecules) | — |
