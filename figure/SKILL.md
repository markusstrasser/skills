---
name: figure
description: "Use when: deciding WHETHER and HOW to show data — sentence vs table vs chart, which form (incl. distributions, uncertainty, multiverse/sensitivity), which tool (Plot/d3/matplotlib/TikZ/three.js), and checking a figure with a blind reader. Styling of HTML charts → /dataviz; diagrams → /scientific-drawing."
user-invocable: true
argument-hint: '[claim or data to show]'
allowed-tools: [Bash, Read, Write, Edit, Grep, Glob, Agent]
effort: medium
---

# Figure

Decide the form before any pixels, build it with the tool the medium wants, then check that a
reader who sees only the figure gets the answer. The bundled `/dataviz` skill owns HTML chart
styling (palette, marks, tooltips, a11y); this skill owns everything before and after that.

## 1. Write the claim first

One sentence the reader should leave with, as a finding ("Schools alone turn the sign"), not a
topic ("Costs by service"). That sentence becomes the title. If you cannot write it, you are
exploring, not presenting; say so and make an exploratory view, not a publication figure.

Then list the 2-4 questions a reader will ask of the figure and tag each:
`claim` (the takeaway), `lookup` (a specific value), `shape` (a crossing, trend, spread, outlier).

## 2. Sentence, table or chart

| The content is... | Use |
|---|---|
| One or two numbers, or a claim with no shape | **A sentence.** Numbers in the prose. |
| A trend that supports a sentence | Sentence + **inline sparkline** (Tufte word-sized graphic) |
| Exact values the reader will look up; few rows | **Table**, sorted by the value that matters, key cells emphasised |
| Every combination of a few assumptions (multiverse) | **Table-heatmap**: numbers in cells, shade by value, main case outlined |
| Shape: crossing, spread, gradient, cluster, outlier | **Chart** |
| The reader is an agent or script | **Table or JSON.** Never a chart. |

The test: if the takeaway survives as a sentence and nobody needs the lookups or shape, cut the
chart. Measure it with the blind reader (step 5) when the call is not obvious.

## 3. Form by job

`/dataviz` covers magnitude, trend, part-to-whole, deltas and stat tiles. The forms it lacks:

| Job | Form | Avoid |
|---|---|---|
| Distribution of one variable | histogram, ECDF, beeswarm/strip (n < ~500), density only with a rug | bar of means |
| Compare distributions | small-multiple histograms, box + jittered points, ridgeline for many groups | dynamite plot (bar + error whisker) |
| Estimate with uncertainty | point + interval; **forest plot** for many estimates; CI band on lines | a bare line with no interval |
| Relationship of two variables | scatter (+ fitted line with band); hexbin when dense | dual-axis line |
| Robustness to assumptions | **multiverse table-heatmap** (every combination) or **specification curve** (sorted estimates over a dot-matrix of choices) | showing only the main case |
| One assumption at a time | **sensitivity strip / tornado**: each row slides one input over its range, coloured by sign | a spaghetti of lines |
| Accumulation of parts | **waterfall / staircase** with a running total column | stacked bar |
| Rank change between two points | **slope chart** or dumbbell | grouped bars |
| Many series over time | **small multiples** on shared axes; horizon charts when very many | 8+ coloured lines |
| Flow between states | Sankey/alluvial, only for <= ~15 nodes | chord diagrams |
| Network | adjacency matrix when dense; node-link only when sparse and the topology is the point | hairball |
| Geography | choropleth normalised per capita; dot or proportional symbol for counts | raw counts on a choropleth |
| Intrinsic 3D (molecules, terrain, point clouds) | interactive three.js / 3Dmol / py3Dmol with a sensible default camera | 3D bars, 3D pies, ever |

Honesty rules that `/dataviz` does not state: bars start at zero (else use dots); aspect ratio
banks the slopes you care about near 45°; show n and the interval, or say why there is none;
log scale when the claim is about ratios; the same quantity keeps the same axis across panels.

## 4. Tool by medium

| Medium | Default | When else |
|---|---|---|
| Terminal / chat answer | markdown table, a sentence, unicode sparkline `▁▂▃▅▇` | nothing heavier |
| HTML artifact or web page | **Observable Plot** (d3-based grammar, small code) + `/dataviz` tokens | **d3** for bespoke forms (staircase, sensitivity strip, custom multiverse); Vega-Lite when a lintable JSON spec must render in several media |
| Svelte/React app | plain SVG in components, scales by hand or d3-scale (the immigration figures page uses no chart library) | LayerCake if many charts share scaffolding |
| Paper / PDF | **matplotlib** with a house style (figures4papers reference: `pdf.fonttype=42`, column widths 89/183 mm) | pgfplots only when the document is LaTeX and font matching matters |
| Diagram, not data | `/scientific-drawing` (Typst/CeTZ, TikZ, D2) | — |
| Motion that explains | `/manim-animations` | — |
| True 3D | three.js (web), py3Dmol (molecules) | — |

## 5. Render, look, then blind-read

1. **Render and look.** Screenshot the real output and view it with Read. Check against the
   claim, then `/dataviz`'s anti-pattern list. Capture gotcha: `agent-browser screenshot <sel>`
   can return blank images for elements below the fold; take `screenshot --full` and crop each
   element by `getBoundingClientRect()` + `scrollY`.
2. **Blind-read** when the sentence-vs-chart call matters or a page has several figures:
   `scripts/blind_read.py SPEC.json --repeats 2`. A fresh `claude --safe-mode` reader answers
   the pre-registered questions from one arm at a time: `full` (whole section image), `prose`
   (the section's text only), `chart` (the graphic only). Answers are graded against values
   **computed from the data, never read off the figure**. The summary reports accuracy per role
   and tokens per arm, and gives an advisory verdict:
   - the chart beats prose on `claim` → keep it;
   - prose matches on `claim`, the chart wins only on `lookup`/`shape` → keep it only if the
     reader needs those (your call, not the script's);
   - prose matches on everything → a sentence will do.
   `--from-results` regrades stored answers after a key fix without new reader calls.
   A `[DEGRADED]` line means reader calls failed; there is no verdict for those items.

Write questions a real reader asks, including at least one `claim` per figure. Lookup-only
question sets bias the test toward charts.

## Evidence

- Built 2026-09-25 from the operator's request on the immigration figures page ("remove ones
  where a sentence will do and show the ones where visualization helps").
- First run (4 figures × 3 arms × 2 repeats, sonnet reader, `references/2026-09-25-first-run.md`):
  chart-only crops answered 100% of questions on all four; prose alone answered takeaways on
  matrix and flip but 0% of lookups/shape; image arms cost ~26K input tokens vs ~2.9K for prose.
