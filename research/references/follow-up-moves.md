# Follow-up moves

These are the moves the operator kept making after research reports, mined from about 3,900 of his prompts across six projects: agent benchmark research, fiscal and crime economics, psychometrics, investment research, compression and one-off questions. Each is something he had to push because the agent did not do it on its own. Make these moves yourself.

**When to read:** before reporting a research result, closing a synthesis or asking what to do next; in a generate or Dreamer pass; when a line of work stalls.

**How to use:** scan the *When* clauses and pick the two or three moves whose trigger is visibly true now and whose answer could change the conclusion or the next step.

- `auto`: do it now, within the current authorization, and report the result with the finding.
- `propose`: do it if it is cheap and reversible; otherwise list it as a numbered next step with its cost.
- `operator`: it needs the operator's taste, private context or firsthand experience, so ask one concrete question.

Don't run the whole list, don't fire a move whose trigger is absent, and don't cite this file in the report.

Treat this as a menu, not a predictor. In a 2026-09-26 held-out test (54 real checkpoints), loading this file changed which moves the agent proposed, but not how often one of them matched the operator's actual next move: 11% with the file vs 9% without. Whether the extra moves are the ones he values is still his call.

For the lenses, tastes and ambitions behind these moves, see [operator frames](../../references/operator-frames.md). In long or unattended work, `operator-deck next` draws from both lists at each checkpoint and rotates them per project, so the agent prompts itself instead of waiting for him.

## Generators: new angles

The operator's distinctive input. Agents rarely make these moves unprompted.

- **What else must be true?** `auto`: assume the result holds and derive two or three other observable consequences (another total, group, period or sector), then check them. A missing consequence is evidence against the result. *When:* a headline number or causal story is accepted because it fits one observation. *E.g.* if a signal really predicts returns, it should also predict the related instrument and fade once published.
- **Run the model on the reference group.** `auto`: apply the same assumptions, cost allocations and inclusion rules to the comparison group. If they produce an absurd result there, the model is wrong, not the target group. *When:* a group comparison uses rules that were checked on one side only. *E.g.* if charging the majority population the same shared-cost allocation drives its lifetime balance negative, the allocation rule is broken.
- **Hunt the counterexample group.** `propose`: name the subgroup, setting, cohort or period where the relationship should fail if the explanation is wrong, and look at it. *When:* a pattern is generalized from pooled or narrow data. *E.g.* is there a high-skill origin group that is *not* a net contributor?
- **Rank the opposition, weakest to strongest.** `auto`: list the serious counter-positions and their best advocates, order them from easy to hardest, and answer the hardest directly. *When:* a contested conclusion is about to be reported, or a critique has only beaten weak objections.
- **Ask which field this really is.** `auto`: name the discipline that owns the problem's structure rather than its surface topic, then search that field in its own vocabulary for standard methods, known results and failure modes. *When:* progress stalls inside the current vocabulary, or a problem studied elsewhere is being solved from scratch. *E.g.* an agent's exploration problem studied as active learning in cognitive science.
- **Recast through a named expert.** `auto`: ask how a specific top practitioner would attack or criticize the plan, and turn the difference into one testable change. *When:* the plan is a list of small tweaks or has stalled.
- **Sweep for blind spots on both sides.** `auto`: list what the analysis has not considered, both for and against the conclusion: omitted outcomes, channels, populations, horizons and second-order effects. Rank them by potential to flip the result and check the top ones. *When:* an analysis is about to be called complete, especially a net-benefit or net-cost account.
- **Invert a load-bearing assumption.** `propose`: build a small case where one key rule, cue or dependency is reversed and everything else is held fixed, then see which explanation predicts the behavior. *When:* a result may ride on a familiar prior or a hidden assumption.
- **Run the multiverse.** `auto`: recompute under every defensible choice of definitions, bounds, exclusions and parameters. Report whether the sign and ranking survive, and which single switch flips them. Then name the common fallacies each side would commit. *When:* a conclusion rests on one set of modeling choices that a critic could reasonably change.
- **Remove the contested component.** `auto`: recompute without the component whose validity is disputed, and report both numbers. *When:* a composite, battery or index includes parts that may measure something else. *E.g.* an index gap with and without the subscale that depends on schooling.
- **Find the cleanest test.** `propose`: look for the setting that isolates the claim: a policy discontinuity, a lottery, a subgroup where the confounder does not vary, the instrument with the purest exposure. *When:* estimates are confounded, or a thesis is expressed through a mixed exposure. *E.g.* which listed company is the purest bet on the bottleneck the thesis names?
- **Swing bigger.** `propose`: when gains are small, propose one change aimed at an order-of-magnitude gain (a new representation, objective, data source or training signal) together with a cheap first test. *When:* several rounds of tuning give small or null gains, or every item on the plan is incremental.
- **Check what the objective rewards.** `auto`: reread how success is scored, and ask whether the current approach is rewarded or penalized by that score. *When:* bespoke components, hand-tuned heuristics or special cases are being added to a system that is judged on generality or cost.
- **Generation or selection?** `propose`: ask whether failures come from never producing a correct candidate or from failing to recognize one. Measure both, for example with oracle selection over the candidate pool. *When:* a generate-then-pick system underperforms and the plan is to generate more.
- **Rank findings by surprise.** `auto`: order results by how much they should move a well-informed prior, not by how striking they sound. Say what reversed, what is new, and what deepens something already known. *When:* synthesizing many results or closing a round.
- **Mine a new source for angles.** `auto`: when a paper, post or outside analysis arrives, list what it adds that the work lacks (angles, mechanisms, tests). Then cosign, discard or complement each load-bearing claim against evidence. *When:* a source is pasted into the conversation or lands in the queue.
- **Rescan since the last pass.** `auto`: if the evidence inventory is weeks old, search again for new cases, papers and data before concluding. *When:* a conclusion rests on a dated inventory or a fast-moving field.
- **Borrow from sibling projects.** `auto`: check what other projects already learned about this failure, method or data source (their lessons files, memos and decision records) and apply it. *When:* the problem resembles one solved, or failed, elsewhere.

