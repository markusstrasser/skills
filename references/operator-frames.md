# Operator frames

How the operator thinks: the lenses, models, tastes and ambitions behind his requests. [Follow-up moves](../research/references/follow-up-moves.md) covers what he asks for next; this file covers the thinking that produces those requests. Both were mined from his own prompts to agents. This file draws on about 5,500 prompts across ten areas: agent benchmarks, investing, fiscal and crime economics, psychometrics, compression, biomedical pipelines, agent infrastructure, publishing and design, general research, and private decisions. The mining extracted 567 frames, and 545 of them trace to a verified quote. 308 of those support the 31 signatures below. A careful generic researcher already checks evidence, constructs and comparisons, so this file keeps what such a researcher would not predict about him.

**When to read:** at the start of a project or plan for him; before a report or recommendation he will judge; in an autonomous generate or Dreamer pass on his projects; when choosing between designs on his behalf.

**How to use:** pick the one to three signatures whose *When* holds right now, apply the *Do*, and name the lens in plain words only if it changed your recommendation. Before reporting, ask yourself the question forms that fit. Don't run the list, and don't quote this file back to him.

Treat it as a menu. A moves catalog mined the same way changed which next steps agents proposed, but did not raise how often they matched his actual next step (a held-out test on 2026-09-26: 11% vs 9%). *Seen in* counts are evidence strength: a signature that shows up in one area is a stance he holds in that project; a signature that shows up across several areas is a habit of mind.

## Growth, bottlenecks and who gets paid

- **Think in trajectories and derivatives.** A level or a static multiple misleads him. He reasons about rates, acceleration and where a curve bends, and expects exponential inputs to be taken seriously. *When:* a valuation, forecast, cost or population figure is given as a current level. *Do:* show the path and its first and second derivatives, and check whether the conclusion survives an accelerating path as well as a linear one. *Misfire:* extrapolating acceleration without a mechanism that sustains it. *Seen in:* 15 messages, 10 sessions; investing.

- **Find the binding input, then who captures it.** When demand grows fast, value flows to whoever holds the scarce input. He asks which layer of the chain is the choke point, who innovates, who keeps the margin and who pays. *When:* a trend, backlog or spending wave is used to argue that some party benefits. *Do:* trace the money from buyer to supplier, name the constrained input and its holder, and separate headline demand from captured revenue and margin. Say who loses. *Misfire:* a full value-chain account when the direct link is already established. *Seen in:* 42 messages, 22 sessions; fiscal and crime economics, investing, private decisions.

- **Effects compound; integrate over people and time.** He models second-round effects as a metabolism (reinvestment, repeated exchange, political feedback) and sums harms and gains over everyone exposed and over whole lifetimes. *When:* an impact estimate is one-period, first-order or per-event. *Do:* add the compounding channel and the exposure integral, state the horizon, and show how much of the answer they contribute. *Misfire:* speculative feedback loops with no measured rate. *Seen in:* 28 messages, 11 sessions; agent benchmarks, fiscal and crime economics, investing.

- **Marginal is not average; costs come in steps.** He distrusts per-head averages for decisions at the margin. Costs split into fixed and variable parts and jump at capacity thresholds, and ledgers that answer different questions stay separate. *When:* an average cost or benefit is applied to a marginal change, or two accounting totals are compared. *Do:* split fixed from variable, find where capacity binds, and give each ledger its own denominator and question. *Misfire:* splitting costs the decision is insensitive to. *Seen in:* 22 messages, 6 sessions; fiscal and crime economics.

## Bets, budgets and reversibility

- **Classify the payoff shape and size by conviction.** He asks whether an option could be a tenfold or is a steady compounder, looks for convexity, and expects exposure to follow conviction. Equal sizing of unequal ideas reads to him as hedging. *When:* ranking investments, research bets or projects by one expected value, or proposing equal allocations. *Do:* label each option's payoff shape (capped, linear, convex), say which could change the scale of the result, and order or size by conviction with the reason. *Misfire:* chasing convexity against poor odds, or sizing past the survival limit below. *Seen in:* 15 messages, 11 sessions; investing.

- **Survive the path.** Being right later is worthless if the position, project or person cannot survive the path there. He separates the thesis from how it is expressed, and conviction from the capacity to carry it. *When:* a recommendation involves leverage, concentration, timing, taxes or an irreversible commitment. *Do:* state the thesis and its expression separately, stress the path (drawdown, financing cost, forced exit, tax, adversarial shocks), include the cost of doing nothing, and size to what survives. *Misfire:* using survival worries to justify never acting. *Seen in:* 26 messages, 12 sessions; investing, private decisions.

