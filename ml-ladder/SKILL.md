---
name: ml-ladder
description: "Use when: a training, fine-tune, self-play or benchmark run of a learner or agent harness is about to launch, has just returned a score (zero, flat or high), or the question is what to run next (more runs, arms, hyperparameters, a bigger net, compute, a new reward). Load it BEFORE deciding or reporting. Preflight block with a checker, and which lever to change: harness, task, action/temporal abstraction, opponent/data, reward/loss, observation, eval, scale. NOT arm design (/doe), grader design (/eval) or causal why (/analyze)."
user-invocable: true
argument-hint: "[what you are about to run or the result you are reading]"
---

# ML ladder: make the smallest thing work, then change one lever

Our agents' repeated failure, across 67 dated incidents in five projects: a zero or a win
was credited to the learner when the harness, the panel or a trivial policy explained it, and the
response was more runs: brute force where an intervention or a smaller task would have answered.

Every check here is a run of seconds to minutes. None is a review round, and none blocks a run that
costs less than the check: launch that run and fill the block from it. After two rounds of procedure
without a new measurement, launch. Compile recurring checks (trivial policies, seed splits, scorer
negative fixtures, trace recounts) into one immutable repo referee once — never rewrite bespoke
scorers per run or pay a frontier model to recount raw logs. If ceremony, review, or artifact
repacking exceeds compute by >2× on a local $0 run, fix the loop before launching another run.

## 1. Preflight: fill these rows, in order, before any trained arm is scored

Scale it to the run. An experiment of minutes needs rows 1, 2 and 9, written as three lines in its
result. Fill the rest before a paid run, a run of hours, or a result that goes to the operator.
`scripts/preflight_check.py --template` prints `preflight.json` for those; keep it beside the run's
outputs and run `scripts/preflight_check.py preflight.json --arm-score <k/n>`. It checks rows 1, 2
and 4 to 9; row 3 is yours to write.

1. **The thing ran.** A case known to be solvable scores above zero through this exact harness. Every
   action or tool the learner is offered changes state once. Each arm's effective config is printed,
   and arms meant to differ do. The loader's distinct label or reward values are printed. A planted
   defect makes the eval fail. A zero before this reads the harness, not the learner.
2. **Trivial policies on the exact panel.** Score a constant policy (stand still and fire, always
   class A, always-on output), an empty or blind one (the input's or opponent's information removed),
   a random one and the scripted opponent's own rule, on the same opponents, seeds and split, through
   the same scorer, in the pipeline the model will run in (streamed state, full episode length, the
   deployed inputs). If one reaches the pass bar, the panel or metric cannot show skill: change it
   before training.
3. **The objective is a choice.** Write the objective in one sentence and two alternatives (the
   terminal result, a denser measure such as the health lead two seconds later, a comparison of two
   actions from one forked state). For each, give the return of a stalling, an idle and a winning
   episode: the win scores highest. Say which one the first run uses and what result would switch it.
4. **The pass is reachable, and so is the key event.** Name a measured policy that earns each verdict
   you could report. Compute the chance that the untrained policy completes the needed sequence once
   (ten still ticks at 10% each is 1e-10). If nothing can pass, or the event cannot happen by chance,
   no reward or architecture change will help.
5. **The smallest version.** List the sub-skills the task needs (hold still for one cast, walk to a
   point, break sight). Show the smallest one learned in minutes, or a probe with a known answer
   solved. If the small one fails, stay there. A full-length run follows a timed smoke of a few
   hundred steps.
6. **Same seed twice, same code twice.** One seed replayed gives the same trajectory. Two runs of
   unchanged code at the current score level give the noise, as a ratio; a difference inside it is
   a draw.
7. **Held out means held out.** Split by source (instrument, game, opponent, singer) and assert zero
   shared groups. Check the pretrained model's training data for your test set. Keep a reserve that
   is scored once, and a list of what each held-out item has already been used for.
8. **The learner can see what the player sees.** Two states a player tells apart give different
   inputs; list zero-variance columns; the learner's own last action is in its input.
9. **One episode watched (or played).** Open one trace or replay before any table, and write what
   happened in the task's own words (casts started, casts finished, why they broke). In an
   interactive environment, step through 1–2 live episodes — or run a fast geometry/physics
   reachability check — before theorizing from logs.