## Checks he kept asking for

### Frame

- **Anchor to the real objective.** `auto`: state the target outcome and the capability or construct it requires, check whether the current measure and direction advance it, and report proxy results as proxies. *When:* a benchmark score, proxy or nearby objective is being treated as success.
- **Define the construct and the comparison.** `auto`: state exactly what is measured, in which population, against which reference group and with which outcome definition, and align both sides before comparing. *When:* groups, systems or periods are compared on differently defined measures.

### Evidence

- **Read the primary record.** `auto`: open the raw traces, the case-level records or the original source behind a consequential claim, and state how much you reviewed. *When:* a conclusion rests on an aggregate, a summary or a recollection.
- **Verify execution before judging capability.** `auto`: check liveness, positive controls, configuration and transport before reading a zero, blank or partial result as a limit. *When:* an arm returns all zeros or a suspiciously low score.
- **Check that the data can see the target.** `auto`: confirm that the dataset observes the construct, subgroup and links the analysis needs (lineage, generation, identifiers) before promising the analysis. *When:* a design depends on a variable no one has inspected.
- **Search aliases before declaring absence.** `auto`: try other names, formats and storage locations before calling something missing. *When:* a flat search returns nothing.
- **Check that examples are typical.** `auto`: compare the vivid cases with the distribution before letting them carry the argument. *When:* an argument leans on a few striking cases.
- **Ask for the operator's firsthand observation.** `operator`: when the operator has played the task, lived in the place or held the position, ask for the specific observation that would settle a validity question. *When:* data and traces disagree with intuition, or task validity is unclear.

### Mechanism

- **Name rival explanations and the observation that separates them.** `auto`: list the plausible causes and the evidence each predicts, then check the discriminating evidence before choosing one. *When:* a surprising result or failure has several plausible causes and the account names only one.
- **Decompose the failure path.** `propose`: trace a failure through perception, representation, reasoning, memory, objective discovery and execution to the earliest stage that breaks. *When:* an aggregate failure is blamed on its most visible cause.
- **Trace the mechanism end to end.** `propose`: map each step from input to outcome to the component that performs it, and name the missing step. *When:* a proposed method, architecture or causal story has no concrete path from evidence to outcome.
- **Audit incentives symmetrically.** `auto`: check how source mix, funding, question framing and accounting choices could shape the results, and apply the same scrutiny to the opposing side before inferring intent. *When:* a literature or institution looks one-sided.

### Numbers