- **Price time, money and quota explicitly.** He sets exchange rates and expects agents to apply them. Sometimes he buys speed with money, sometimes he saves a few dollars over half an hour, and he treats quota and idle waiting as real budget. *When:* choosing hardware, model tier, parallelism or a paid service, or letting a job wait. *Do:* state the cost in time and money, apply his stated rate (or ask once for it), and pick the option that buys decision-changing information soonest. *Misfire:* frugality that stretches a feedback loop from minutes to hours. *Seen in:* 25 messages, 11 sessions; 4 areas.

- **Reversible first; the incumbent stays until beaten.** Permanent choices get a reversible prototype, deletions start as recommendations, and a working default stays until a challenger wins a matched comparison. Options stay open until a winner shows. *When:* a change is hard to undo, a deletion is proposed, or a new tool, model or version would replace a working one. *Do:* propose the reversible trial, compare the challenger head to head on the real task with matched variants, and keep the incumbent when the difference is unclear. *Misfire:* keeping every option alive forever; he prunes when the evidence turns. *Seen in:* 34 messages, 16 sessions; 6 areas.

- **Grade by the real endpoint, in its own units.** He names the outcome in its native unit (return at a given risk, how old someone looks, what the end user receives, a working candidate) and judges analysis, infrastructure and activity by movement on it. *When:* reporting progress, choosing a metric, or justifying infrastructure work. *Do:* name the endpoint and unit first, report the change on it, and label everything else as a means with its expected effect. *Misfire:* grading sound decisions by noisy outcomes; judge those by what was knowable then. *Seen in:* 55 messages, 20 sessions; 4 areas.

## Intelligence and learning

- **Generality is the goal; a benchmark is a probe.** A score is evidence about a transferable capability. Anything that encodes the task (specific rules, exploits, tailored features) can win the score and miss the point. *When:* a method improves a benchmark, or a design adds task-specific knowledge. *Do:* say what general capability the gain shows, test held-out and recombined cases, and flag task-specific help as a confound. *Misfire:* near a deadline he may set the score itself as the target; follow his stated priority. *Seen in:* 72 messages, 33 sessions; agent benchmarks.

- **Humans are the yardstick.** He measures machine learning against fast human learners: how little data a strong person needs, how a skilled player (often himself) performs, and how understanding forms in narrated play. Expert human traces are scarce assets. *When:* judging data needs, sample efficiency or superhuman claims, or choosing training and evaluation data. *Do:* put a capable-human reference beside the model result, count the experience each needed, and use real human traces, including the path to insight, before synthetic ones. *Misfire:* one person's play is a noisy reference; state its limits. *Seen in:* 35 messages, 14 sessions; agent benchmarks.

- **Make priors fight the evidence.** He rigs tests so memorized conventions fail, keeps broken cases as controls, and asks whether an apparent discovery was already implied by pretraining or textbooks. *When:* a model succeeds on familiar-looking tasks, or a finding might be rediscovery. *Do:* build a variant where the familiar rule is wrong and all else is equal, and check whether the new result was inferable from the training distribution or standard sources. *Misfire:* priors are also knowledge; he holds that intelligence needs them. *Seen in:* 19 messages, 12 sessions; agent benchmarks.

- **Hunt the kernel.** He looks for the most compact, most general mechanism: the theory with the fewest moving parts, an operator that survives the transformations (he reaches for category theory), deeper primitives, learned rather than engineered axes, and a better medium than the inherited one. *When:* a design grows by adding features, axes, rules or primitives, or an explanation needs many parts. *Do:* ask what smaller mechanism would generate the list, whether the axes can be learned, and whether the representation (tokens, language, format) is the bottleneck. Test one compression of the design. *Misfire:* elegance that drops needed detail, or abstract labels without invariant behavior. *Seen in:* 42 messages, 20 sessions; 4 areas.

- **Learning comes from interaction.** He expects general learners to build causal world models by acting and seeing consequences, with language as a thin layer over spatial and sensory models. *When:* designing a learner, curriculum or agent that mostly consumes static text or examples. *Do:* add a closed loop (act, observe, update), measure what each action taught, and treat language as an interface to the model rather than the model. *Misfire:* interaction that cannot tell hypotheses apart teaches nothing. *Seen in:* 33 messages, 15 sessions; agent benchmarks.

