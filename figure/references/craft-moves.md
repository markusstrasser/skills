# Craft moves, with exemplars

The practitioners' moves behind the SKILL.md principles. Each has a named exemplar to study and
the case where it fails. Quotes and full sourcing: `agent-infra/research/2026-09-25-information-display-*.md`.

| Move | Exemplar to study | Fails when |
|---|---|---|
| **Title the finding; annotate the 2-3 marks that prove it** — "the words in a graphic should highlight the relevant pattern ... and not merely say 'Here is some data'" (Amanda Cox) | FT Covid trajectory tracker (Burn-Murdoch); Datawrapper sea-ice chart | the title claims more than the data (Healy's "halo effect" NYT democracy chart); exploratory essays that depict a system (The Pudding) |
| **Label directly, drop the legend** — "Place the words that explain your chart elements as close to those elements as possible" (Muth) | Datawrapper line charts; Rosling TED 2006 | narrow/mobile widths, many series; novel encodings, where the legend is "the bridge" (Fragapane) |
| **Grey the context, one focal colour, ranked by priority** | Datawrapper sea-ice: black this year, blue last ten, the rest grey | the reader cares about a different series — split into small multiples |
| **Compared to what? Within one eyespan** — "Comparisons must be enforced within the scope of the eyespan" (Tufte, EI) | FT excess-deaths small multiples: thick red current year over thin grey past years, excess printed per panel | independent y-scales that fake comparability |
| **Scale and align so the claim is a straight line** | FT log-scale "days since 100th case" with doubling guides | general readers misread log scales (Romano 2020, randomised, n≈2000) — add a linear companion |
| **Predict, then reveal** — "more compelling after one has been forced to think about it first" (Aisch) | NYT "You Draw It: family income and college" (2015) | unsurprising answers; exact values (text wins) |
| **Detail makes the overview; split the averages** — "to clarify, add detail" (Tufte) | Rosling splitting Sub-Saharan Africa into countries, Uganda into quintiles | counts without a denominator (Snow's dot map) |
| **Layer and separate: data forward, scaffolding back** | Tufte, *Envisioning Information* ch.3 | subtraction past the reader's needs — Tufte's own minimal boxplot was hardest to read (Anderson et al. 2011, via Healy) |
| **Word-sized graphics** — "Data graphics should have the resolution of typography" | Tufte sparklines | flat aspect ratios; no anchor numbers |
| **Same marks across views; animate only to keep identity** — "Above all, animation should be meaningful" (Bostock) | NYT "Four Ways to Slice Obama's 2013 Budget" | areas stay hard to compare; unstable layouts on reload |
| **Variable fits the data's level** (Bertin): position/length for quantity, lightness for order, hue for category | Nightingale correcting her rose from radius to area | area stays imprecise even when correct |
| **Frame the argument's comparison and say it is a frame** | Du Bois 1900 plates (Black American illiteracy beside European nations); Nightingale's before/after roses | juxtaposition that misleads — Minard's temperature strip implies the army froze, most losses came earlier (Small) |
| **Beauty to earn attention, kept subordinate** — "hook them in before you can try to convey the insights" (Bremer); "truth and beauty are equally important" (Stefaner) | Stefaner's OECD Better Life flowers; Fragapane "Stories Behind a Line"; Lupi/Posavec *Dear Data* | analytic, lookup or agent readers; decoration unrelated to data (Haroz 2015) |
| **Show the seams** — "'Data-driven' doesn't mean 'unmistakably true'" (Lupi) | The Pudding "Film Dialogue" methodology; Burn-Murdoch relabelling "cases" as "confirmed positive tests" | caveats in the title competing with the claim — keep them in the notes layer |
| **Static first, interaction only when paper can't do it** — "If you make a tooltip or rollover, assume no one will ever see it" (Tse 2016) | Victor's *Magic Ink* train timetable; Red Blob Games variants side by side | analyst tools; pieces where the interaction is the story (You Draw It) |
| **Reactive document: reads correctly untouched, knobs on the uncertain assumptions** — "The reader is not *forced* to interact in order to learn" (Victor) | Victor, *Explorable Explanations* (Prop 21 paragraph) | decorative knobs; agent readers |
| **Concrete first, question first, "but/therefore" between figures** (Nicky Case, after Victor's Ladder) | *Parable of the Polygons*; *The Evolution of Trust* | reference docs and executive summaries, where the answer leads |

## Taste disagreements to decide per piece

- **Thesis or system?** Cox and Burn-Murdoch title the point; Matt Daniels (The Pudding) depicts "the system ... rather than a thesis", and Lupi holds "clarity does not need to come all at once."
- **Glance or dwell?** Newsrooms design for a scroll ("Readers just want to scroll", Tse); Lupi and Fragapane design pieces that "need time to be read".
- **Minimal or embellished?** Neither wins in general. Lean for analysis and lookup; relevant embellishment is fine for presentation and recall (Bateman 2010; Borkin 2016; Kosara's definition of junk as anything that "does not contribute to clarifying the intended message").
- **Are the canon exemplars good models?** Minard, Snow and Nightingale were persuasion pieces (Kosara, BELIV 2016). Copy the fit between form and argument, not the form.