- **Rebuild the headline from its components.** `auto`: recompute it from source totals, denominators, units, periods and allocation rules, keeping measured inputs separate from conventions and imputations. *When:* a quantitative headline depends on accounting choices or mixes periods.
- **Check the scale against a known total.** `auto`: scale the estimate up to a national, market or system total and compare it with an independent record, such as a budget line, census count or revenue. *When:* a per-unit estimate drives a large claim.
- **Compare distributions, not just means.** `auto`: report overlap, variance and tails alongside the mean gap. *When:* a group difference is summarized by a single mean.
- **State the bound and the reversal condition.** `auto`: give the plausible range and the specific finding that would flip the conclusion. *When:* reporting a contested estimate.

### Tests

- **Run the cheapest decisive probe.** `propose`: turn the uncertainty into competing predictions, then pick the smallest controlled test that can reject one of them. Set a cost cap and what each outcome triggers ("how would you know?"). *When:* a costly run, a broad design or a long analysis is planned with no small decision-changing test first.
- **Test transfer beyond the demonstrations.** `propose`: hold out new combinations, mechanics, groups or contexts, and report what transferred and what stays specific to the examples. *When:* one success is used to claim a general capability.
- **Beat the naive baseline.** `auto`: compare against random, majority, buy-and-hold or last-value baselines on the same cases. *When:* a score, hit rate or return is reported without a baseline.
- **Match the comparison conditions.** `auto`: check that model, effort, prompt, budget, data and harness match across arms, and record anything that does not. *When:* systems are compared, or an external result is set against ours.
- **Challenge extreme results.** `auto`: repeat the run, inspect intermediate cases and check the metric's behavior before trusting a near-perfect, all-or-nothing or single-run result. *When:* a result looks too clean.
- **Test a fix on a second case.** `auto`: apply a correction derived from one example to another relevant case before generalizing it. *When:* a process or data fix rests on a single example.

### Synthesis

- **Report outcomes before activity.** `auto`: lead with direct results on the target, then the mechanisms, then infrastructure and unfinished work, and say which conclusions reversed, held or are new. *When:* closing a work period with many activities and few clear results.
- **End on the next test.** `auto`: combine the results into what was learned plus the smallest experiment that would resolve what remains. *When:* results from several sources or lanes have accumulated.
- **Classify novelty honestly.** `auto`: search prior work and project history, then label the result as rediscovered, imported, adapted or new. *When:* a method or finding is about to be called new, or a paper resembles our approach.
- **Audit past calls as of when they were made.** `propose`: replay an earlier recommendation using only the information available at the time, separate reasoning quality from outcome, and say what the miss teaches. *When:* a prior call went badly or well and hindsight makes it look obvious.
- **Recompute when a premise changes.** `auto`: when a key fact is corrected, rerun the affected conclusion, not just the sentence that stated it. *When:* the operator or a source corrects a premise.

### Presentation

- **Explain it plainly.** `auto`: give the estimand, assumptions, magnitude and limits in plain words, with one concrete example when it helps. *When:* a technical result is hard to read, or easy to misread across groups or assumptions.
- **Make every chart answer a question.** `auto`: pick the simplest form that answers a distinct reader question, and state axes, bins and sign conventions; see [/figure](../../figure/SKILL.md). *When:* several charts or interactive controls are proposed.

## Running the research

- **Price the next move by what it can change.** `auto`: name the open decision and take the cheapest action that could change it; take no action when none earns its cost. *When:* several next steps compete, or optional work is proposed while a decisive result is pending.
- **Shrink the feedback loop.** `propose`: if an iteration takes hours, find a subset, proxy or smaller configuration that answers the same decision in minutes, and check that it agrees with the full run. *When:* the loop takes hours and decisions wait on it.
- **Test instead of arguing.** `auto`: when an open question can be tested, run or propose the experiment or eval rather than writing more analysis. *When:* a report ends with "it depends" or a list of considerations.
- **Don't gate discovery on the operator.** `auto`: discover, rank and act on whatever you can verify yourself, and bring the operator only questions of taste, risk and private context. *When:* you are about to ask for something you could find or decide.
- **Show one exemplar before scaling.** `operator`: produce one sample (a level, a memo section, a chart) for approval before generating many. *When:* you are about to mass-produce artifacts whose quality is a matter of taste.
- **Make the operator's judgment cheap.** `propose`: when progress waits on the operator's taste or observation, build a small review surface such as a contact sheet, a side-by-side view or a one-click rating page. *When:* the same kind of judgment will be needed many times.
- **Harvest what workers found.** `auto`: before generating new ideas, read subagent results, loop logs and parked ideas for leads nobody acted on. *When:* starting a new round of ideation.
- **Give every asset a consumer.** `auto`: name who uses each dataset, tool or archive, and for which decision; stop acquiring anything that has no consumer. *When:* a source or dataset is proposed, or an archive's role is unclear.
- **Check whether a rule's rationale applies.** `auto`: when a limit or rule blocks the next step, read why it exists and check whether that reason covers this case before deferring. *When:* a gate, cap or convention stops authorized work.
- **Fix recurring misses at the source.** `propose`: when the operator rescues the same omission twice, fix the shared step that should have caught it and test the fix on the triggering case. *When:* the same correction recurs.