- **Look for signs of life early.** He wants fine-grained evidence that learning is happening long before the headline metric moves: progress below the win, a curve out of its weight class, and a fast cycle. *When:* the main metric sits at zero or takes hours or days to move. *Do:* define a graded intermediate signal, find the fastest loop that shows it, and report the curve. *Misfire:* a proxy that improves while the capability does not. *Seen in:* 20 messages, 8 sessions; agent benchmarks.

## Evidence, experts and contested questions

- **Audit claims, not reputations.** Status and consensus count for little with him. He checks experts the way he checks agents: which channels they ignored, who funded the work, what they delivered, and whether their dated predictions hold. He also grants that consensus is often right. *When:* a conclusion leans on an expert, a field's consensus, an institution or a prominent writer. *Do:* restate the claim, list the channels the source left out, check funding and incentives, and compare the track record. Give the consensus its due when it survives. *Misfire:* contrarianism for its own sake; an incentive story is not a refutation. *Seen in:* 50 messages, 24 sessions; 4 areas.

- **Contested hypotheses are empirical questions.** He wants a socially disfavored hypothesis stated plainly and tested on its own terms, with the same standard for every group. He treats model training bias as a bounded uncertainty and wants results written to survive hostile readers. *When:* a question touches group differences, politics or other charged ground. *Do:* write the strongest version of each hypothesis, test each side with the same rules, widen the interval for known model bias, give calibrated probabilities instead of verdicts, and pre-empt the obvious attacks. *Misfire:* a thumb on the scale in either direction; he wants the evidence. *Seen in:* 21 messages, 10 sessions; 4 areas.

- **Beliefs live in a dated ledger.** He wants judgments about people, markets, experts, his own decisions and pipeline outputs kept as dated, resolvable claims. Skill can then be scored without hindsight, and the record can decide what to reuse or rerun. *When:* making a forecast, a recommendation or a verdict on a person or source, or deciding what to recompute. *Do:* record the claim, date, evidence and resolution condition; judge past calls by what was knowable then; let the record decide what needs rerunning. *Misfire:* ceremony for throwaway exploratory guesses. *Seen in:* 56 messages, 20 sessions; 5 areas.

- **What does the number measure?** A psychometrician's reflex he applies everywhere: which construct a score represents, its reference scale, what it double-counts, the shape of its errors, and the gap between possible and likely. *When:* a score, index, ranking or accuracy figure carries a claim. *Do:* name the construct and task mix, give the reference scale and chance baseline, and show the error profile instead of one number. *Misfire:* construct worries when the stated goal is the narrow metric itself. *Seen in:* 47 messages, 20 sessions; 4 areas.

## Systems craft

- **One clean authority; no legacy, no cruft.** He wants one inspectable source of truth and one path. When no live reader needs the old path, a full migration beats a compatibility layer, and unifying must not lose power. *When:* adding an adapter, wrapper, duplicate store or second path, or when a system has grown layers. *Do:* trace the actual readers, migrate them, delete the old path, and keep only what serves a named reader. *Misfire:* a copy is warranted for recovery or for a genuinely distinct reader. *Seen in:* 51 messages, 30 sessions; 5 areas.

- **Strictly better or no-op.** His bar for change borrows from medicine: the change must be durable and strictly better, add no noise, and do no harm through the treatment itself (iatrogenic harm). No change is a valid and respectable answer. *When:* proposing changes to a working system, loop or document, especially in a self-improvement pass. *Do:* show the durable gain, name the side effects and upkeep, and return a reasoned no-op when nothing clears the bar. *Misfire:* timidity that shields a weak incumbent from a consequential fix. *Seen in:* 43 messages, 23 sessions; 7 areas.

- **Fix the writer, not the mess.** To him, recurrence is evidence of a system flaw. He asks what keeps producing the waste or delay, splits elapsed time into real work and overhead, and wants an honest account of what remains and what it will cost. *When:* the same cleanup, bug, delay or explanation comes up a second time, or a job runs far longer than its compute. *Do:* find and change the producer (writer, rule, workflow), decompose the wall time, and state the remaining work with a time and cost bound. *Misfire:* turning a one-off into a rule. *Seen in:* 66 messages, 16 sessions; agent infrastructure, biomedical pipelines.

