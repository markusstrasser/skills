# Long-Form Register — Markus Strasser

Patterns for essays, blog posts, and other long-form pieces written in Markus's voice. Load this when writing or reviewing long-form prose; short-form rules in `SKILL.md` apply additionally (banned vocabulary, opinion markers, agreement words). The deeper guide with multi-sample analysis lives in `~/Projects/phenome/docs/derived/writing-style-guide.md` — this file is the focused subset for the essay register.

**Source data:** Three essays sampled so far, deliberately covering different sub-registers:

| Essay | Length | Sub-register |
|---|---|---|
| `extracting-knowledge-from-literature` (2021) | ~25 min | Long autobiographical-analytical (retrospective of a failed venture) |
| `browser-extensions-are-underexplored` (2021) | ~2 min | Short claim essay (one thesis + enumerated reasons) |
| `a-future-query` (2019, republished 2025) | ~4 min | Vision / speculative (worked-example illustration of a hypothetical product) |

Patterns confirmed across all three are unmarked. Patterns observed in some but not all carry a sub-register tag (`[long-analytical]`, `[short-claim]`, `[vision]`) where they belong. Patterns observed once carry `[1×]`. The sub-registers differ enough that some patterns are register-specific rather than universal — important to preserve that distinction.

## Form & Mechanics

| Element | Rule | Notes |
|---|---|---|
| Opener | One of: (a) `TL;DR` literal heading + 1–2 sentence summary `[long-analytical, short-claim]`; (b) italicized `Note` block with meta-context (when written, why now, what to assume) `[vision]`; (c) date+place biographical hook `[long-analytical]`; (d) direct claim that doubles as thesis. Never an abstract framing paragraph. | Reader gets the thesis or the meta-context immediately. The literal `TL;DR` is not universal — vision/speculative essays open with a `Note` framing block instead. |
| Section titles | The essay title itself states the thesis (*"Browser Extensions are Underexplored"*, *"The Business of Extracting Knowledge from Academic Publications"*). For long autobiographical essays, internal section titles also do rhetorical work — *"Psychoanalysis of a Troubled Industry"*, *"My Quixotic Escapades in Building X"*, *"Public Penance: My Mistakes, Biases and Self-Deceptions"*. | Title Case. Literary flair appears mainly in long pieces. |
| Footnotes | Inline integers as superscript markers — confirmed 2/2. Half-integers (`0.5`, `1.5`, `2.5`) appear in long discursive essays for sub-asides `[1×]`. | Tufte-style sidenotes for caveats, niche detail. Cite-the-source block also auto-generated at essay end. |
| Latin abbreviations | `eg.` (confirmed 2/2). `ie.` and `w.r.t.` `[1×]` — same single-dot convention. | Mechanics signature. Don't auto-expand. |
| Ellipsis | Unicode `…` (single char) for trailing/unfinished thought, not `...` `[1×]` | Used at end of sentence or paragraph for rhetorical exit in long discursive essays. |
| Block quotes | Introduced with `From [source]:` — informal one-liner attribution `[1×]` | E.g. `From Notes on The changing structure of American innovation:`. Appears in essays that aggregate multiple external sources. |
| Em-dashes | **Used in `[long-analytical]` and `[vision]` sub-registers.** Carry parentheticals and topic-shifts (*"next-level search—API standards, interoperability, fine-grained differential privacy—we start at the end"*; *"Call it YOU-DB—a service that exposes your merged data streams"*). Absent in `[short-claim]` essays. | The outreach ban from the main skill does not apply here. But em-dash use is register-conditional, not a default. |
| Lists | Three list shapes: bullet enumeration `[short-claim]`, internal section enumeration with H2 sub-headers `[long-analytical]`, or fictional dialog `[vision]`. Lists exist to make parallel structure visible; the form follows the argument shape. | The pattern is structural visibility, not list-as-decoration. |
| Worked-example dialog | `[vision]` essays construct a fictional interaction (Me / system) as the central illustration of the proposed product. The dialog *is* the argument; surrounding prose contextualizes it. `[1×]` | *"Me: Hey Ohm, who is currently in Cambridge…"* — argument by showing, not telling. |
| Coined placeholders | `[vision]` essays introduce arbitrarily named entities and acknowledge them as such. `[1×]` | *"Welcome to Ohm, the arbitrarily named search engine of the soon-enough future"*; *"Call it YOU-DB"*. Marker of speculative register. |
| Bold/italic | Sparingly. Emphasis is by sentence structure first, typography second. Italics used for the `Note` framing block in vision essays. | Confirmed 3/3 — neither bold nor inline italics are used to carry emphasis. |

## Rhetorical Moves