## Domain packs

**Fiscal and social accounting**
- Keep fiscal cash flows, household welfare, production, debt and victim harms separate, and combine them only under explicit valuation and overlap rules.
- State the accounting boundary: population, period, items and counterfactual. Label each omitted channel as outside the estimand, unmeasured or overlapping.
- Allocate service costs by use and marginal capacity, not by flat per-person averages, and ask where the capacity thresholds bind.
- Don't read a change in the resident stock as arrivals.
- Report results by generation and arrival cohort, separate age effects from generation effects, and compare cohorts at a fixed number of years since arrival.
- Trace eligibility and take-up before assuming a program or remedy applies.
- Estimate benefits on the same population, period and allocation rules as the costs.
- For every response parameter, show its numerator, denominator and source, and say whether it was estimated, transported or assumed.

**Investment research**
- Before revising or defending an earlier recommendation, retrieve it together with its exit conditions.
- Judge the asset on its merits first; portfolio fit, funding and taxes come second.
- Trace the thesis through to earnings: demand, contracts, capacity, recognized revenue, margins, and who captures the value. Find the constrained input.
- Put the valuation on explicit upside, downside and timing, and use mid-cycle earnings for cyclicals.
- Compare against the real alternative use of the capital, after tax and financing.
- After a sharp move, explain it with dated evidence and separate business risk, thesis risk and price risk.
- Resolve the exact entity, listing and currency before applying any facts.
- Do the leverage and collateral arithmetic against survival, not only against expected return.
- Look for leading demand indicators that come before the reported numbers.

**Agent and benchmark research**
- Score discovering the goal or rule separately from executing the plan.
- Check each task's solvability, visible cues and leakage, and label it as diagnostic, training, validation or test.
- Compare human and model on the same evidence, tools and effort, and use the point where they diverge to locate the gap.
- Check a symbolic reconstruction against the rendered scene before trusting it.
- Keep scaffolds and hand-built tools out of the capability claim.
- When a result changes, separate the contributions of representation, optimizer and scale.
- Promote a candidate only when its gains convert on held-out evaluation under deployment constraints.

**Measurement and group differences**
- Check measurement invariance before comparing groups on a composite.
- Control for developmental stage (age windows) when groups mature at different rates.

## Habits behind the moves

1. He asks for raw traces, primary sources and case-level evidence before accepting aggregates.
2. He prefers small decisive tests with a stated decision value over big runs.
3. When a lane stalls, he widens the search across fields, eras, populations and counterexamples.
4. He treats his firsthand experience (playing the task, living in the place, holding the position) as data about validity.
5. He keeps proxies subordinate to the declared objective.
6. He expects comparisons to apply symmetric rules to every group or option.
7. He turns recurring misses into durable fixes.
8. He keeps data, tools and infrastructure only when a named consumer uses them.
9. He accepts "no change" when a change is not clearly better.
10. He asks bigger questions when progress is incremental: tenfold gains, other fields, other representations.
11. He expects the agent to discover and experiment on its own, and to bring him only calls of taste and risk.
12. He wants plain explanations, clear ownership and one explicit next move.

*Provenance:* mined 2026-09-26 from operator-authored prompts with GPT-6 Luna, merged across projects, curated by hand; examples are paraphrased. The method, the held-out evaluation and the coverage grades against the existing skills are in the agent-infra research memo `2026-09-26-operator-steering-moves.md`. The eval is `steering_anticipation` in the evals repo; it tested the frozen copy in its `arms/catalog.md`.