- **Keep what cannot be rebuilt.** He sorts artifacts by recreation cost and provenance: raw evidence, human judgment and dated records stay, and derived packaging goes. Experts get the full evidence, not an agent's filtered verdict. *When:* cleaning storage, summarizing for someone, or pruning notes and outputs. *Do:* classify each item as source, judgment or rebuildable; keep the first two close and findable; hand over evidence with provenance, not just conclusions. *Misfire:* keeping everything buries what matters. *Seen in:* 37 messages, 16 sessions; 4 areas.

## Taste in design and writing

- **Every visual must carry meaning.** Color, motion and layout should tell the viewer what things are and what they can do; a chart should be Tufte-grade or absent. He reads confusing or boring presentation as a flaw in the measurement, not only in the look. *When:* building an interface, game, chart or report page. *Do:* give each visual distinction a meaning, raise information density without clutter, choose the form (chart, table or plain text) from the data's structure, and cut decoration. *Misfire:* sparse design that hides context people need. *Seen in:* 62 messages, 20 sessions; 6 areas.

- **Match the feel of the reference.** He judges a design against a concrete reference experience (a game's camera, a catalogue's gradient, recorded motion, grip underfoot) and wants its feel reproduced, not its parts copied literally. *When:* reproducing a style, motion, material or interaction from an example. *Do:* get the reference itself (video, image or spec), work out what makes it feel that way, keep composition and identity separate, and compare side by side. *Misfire:* copying surface motifs while missing the structure. *Seen in:* 34 messages, 10 sessions; general research, private decisions, publishing and design.

- **Keep the character; originality over polish.** Clean execution is a low bar next to inventing a voice or a visual language. He wants irregularities kept, no traces of machine writing, and essays that take positions and make predictions. *When:* editing, summarizing or generating writing, art or design in his name or for his judgment. *Do:* keep his judgments and quirks, cut the ceremony and hedging that remove exposure, and ask whether a revision is better or only cleaner. *Misfire:* protecting unclear expression that needs correcting. *Seen in:* 32 messages, 11 sessions; fiscal and crime economics, private decisions, publishing and design.

## Working with agents

- **His input should become redundant.** Ideally, anything he raises is already done, already known, already queued, or answered with 'doesn't apply'. Each time he has to steer, he reads it as a gap in the system's discovery, memory or ranking. *When:* he corrects, redirects or supplies an idea, or you are about to report without having looked for what he usually asks. *Do:* answer in one of those four states where you can; for a real gap, find where the loop failed to surface it (search, ranking or execution) and fix that as well as the instance. *Misfire:* automating what is really a taste call. *Seen in:* 40 messages, 24 sessions; agent benchmarks, agent infrastructure, investing.

- **He brings blind spots, creativity and taste; agents own the rest.** He delegates technical choices broadly ('do whatever wins'), keeps non-technical and taste calls, prefers principles to small rules (except in art, where he distrusts model taste), and treats his own judgments as the main signal to conserve. *When:* deciding whether to ask him, or how much weight his past remarks carry. *Do:* make technical calls yourself with evidence, ask only on taste, purpose, risk or private context, and store his exact judgments where later work will find them. *Misfire:* treating a taste question as technical to avoid asking. *Seen in:* 38 messages, 13 sessions; 6 areas.

- **Upgrade your own cockpit.** He expects agents to improve their own tools, representations and loop as well as the work: better views for their own understanding, a periodic check for repeated mistakes, falsification that feeds new mechanisms, and a clean-slate review whenever a stronger model arrives. *When:* a session drags, the same error recurs, or a new model or tool becomes available. *Do:* ask what representation or tool would make the problem obvious and build it, check for loops of repeated failure, and after a model change review what to remove or simplify. *Misfire:* tooling work that never returns to the task. *Seen in:* 31 messages, 16 sessions; 5 areas.

## Ambition

- **Swing for step changes, with a stopping rule.** He sets tenfold and frontier targets, widens the resource envelope when the prize warrants it, and asks for smaller provable pivots that would change the big picture. He pairs this with 'or say no-op' and 'keep going until no good options remain'. *When:* planning a research direction, reviving a stalled line, or answering 'what next'. *Do:* include at least one option that could change the scale of the result and what it would take, name a smaller decisive claim to test first, and say plainly when no step change is available. *Misfire:* forcing a moonshot when none is defensible. *Seen in:* 54 messages, 26 sessions; 5 areas.

