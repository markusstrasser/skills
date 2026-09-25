---
name: figure
description: "Use when: deciding WHETHER and HOW to show data — sentence vs table vs chart, which form (incl. distributions, uncertainty, multiverse/sensitivity), which tool (Plot/d3/matplotlib/TikZ/three.js), and checking a figure with a blind reader. Styling of HTML charts → /dataviz; diagrams → /scientific-drawing."
user-invocable: true
argument-hint: '[claim or data to show]'
allowed-tools: [Bash, Read, Write, Edit, Grep, Glob, Agent]
effort: medium
---

# Figure

A figure is an argument a reader should get right. This skill decides whether one is needed, what
it shows and how it is checked; `/dataviz` styles HTML charts. The principles below are the
contract. Tables and exemplars live in `references/` and only speed up the search.

## Principles

1. **Start from the reader's task.** Name it: look up a value, grasp a claim, see a shape, remember
   it later, or explore. Most famous rules reverse across tasks: minimal design loses on recall,
   ornament on precise reading, log scales on lay readers, interaction on everyone who only
   scrolls. An error at the task level cannot be fixed by styling (Munzner's nested model).

2. **The words are part of the figure.** The title states the finding. Numbers sit at the point
   they describe, encoding notes at the axis, and 2-3 annotations mark what proves the claim.
   Readers remember titles over data and still judge the chart neutral, so the title must name the
   chart's most prominent feature; if it doesn't, change the chart, not the words. Every figure
   can be restated as one stand-alone sentence; ship that sentence too.

3. **One comparison, inside one eyespan.** Name the comparison that carries the claim. Put its
   items next to each other, give them the focal colour and grey the rest, and encode it as
   position on a shared scale. When there are more comparisons, use small multiples with an
   identical design, not more colours.

4. **The default view carries everything.** Design the static figure first. Interaction and
   motion are optional depth that most readers never touch: nothing needed for the claim hides
   behind hover, click, tab or slider. Show variants side by side instead of behind a toggle.
   Animate only sampling uncertainty, marks regrouping across views, or a narrated talk. An
   explorable must read correctly untouched, with its defaults set to the main case.

5. **Show the family, highlight the case.** Draw every run, specification, year or unit faintly,
   with the one the reader cares about drawn strongly. Break an average open when the claim
   depends on the variation inside it.

6. **Scales and intervals are claims.** The axis range asserts an effect size: bars from zero,
   dots and lines ranged to the effect you mean, stated in the text. Use log for ratio claims,
   with a linear companion for lay readers. Name every interval; for lay readers, show outcomes
   (quantile dotplot, icon array) rather than a bare 95% CI.

7. **Show the seams.** Put what was measured (as distinct from what the reader will assume), the
   source, the method and the framing choice in a notes line under the figure, never in the
   title.

8. **Ornament must be data or earn needed attention.** There is no data-ink quota. Pictographs
   and metaphors that encode the data are fine, and beauty may hook a general audience, but
   imagery unrelated to the data goes. A polished figure can mislead through its polish.

9. **If no figure makes it obvious, rethink the idea, not the styling.** The claim may be a
   sentence, or it may need a different transform, axis or notation.

10. **Judge by readers, not by your own eye.** Authors cannot see their own figure fresh (the
    curse of knowledge). Clarity is checked with a blind reader against the data. Beauty has no
    verifier here: the operator judges it.

**Where the principles yield.** Exploratory pieces that deliberately depict a system without a
thesis (The Pudding, Lupi) drop the finding-title but keep principles 3-8, and say they are
exploratory. Expert audiences keep their conventions (forest plots, equations, dense tables).
Agent readers get a table or JSON.

## Process

1. **Claim, task, comparison.** Write the claim sentence, the reader's task and the one
   comparison. List 2-4 questions the reader will ask, tagged `claim`, `lookup`, `shape` or
   `trap` (a question whose right answer runs against the figure's visual impression).
2. **Sentence, table or chart.** Take the lightest form that answers the questions:
   `references/forms-and-tools.md` § Sentence, table or chart.
3. **Form and tool.** Choose from `references/forms-and-tools.md`, and borrow moves from
   `references/craft-moves.md`.
4. **Build.** HTML charts use `/dataviz` styling; paper figures use matplotlib in the
   figures4papers house style; diagrams use `/scientific-drawing`; motion uses `/manim-animations`.
5. **Check.**
   - *Look.* Render it and view it with Read. Check that the title names the most prominent
     feature, 2-3 annotations mark the proof, labels are direct, context is grey around one focal
     colour, compared items sit in one eyespan, scales and intervals are named, and a notes line
     exists. Capture gotcha: `agent-browser screenshot <sel>` returns blank images below the fold;
     take `screenshot --full` and crop by `getBoundingClientRect()` + `scrollY`.
   - *Blind-read* (`scripts/blind_read.py SPEC.json --repeats 2`). A fresh `claude --safe-mode`
     reader with no backstory sees one arm at a time: `full` (the whole section), `prose` (the
     text only) and `chart` (the graphic without its title). `open` questions ("what is the main
     point?") run first in their own call, so nothing cues them; compare their answers with your
     title. Graded answers are checked against values computed from the data, never read off
     the figure. The advisory verdict per figure reads:
     - the chart beats prose on `claim` → keep it;
     - the chart beats prose only on `lookup`/`shape` → keep it if readers need those;
     - prose matches everything → a sentence will do;
     - `[MISLEADS]` → full-arm readers fail a `trap`; fix it before shipping.
     Use `--from-results` to regrade stored answers after fixing the key. `[DEGRADED]` means
     reader calls failed and those items get no verdict. Remember the reader is an LLM standing
     in for a human.
   - *Taste.* When the look matters (a published piece, a cover figure), render 2-3 variants side
     by side and let the operator choose. Do not iterate on your own aesthetic judgment.

## Evidence

- Research behind the principles (2026-09-25; three lanes with read/skipped logs):
  `agent-infra/research/2026-09-25-information-display-craft.md`. Anchors: Victor (*Magic Ink*,
  *Explorable Explanations*, *Ladder of Abstraction*); Franconeri et al. 2021 (PSPI); Stokes et
  al. 2022; Kim, Setlur & Agrawala 2021; Kong et al. 2018/2019; Correll et al. 2020; Robertson
  et al. 2008; Tversky et al. 2002; Tse 2016; Tufte; Healy; Xiong et al. 2020.
- First blind-read run on the immigration figures page: `references/2026-09-25-first-run.md`.
  Chart-only crops answered every question; prose carried the takeaway for matrix and flip but
  none of the lookups; image arms cost ~26K input tokens against ~2.9K for prose. An uncued
  chart-only reader read the staircase as about "unauthorized immigrants", which the page does
  not claim.