| Move | Pattern | Examples |
|---|---|---|
| Strong-negation punchline | Closes a paragraph or argument with a deflationary phrase. Confirmed 3/3 (different specifics each essay, same move). | *"vanishingly small"*, *"elusive and trite simultaneously"*, *"dead in my view (without admitting it)"*, *"masochistic and asinine to add features"*, *"fragile to base a business on"*. Vision essays use a softer version (*"It only becomes spooky if…"*). |
| Concrete named entities over abstractions | Names actual companies, products, programs, places. Confirmed 3/3. | *"Bayer, AZ, GSK"*; *"Atomwise, Insitro, nFerence"*; *"Google Playstore"*, *"Safari and Firefox"*; *"Cambridge, UK"*, *"Waterstone's Bookstore"*, *"Goodreads"*, *"LinkedIn's InMail"*. |
| Argument structure | One of: enumeration of independent reasons `[long-analytical, short-claim]` or a single extended worked example `[vision]`. Both make parallel structure visible. | Long: 8 numbered sections each one reason. Short: bullet list of 6 dev pains. Vision: one extended dialog with branching sub-questions. |
| Rhetorical pivot question | A direct question pivots from setup to body or sets up a section. Confirmed 3/3. | *"So, why aren't we seeing more innovative and ambitious browser extensions?"*; *"Would you invest in automation if you have billions of disposable income…?"*; *"Where does the data come from?"* |
| Technical-frame casual register | Drops technical/scientific concepts as casual rhetorical moves. No definition asides. Confirmed 3/3. | *"My null hypothesis is usually that people don't have ideas."*; *"drunkard's search"*; *"acqui-hire"*; *"differential privacy"*, *"feature embeddings"*, *"feature activations"*. |
| Closing-conviction marker | Closes with a re-statement of personal conviction (`I still think`, `I suspect`, `To me…`) or a forward-looking conditional (`With X, we can Y`). Confirmed 3/3. | *"I still think browser extensions are massively underrated and under-explored."*; *"I suspect the inconsequential costs of lab labor is a reason why…"*; *"The way we get to the next level in search is through personal privacy. With that, our knowledge … can be queried if we wish—and connected to others vastly better."* |
| Self-mocking hedge for loose claims | Acknowledges informal/imprecise reasoning instead of cleaning it up. `[1×]` | *"A 3am hand-waving definition of context is…"* |
| Republish-with-note convention | Old essays brought back have a meta `Note` block explaining the dating, what's changed, and what to assume. Treats the writing as a snapshot with a thread back to the present. `[vision][1×]` | *"This is an essay I unpublished years ago. It seemed obvious—everyone would have personal APIs… Yet in November 2025, I still can't run anything like 'A Future Query.'"* |
| `right?` tag | Trailing rhetorical question softens pushback. `[1×]` — appears in personal/discursive essays | *"…it can't just be the clogging of liquid handling robots, right?"* |
| Self-quoting as anti-example | Quotes his own past work alongside others' as part of the critique. `[1×]` | *"Or from a grant application of yours truly:"* — quotes his own grant after listing AllenAI/Tellic/OccamzRazor pitches. |
| Geographic + temporal anchoring | Names specific cities, months, years to ground biographical context. `[1×]` — appears in autobiographical essays. | *"Back in March 2020 when the first covid lockdowns started I evacuated San Francisco…"* |
| Specific dollar/salary figures | Numbers carry the argument, not adjectives. `[1×]` — appears when grounding economic claims. | *"£35k at AstraZeneca"*, *"$6,000 yearly salary"*, *"four months of youtubing Javascript tutorials"* |
| Owning past mistakes | Direct admission of having been wrong, used as evidence for the current claim. `[1×]` | *"Technological utopians and ideologists like my former self underrate how important context and tacit knowledge is."* |
| Confessional section near end | Penultimate section labelled to acknowledge own biases. `[1×]` — long autobiographical essays only. | *"Public Penance: My Mistakes, Biases and Self-Deceptions"* — *"Yes, I was raised catholic. How did you know?"* |

## Opening Conventions

Open with one of:
- `TL;DR` heading + 1–2 sentence summary (claim and analytical essays)
- An italicized `Note` block with meta-context — when written, why republished, what to assume (vision/speculative essays, especially republished ones)
- A date and place — *"Back in March 2020 when the first covid lockdowns started I evacuated San Francisco…"* (long autobiographical)
- A direct claim that doubles as thesis

Never:
- An abstract framing paragraph ("This essay will discuss...")
- Background context the reader can derive
- Throat-clearing ("I've been thinking a lot about...")

## Closing Conventions

Essays end on one of four moves — never a summary or "future work" paragraph:

1. **Conviction restatement.** *"I still think browser extensions are massively underrated and under-explored."* Direct re-assertion of the thesis as personal conviction, often using `I still think`, `I suspect`, `To me…`.
2. **Forward-looking conditional.** *"With that, our knowledge, hobbies, interests, worries, feelings can be queried if we wish—and connected to others vastly better."* `[vision]` essays close with a `With X, we Y` clause that paints the post-condition rather than summarizing what was argued.
3. **Punchline / joke.** *"Yes, I was raised catholic. How did you know?"* Last line is a self-aware joke that recontextualizes the section above. `[long-analytical]`
4. **Last substantive point with no wrap-up.** Argument stops where it stops; the reader walks out on the final claim.