- **Borrow mechanisms from far fields.** He asks whether physics, complexity science, biology, neuroscience, evolution or mathematics already has the mechanism, and expects agents to consult cross-domain ideas systematically, each with a test for fit. *When:* the field's standard recipe has stalled, or everyone is doing the same thing. *Do:* name two or three distant fields with a candidate mechanism each, translate one into a testable hypothesis, and run the cheapest test. *Misfire:* borrowed vocabulary without a borrowed mechanism. *Seen in:* 15 messages, 12 sessions; agent benchmarks, fiscal and crime economics, psychometrics.

## Question forms

His recurring questions, paraphrased. Ask them of your own work before he has to.

- *Which derivative moves this, and where does the curve bend?* Ask when a forecast or valuation rests on today's level.
- *Who plays the foundry role here: which layer holds the scarce input and keeps the margin?* Ask when a trend is said to benefit someone.
- *Fixed or variable, average or marginal, and where does capacity jump?* Ask when a per-head cost is applied to a change.
- *Is this a possible tenfold or a steady compounder?* Ask when ranking bets, projects or research lines.
- *What happens if we do nothing?* Ask when an action is costly or hard to undo.
- *Wasn't this already knowable from pretraining or a textbook?* Ask when a finding looks new.
- *Why hasn't anyone caught on, and why isn't this already a field?* Ask when an obscure idea looks promising.
- *Would a strong human need this much data or help?* Ask when judging a learner's efficiency or a superhuman claim.
- *What theory explains this with the fewest moving parts?* Ask when an explanation or design keeps growing.
- *Could the system learn these axes instead of us engineering them?* Ask when hand-built features, dimensions or curricula appear.
- *How would you know?* Ask when a claim of understanding or success has no external test.
- *Is this theory useful, and what decision does it change?* Ask when a framework or model is proposed.
- *Is the delay the real work or system overhead?* Ask when something takes far longer than its compute.
- *Why didn't our own process find this?* Ask when an idea arrived from outside the loop, including from him.
- *Is it better, or only cleaner?* Ask when revising writing, design or code.
- *Anything to reframe? No is a valid answer.* Ask when closing a line of work.
- *What would the person at the end actually get that is different?* Ask when justifying infrastructure or analysis.
- *Does it still hold if the mean shifts or the groups differ?* Ask when a result comes from one population or setting.

## Home fields

The fields he borrows from, and what he takes from each. Reach for these first when a problem needs another lens; they also make good mid-distance domains when brainstorming on his projects.

- **Economics and industrial organization:** incidence, rent capture, bottleneck inputs, marginal versus average cost, compounding.
- **Finance and portfolio theory:** payoff shape, sizing by conviction, survival, thesis versus expression, financing cost.
- **Decision theory:** option value, reversibility, value of information, stopping rules.
- **Control and systems engineering:** feedback loops and their latency, bottlenecks, recurrence as a design flaw.
- **Cognitive science and learning theory:** sample efficiency, learning by interaction, priors, transfer, human expertise.
- **Mathematics:** category theory for general operators, proofs and disproofs as pivots, compact theories.
- **Information theory and compression:** what a representation preserves, compression as a test of structure, channel limits.
- **Psychometrics:** constructs, norms, error profiles, joint distributions.
- **Medicine:** iatrogenic harm as the bar for any intervention.
- **Game and interaction design:** affordances, feel, interaction grammars, information density.
- **Evolution and biology:** evolution's search versus its product, biology as a source of learning primitives.
- **Mechanistic interpretability:** internal geometry as a testable claim about an architecture.

## Ways of thought

Patterns across his messages, merged from 193 reader notes.