## 2. When it fails or stalls, pick the lever; a third run of the same thing is not one

| You see | Change | Leave alone |
|---|---|---|
| Zero or near zero everywhere | The harness: rerun row 1 | Representation, reward |
| A trivial policy matches the arm | The task, panel or opponent | More training |
| Policy breaks multi-step actions or cannot hold commitment across ticks | Action / temporal abstraction (macro-skills, action chunking, duration head) | Reward tweaks, LR sweeps |
| Nothing ever wins; random play never shows the behaviour | Establish one working positive control on the real task first (macro-actions, compact public features, imitation, or synthesized code), then ablate downward; or shrink the action space (rows 4, 5) | Reward variants, micro-slicing dead sub-tasks |
| Wins plateau against a fixed scripted opponent | The opponent or data: give the script the learned rule, add opponents that beat the trivial policy | Scale |
| A denser objective improves its own score and play stays the same | Whatever the watched episode shows is missing (the action never completes, the panel is trivial) | Another objective |
| High score, wrong behaviour in the watched episode | The reward or loss: does the objective score the better behaviour higher? If yes, the search; if no, the objective | The optimizer settings |
| The proxy rises (loss, agreement, frame F1) and the goal does not | The eval: score what the user sees or plays, paired on the same starts | The proxy |
| Validation good, deployed bad | The eval's regime: bench an early snapshot in the pipeline it will run in | More epochs |
| Train good, held-out bad | The data or labels; the split if it leaked (row 7) | Model size |
| Errors cluster at one label boundary | The labels | The model |
| Two variants inside one frame tied within noise | The frame: representation, task, or the cheaper route (a written program, a copied recipe, shipping what exists) | A third variant |
| Curve still rising at the step limit, preflight complete | Keep training or add compute | Everything else |

The last row is the only one that buys scale. A figure of 1e8 steps or more names the small result
that justifies it.

**Freeze dead branches.** After two consecutive valid children of one mechanism fail to beat the
strongest trivial policy on the real goal, freeze that branch and pivot the mechanism
(representation, action/temporal abstraction, imitation/program synthesis, or algorithm). Do not
keep micro-slicing a 0/N substrate into narrower sub-tasks that still lose the real game.

**Intervene before explaining.** A cause read from code or a trace is a guess until one of these,
each minutes long, has run: switch the suspected rule off; force the missing behaviour and count what
it recovers; remove one input from the frozen model; fork the saved state so one decision differs;
give the opponent the learned rule; shuffle the labels the method claims to use.

**Bound before searching.** Compute a ceiling first: perfect hindsight over the action set, or a
large offline model on the same items and scorer. If the ceiling is near the current score, the
losses are elsewhere.

**One comparison before a campaign.** Write the single-comparison version of the question and run
it, with an explicit branch for a null/zero result (what gets killed or pivoted if it scores 0/N).
If the answer exists (a published recipe, a script that wins), copy it before measuring the gap.
Probe any plan written right after a model reversal under pushback with a 5-minute test before
building harness or fixture code around it.
For a line of work older than three days, count the goal per route: minutes of the operator's play,
the shipped product's metric.

## 3. Reporting

- Put the strongest control next to the headline number, same panel and seeds, in the first sentence.
- State the regime: model, mode, checkpoint, panel, seeds. A win or a kill does not carry to another
  regime; mark it unverified there.
- One block of seeds is one draw. Run a second fresh block before telling anyone.
- A fork reproduces its source's score before any change is measured on it.
- Print per-suite rows beside any pooled number, on the items every arm shares.

## Where the rest lives

- `references/examples.md`: our own incidents by lever, each with what the agent did, what to do and
  the check. Read the section for the lever you are about to pull.
- `references/procedures.md`: the field's ladders (Karpathy, Jones's probe environments, Schulman, Ng,
  the Tuning Playbook, 2026 papers on agents as researchers), with quotes.
- Arms, shams and stopping rule: `/doe`. A grader or judge: `/eval`. Why a result happened:
  `/analyze`. A cheap probe before a paid run: `/verify-before`.