Never:
- "In conclusion..." / "To summarize..."
- "Despite [problems], [vague optimism about the future]"
- A wrap-up paragraph that restates the body's points
- A "future work" / "next steps" closing in personal essays

## Argumentation Style

- **Examples > abstractions.** Concrete companies, salaries, named programs, real emails — or, in vision essays, a fully worked-out dialog. Abstractions are illustrated by example, never the reverse.
- **Quotation as evidence** `[long-analytical]`**.** Pulls block quotes from sources to make the point, then adds his own line of commentary. Doesn't paraphrase someone else's argument when their own words would do.
- **Adversarial register** `[long-analytical, short-claim]`**.** Comfortable saying things are *"dead in my view"*, *"a pipe dream"*, *"vanishingly small"*, *"masochistic and asinine"*. Not academic-neutral.
- **Speculative-constructive register** `[vision]`**.** When painting a vision, the register softens: lots of `could`, `if we`, `we can`. Still personality-forward and concrete (worked example, named placeholders), not academic-detached.
- **Argument by accumulation of independent observations** `[long-analytical, short-claim]`, not single decisive proof. Each section is one reason; together they form the case. Explicitly: *"To me the reasons feel elusive and trite simultaneously. All are blatantly obvious in hindsight."*
- **Argument by extended illustration** `[vision]`. One example carries the whole essay; surrounding prose contextualizes it.

## Negative Space — What He Doesn't Do

Read this as hard constraints — these patterns are absent across the sampled essay and should not be introduced when writing in his voice:

- No **boost vocabulary**: *groundbreaking, pivotal, revolutionary, transformative, vital, crucial, key (adj), significant (adj)*.
- No **figurative usage** of *delve, tapestry, intricate, landscape, vibrant, dive deep, unpack, foster, leverage, garner*.
- No **vague attribution**: *"experts argue"*, *"observers cite"*, *"it is widely regarded"*. When he attributes, he names the source or admits aggregate (*"After talking with employees of GSK, AZ and Medscape"*).
- No **definition asides** for technical terms. He drops *drunkard's search*, *Swanson linking*, *tacit knowledge*, *acqui-hire*, *information asymmetries* without parenthetical explanation. Assume reader knows or can look it up.
- No **abstract framing first**. Body opens directly; no "First we will discuss X, then Y."
- No **optimistic / "future is bright" closings**. Closes adversarial or self-deprecating.
- No **rule-of-three padding**. When three items appear, they are genuinely distinct (*"extracting, structuring or synthesizing"*; *"Bayer, AZ, GSK"*).
- No **symbolic significance assertions**: *"X represents Y"*, *"this reflects a broader shift"* — absent.
- No **didactic asides**: *"It is important to note"*, *"Notably"*, *"Crucially"* — absent.
- No **hedging chains**: *"perhaps it could potentially be the case that..."* — absent.
- No **section summaries** mid-essay. Sections end on their last substantive point.
- No **promotional warmth**. The whole register is adversarial / forensic.

## Sub-Register Cheat Sheet

When drafting, identify the sub-register first; the universal rules + the sub-register rules together define the constraint.

| Aspect | `[long-analytical]` | `[short-claim]` | `[vision]` |
|---|---|---|---|
| Opener | TL;DR or date+place | TL;DR | italicized `Note` |
| Body shape | numbered/named sections, one per reason | single bullet list of reasons | extended worked example (dialog) + light surrounding prose |
| Em-dashes | yes, used for parentheticals | absent | yes, used for parentheticals |
| Tone | adversarial, autobiographical | adversarial, terse | speculative-constructive |
| Closing move | punchline / joke / last-substantive-point | conviction restatement | forward-looking conditional |
| Named entities | real companies, places, dollar figures | real companies | named places + coined placeholders |
| Self-reference | "Public Penance" / "yours truly" / past-self critique | "I haven't seen anybody figure out…" | "I have been hosting book clubs on and off for years" |

## Open Validation Items

Patterns still observed only once or in one sub-register that may or may not generalize:

- Whether half-integer footnotes (`0.5`, `1.5`) are a stable convention or specific to long discursive pieces (seen only in `extracting-knowledge`)
- Whether `Public Penance`-style confessional sections recur or were a one-off
- Whether the `From [source]:` block-quote intro convention holds across other multi-source essays
- Whether `right?` tags appear outside personal/discursive pieces
- Whether the `Note` republish-block convention recurs (seen only in `a-future-query`, which is the only republished essay among the three)
- Whether section titles do literary rhetorical work in short claim essays (none long enough so far to test)

**To validate:** sample two more essays — preferably one personal/diary-style and one technical/how-to piece — to round out the sub-register coverage. Promote stable patterns, drop ones that don't replicate, add new sub-registers if needed.