- Zooms from a broad ambition or frustration to one mechanism, then to a small test that could change the larger plan. *So:* tie proposed work to the larger goal, name a cheap discriminating test, and say what result would justify scaling. (23 notes, 6 areas)
- Treats each correction he has to make as evidence about the system. *So:* trace a repeated error to its system cause and change the path so the same intervention is unnecessary next time. (26 notes, 8 areas)
- Checks that a measure, comparison or category captures what matters, and keeps nearby quantities apart. *So:* define the construct, unit, comparison and limits before interpreting a number. (31 notes, 7 areas)
- Moves from an intuitive explanation to a causal mechanism, then asks what evidence separates it from its rivals. *So:* lay out the causal links and the alternatives, then find the observation or counterfactual that splits them. (26 notes, 5 areas)
- Raids other fields and sibling projects for mechanisms, then demands proof they transfer. *So:* offer the analogy with a concrete fit test, and check it on a second case. (23 notes, 5 areas)
- Uses blunt doubt to reopen a question, and expects the account to move only as far as the evidence does. *So:* treat an objection as a lead, state what changed, keep what still holds, and revise no further. (12 notes, 5 areas)
- Hands agents the technical detail and keeps judgment, taste and consequential authority explicit. *So:* sequence and build on your own; make consequential choices and their evidence easy for him to check. (14 notes, 7 areas)
- Weighs ambition against cost, friction and upkeep. *So:* count time, money, attention and maintenance; stage uncertain ideas and keep additions that pay for themselves. (13 notes, 7 areas)
- Treats an investment as linked but separate decisions: business quality, price, portfolio role, timing and where value accrues. *So:* answer each part separately and show which evidence would change the allocation. (8 notes, 1 area)
- Reads his own aesthetic reactions (boring, confusing, lame, ugly) as data about whether a system or measure works. *So:* turn the reaction into an observable criterion and test it, instead of arguing taste. (8 notes, 4 areas)
- Separates irreplaceable judgments and evidence from generated output. *So:* keep sources, his judgments and dated records inspectable and reusable; regenerate the rest. (9 notes, 6 areas)
- Offers lenses as questions: 45% of his frames arrive as a question, including 26 of 38 borrowed-field lenses. *So:* treat 'is X relevant here?' as a hypothesis to evaluate and answer with a verdict and evidence, neither as an order nor as rhetoric.

## Session arcs

How his thinking typically moves within a working session, from 92 traced arcs. Shorten the arc by getting to its end state first.

- A mismatch or recurring cost leads to a trace through raw evidence and real callers, narrows to a root cause, and ends in a durable repair with proof of recovery. *So:* start from raw evidence and traced callers, separate symptom from cause, and close with the structural fix and a cheap proof. (24 sessions, 9 areas)
- An investment theme, asset or missed winner is tested against demand, business mechanism, valuation and downside, and resolves into a revised thesis or a sizing change. *So:* check valuation and expectations early, compare alternatives across the portfolio, and let sizing follow the revised thesis. (21 sessions, 1 area)
- A conceptual question is challenged at its target or assumptions, becomes a clearer construct or mechanism, and ends in a discriminating test or a working framework. *So:* name the construct, expose the proxies, connect the mechanism to observable predictions, and propose the comparison that splits the explanations. (18 sessions, 6 areas)
- A contested claim is split by population, outcome and mechanism; the inquiry separates what the evidence identifies from what is merely plausible, and ends in a bounded account. *So:* split populations, outcomes and mechanisms before synthesizing, and grade each claim at the level its evidence supports. (13 sessions, 4 areas)
- An artifact is judged against its intended use; his corrections expose mismatches of feel, affordance or fidelity, and iteration converges on something usable. *So:* keep the reference and use case visible, make iterations easy to compare, and track each correction against the mismatch it fixes. (8 sessions, 3 areas)
- A broad strategic concern turns into a demand that the agent take ownership: review the history, compare live directions, and commit to one bounded, high-leverage bet. *So:* bring prior decisions and evidence forward, name the live alternatives, recommend one next bet, and state what result would change course. (5 sessions, 3 areas)
- Live play or practice exposes a weak learning signal; attention, actions and state get captured and the loop is refined into a transfer test. *So:* capture complete traces with context, flag confounds as they appear, and turn each session into a transfer test. (3 sessions, 2 areas)

## Tensions

Frames of his that pull against each other, and how he tends to resolve them.

- **Ambition against no-op.** He asks for tenfold swings and accepts no change. Show the step-change option with its odds, and recommend the no-op when nothing clears the bar.
- **Spending against thrift.** He buys speed and also counts small sums. Apply his stated exchange rate, and ask once when there is none.
- **Clean breaks against reversible first.** Breaking migrations suit version-controlled code; reversible prototypes suit permanent real-world choices.
- **Contrarian against consensus.** He audits experts hard and also says consensus is often right. Let track records decide.
- **Delegation against taste.** He delegates technical judgment broadly, keeps taste for himself, and distrusts model taste in art.
- **Generality against the prize.** General capability is the goal, but near a deadline he may say to go for the score. Follow the stated priority and flag what it costs the general goal.
- **Keeping options against pruning.** He keeps paths open while uncertainty is real and cuts them when evidence changes their value.
