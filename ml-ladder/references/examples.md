# Worked examples

Situations from three campaigns: arena (game-bot RL, 2026-11), ARC-AGI agents (2026-03 to 2026-11) and a pitch-detection benchmark with fine-tunes (2026-10). Two statistical-analysis projects supplied the same classes outside training (a pipeline that silently measured something else, a result its construction forces, a number carried outside its population) and no examples here. Each names what our agents did, what to do instead, and the artifact that proves it was done. The levers are ordered by which to check first. A mistake is here only if it happened in two projects or at least twice in one. The dated records behind them, with sources, are on the operator's machine under `~/.cache/arena/findings/2026-11-24-ml-mistakes-skill/`.

## 1. The harness (is the zero real?)

Check this lever first whenever a score is zero, flat or far below a person's, and whenever a new tool or arm is about to be scored: a broken harness produces the same numbers as a hard task.

### Online runs score 0 while the same agent wins offline
- **Tempting:** ARC-AGI-3, 2026-06-19. The online harness read `score` while the server reports `levels_completed`, so every online run scored 0. The session recorded "goal-direction is an unbreakable wall" as a strategic decision. Cost not recorded.
- **Instead:** Before you interpret any zero, push a scripted known win through the exact harness, scorer and transport the experiment uses. If it scores 0, stop the analysis and fix the harness. After one action, assert the observation changed.
- **Check:** a results row `positive_control` with the scripted win's nonzero score from the same scorer, and a log line showing the frame changed after one action.

### A new arm returns plausible numbers on its first run
- **Tempting:** ARC-AGI-3, 2026-07-18. The model transport parsed the wrong event schema, so every model call returned None and the "LLM" arm silently ran a round-robin fallback. The calls were still billed; the day's headline cell was void.
- **Instead:** Before launch, call every tool and model route the arm uses once against the live service and assert a real result. Count fallback events per run; fail any run with a count above zero.
- **Check:** a pre-launch log with one non-null response per named tool, and a `fallback_count` column of 0.

### Two arms meant to differ return the same curve
- **Tempting:** pitch detection, 2026-10. A warm-up ramp kept both EMA decays (0.999 and 0.9998) near a 1,300-step window in a 12K-step run, so the two arms could not differ. Another contest compared 36K steps against 12K. A choir loader had never run, so that suite produced no rows.
- **Instead:** Print each arm's effective config beside its result and assert that arms meant to differ do, in the values the run actually used. Assert a nonzero row count for every suite in every report.
- **Check:** an effective-config table with the differing field visibly different, and a per-suite row count with no zero.

## 2. The task and goal

Change the task when nothing wins after a few runs, when a trivial routine wins, or when the third variant of one mechanism ties the first two.

### Every full-task run wins 0 fights
- **Tempting:** arena, 2026-11-16. Cost not recorded. The agent never shrank the task; the operator proposed one, which found the floor at once: against an idle target, 0 of 18 runs learned the walk from 45 yd.
- **Instead:** When success is 0 after two runs, shrink the task until it has a known answer: one ability, an idle target, a short distance. Solve that, then add back one piece at a time.
- **Check:** a ladder table, one row per task size with its success count, each above 0 before the next runs.

### A bot that stands still scores almost as high as your best arm
- **Tempting:** arena, 2026-11-24 (Codex). A weight-searched bot won 626/640; standing still and pressing one attack won 624/640. Pretraining (0/384) and controls (1/96) were still scored on that panel: 480 fights on a test the turret passed.
- **Instead:** Before the first arm, score still, blind (enemy inputs removed) and constant policies on the exact panel. If any reaches the pass bar, add an opponent or situation that beats them, then rerun them.
- **Check:** a baselines table with rows `still`, `blind` and `constant`, each below the pass bar, dated before the first arm.

### You are designing a many-arm campaign to answer one question
- **Tempting:** ARC-AGI-3, 2026-07-22. An 11-arm, 126-cell transfer campaign booked 15-20 h of both lanes; the operator killed it 40 minutes in. The day before, a campaign measured the gap to a public harness whose recipe and traces sat in the repo.
- **Instead:** Write the question as one comparison on a few named cases and run that first. When a working recipe exists, copy it and reproduce its score before measuring against it.
- **Check:** a one-line question naming its comparison and cases, with its result row, committed before any multi-arm design.

### The third variant of the same mechanism ties the first two
- **Tempting:** ARC-AGI-3, 2026-06-19 to 07-24. One exploration prior was tuned four times; each later variant tied or lost. In 22 days the loop wrote 830 memos, 60% with no measurement, and held-out conversions stayed at 21/36.
- **Instead:** After two ties within one frame, stop tuning it. Change the frame (task, data, objective, interface), or watch ten episodes the agent fails and write what a person would do there.
- **Check:** a frame log listing each variant and its result; after the second tie, a new-frame entry or a file of ten watched failures.

## 3. The opponent, data or distribution

Change the opponent or data when the score plateaus near its ceiling against a fixed opponent, or when the situations that decide real play are rare or absent in training and eval.

### Win rate has plateaued near 95% against a fixed scripted opponent
- **Tempting:** arena, 2026-11-14/15. The agent built machinery for a 24 h, 10M-decision run and reported pass bars. the operator then beat the trained rogue 3 of 3. Cost: days of training experiments and launch machinery.
- **Instead:** Read a plateau against a fixed opponent as that opponent's ceiling. Change the data: a ladder of stronger opponents, one that adapts, or the operator's own play. Scale only once the new opponents produce a rising curve.
- **Check:** a learning-curve plot against the new opponent set, and one recorded fight against a human that you watched.

### Training data is synthetic and the score on it is 97.8%
- **Tempting:** ARC-AGI-2, date not recorded. A program-synthesis model's encoder separated the synthetic program types perfectly but lost spatial structure. Real tasks got valid but wrong programs, and cross-program transfer was 0/16. Cost not recorded.
- **Instead:** Score 10 real tasks before trusting any synthetic number, and again each time the synthetic score moves. If synthetic rises while real stays flat, change the generator.
- **Check:** a results table with a `real_10` column beside the synthetic score for every checkpoint.

### After 1,525 extra training rooms the onset losses have not moved
- **Tempting:** pitch detection, 2026-10. A data-augmentation round added room recordings and changed nothing; more augmentation was the next idea.
- **Instead:** Before a data or tuning campaign, score a ceiling on the same items and scorer: a large offline model, or perfect hindsight over the action set. Here a 24.6M-parameter offline model lost 2-5% of onsets in rooms against 15-21%, so the audio held the information and the small model was the limit.
- **Check:** a `ceiling` row beside the current score. A gap names model capacity or search; no gap sends you to the data or the task.

### Errors cluster where one note slides into the next
- **Tempting:** pitch detection, 2026-10. The singing delay sat in legato pitch changes, and the model was the first thing to change.
- **Instead:** When errors cluster at one boundary of the label definition, change the labels and hold everything else fixed. Re-segmenting only the singer labels (same audio, rows and batch order) bought 10.2 ms, and it replicated on a second seed.
- **Check:** an error table split by label type before the change, and a relabel-only arm whose config differs in the label file alone.

## 4. The reward or loss

Change the reward or loss when a degenerate policy (stall, constant, memorize) scores as well as a good one; leave it alone while success is still 0, as arena #3 showed: nine 2M-decision runs, plain, with a damage reward and with an unpinned first layer, all won no fight.

### Timeouts count as losses and the discount is below 1
- **Tempting:** arena, 2026-11-10 to 11-12. With γ=0.999, a loss at the 180 s limit weighed 0.17 at the first decision against 0.74 for a death at 30 s, so stalling was the cheapest loss. It trained that way for two days.
- **Instead:** Before training, compute under the exact reward and discount the return of each degenerate episode (stall to timeout, die early, idle) and of a win. The win must score highest.
- **Check:** a four-row return table (stall, early death, idle, win), win on top.

### Imitation loss falls and agreement rises while wins barely move
- **Tempting:** arena, 2026-11-17 to 11-19. Agreement with the teacher gained 34 points for 3.2 points of wins. 97% of the loss came from waiting decisions, and the teacher read 6 facts the student never sees.
- **Instead:** Pick the checkpoint by paired wins on the same starts. Split the loss by decision type, and diff the teacher's inputs against the student's before cloning.
- **Check:** a table of loss and paired wins per checkpoint, a per-decision-type loss breakdown, and a list of teacher-only inputs that is empty or justified.

## 5. The observation and action interface

Change the interface when the untrained learner cannot complete the key action sequence by chance, or when two states a player tells apart give the same input tensor.

### The caster presses its spell thousands of times, finishing none
- **Tempting:** arena, 2026-11-24 (Codex). The longest stationary run was 3 ticks; 2,696 of 3,009 presses came while moving, and 0 of 195 casts finished. An 11-11 hold prior never reached the new code. About 6 of 32 ledger rows.
- **Instead:** Before training, compute the untrained policy's chance of completing the key sequence once (a cast needs about 25 still decisions). If it is near zero, change the action space or add a hold prior.
- **Check:** that probability, printed for the initial policy, and a completed-cast count above 0 in one untrained episode.

### Before and after a key press, the observation is identical
- **Tempting:** arena, 2026-11-24. The duel's 24 input fields left out the bot's own sent inputs, so 16 of 16 Stride examples were identical before and after the press. On 11-15, standardisation zeroed constant spell-data columns. Cost not recorded.
- **Instead:** List zero-variance columns. Then take pairs of states a player tells apart (before and after own press, spell ready or not) and diff their tensors. Any identical pair is a missing feature.
- **Check:** a zero-variance column list and a diff table over named state pairs, every row nonzero.

## 6. The eval and the score

Change the eval when the headline number lacks its control, when the noise floor came from another score level, or when arms ran on different seeds or cases.

### Your trained bot beats the scripted bot 193–63
- **Tempting:** arena, 2026-11-24 (Codex). The reply led with "beat the current scripted bot 193–63" and "Some skill transferred". The same message reported that a script given the same 26-yard rule went 64–64.
- **Instead:** Give the baseline the simplest rule the learner might have found, run it on the same seeds, and lead with that comparison. Claim skill only for the margin over it.
- **Check:** a results table whose first row is the learner against the rule-matched baseline on identical seeds, with the headline taken from that row.

### One run beat the last by 0.43, "~14× the measured same-code spread"
- **Tempting:** ARC-AGI-3, July to September. A 0.03 same-code spread, measured at scores of 0.09-0.12, was applied at scores of 1-4. A +0.43 kept one loop version and a −0.19 reverted a runtime. Identical code later drew 2.79 and 3.78.
- **Instead:** Measure the noise floor by running identical code twice at the current score level on the same seeds. Compare as a ratio when noise grows with the score. Confirm any gain on a fresh seed block.
- **Check:** a same-code pair row at today's score level, and a second-block row on fresh seeds beside the claimed gain.

### A new latency metric improves on every arm
- **Tempting:** pitch detection, 2026-10. The first latency metric excluded misses from its median and counted sustained activity as detection, so empty and always-on outputs scored well. Every conclusion on it was withdrawn and rerun.
- **Instead:** Before any model, run the scorer on always-on, empty, oracle and too-early outputs. A degenerate output that scores well means the metric needs a gate (here precision at least 0.8). Baselines pass the same gates as the arms.
- **Check:** a scorer dry-run table with those four rows, each degenerate one failing.

### Dev and test are split by item
- **Tempting:** pitch detection, 2026-10. A split by note hash put one instrument's notes on both sides, and a tuning function fell back to all rows when no dev rows existed. Picking thresholds on test would have flattered latency by 34 ms. Two test suites were also inside the pretrained model's training data, and pooling hid the sign.
- **Instead:** Split by source (instrument, recording, game, opponent) and assert zero shared groups at build time. The selection function raises on an empty selection set. Read the pretrained model's data manifest before picking suites, print per-suite rows, and keep a reserve that is scored once.
- **Check:** a shared-groups count of 0, per-suite rows, and a reserve with one scoring date.

### Validation is fine and the deployed model fails
- **Tempting:** pitch detection, 2026-10. A recurrent head early-stopped on sequences that covered state ages 64-112; the browser streams from age 0 to about 2,600 frames. Streamed, it never reached the precision gate. The review had named the risk and the plan filed it as a limit.
- **Instead:** A limit that can void the arm gets a probe before the full spend: bench an early snapshot in the pipeline the model will run in.
- **Check:** a deployed-pipeline row for an early snapshot, dated before the full run.

### Frame F1 rises and the product gets worse
- **Tempting:** pitch detection, 2026-10. Frame F1 mostly measured how long fading pedal tails stay shown; the app displays chord names. The head with the better F1 named fewer chord changes correctly (0.48 against 0.55). The operator caught it.
- **Instead:** Before round one, write down what the user sees or plays and score that beside the standard metric. Select on it.
- **Check:** a product-metric column in every results table, and the selection rule naming it.

## 7. Scale and compute

Scale only after the small case succeeds and its curve still rises; launch a cheap run at once when it costs less than one more round of review.

### You are about to cite a 10^9-decision precedent for the next run
- **Tempting:** arena, 2026-11-21 and 11-23. With no small result working, the agent quoted a 10^9-decision precedent of about 200 days as a yardstick. It was recorded as the third time; on 11-23 the operator said "again".
- **Instead:** Any figure of 10^8 decisions or more names the small result that justifies it, with its curve. Without one, run the smallest version.
- **Check:** the proposal's first line cites a small-case result row with success above 0 and a rising curve.

### A USD 1.72 run is waiting on another critique round
- **Tempting:** arena, 2026-11-18. The run waited through nine critique rounds and nothing trained overnight. On 11-23 an agent turned a warning into "no training runs" and called it the operator's rule.
- **Instead:** After two review rounds that change only procedure, launch. When restating an operator rule, quote his words.
- **Check:** a launch timestamp no later than the second procedure-only review, and each cited rule matching a verbatim quote.

### A full-length run is about to launch on a new layer
- **Tempting:** pitch detection, 2026-10. A 36K-step run failed first on an out-of-memory error, then on a 4,500 s timeout, and produced no rows.
- **Instead:** Run a 300-step smoke first, read memory and seconds per step from it, and set the timeout to 1.5 times seconds per step times steps.
- **Check:** a smoke row with peak memory and s/step, and the timeout derived from it.

## 8. Reading the result

Before writing any verdict, watch at least one episode and count the claimed behaviour in the task's own terms; before reusing a negative, check it was measured in today's setup.

### Your bot won "8 of 8 against a pillar waiter"
- **Tempting:** arena, 2026-11-21. Counted as real hides, it was 19 of 32. League fights had line of sight blocked in 0 of 12,482 samples, against 7-30% in the operator's play. A flag called 328 of 830 refused lines clear.
- **Instead:** Count the behaviour from rendered episodes in the player's terms. Print how often the eval contains the deciding situation. Name a cause only after switching it off.
- **Check:** a table of watched episodes with the hand count beside the instrument's, a coverage line for the situation, and a knockout row.

### A past experiment "killed" the idea you are about to try
- **Tempting:** ARC-AGI-3, July to September. Prefix caching was cited as "0%" from runs on an older model after newer logs showed 25-37% hits. Other kills were reused after the model, runtime or binding constraint changed.
- **Instead:** Tag every negative with its model, runtime, checkpoint and binding constraint. When any of those changed, treat the negative as unverified and rerun its cheapest probe.
- **Check:** each kill entry carries a regime tag, and each reused kill shows a rerun after the last regime change.

## 9. Interventions that settled a question in minutes

Each replaced a cause read from code or a table. All are from arena, 2026-11.

| Move | What it settled | Cost |
|---|---|---|
| Give the scripted opponent the rule the learner found | A 193–63 win was one range threshold; with it the score was 64–64 | 12-16 s |
| Switch the suspected rule off | The pillar failure came from a different rule than the one first read from code: 0 of 32 hides ended became 26 of 31 | 3 min |
| Force the missing behaviour | Forced standing took damaging hits from 0 to 79 and wins only to 1 of 72: the cause of zero hits, and not the whole loss | one replay |
| Remove one input from the frozen actor | Without the enemy cast-bar features, dodges fell from 16 to 0 | no retraining |
| Fork a saved state so one decision differs | Every drill had a winning and a losing action; the forks then graded later arms | 69 s |
| Compute the hindsight ceiling | Perfect hindsight over eight reactions won 41 of 64 against 39 achieved: the losses were elsewhere | one sweep |
| Shuffle what the method claims to use | Shuffled openings cost 3 wins of 512; shuffled labels passed the drills and lost all 192 fights | one arm |
| Replay the frozen run against its stored result | The instrument read the run that was graded | one replay |
| Second block of fresh seeds | "44 of 64" became 34 | 7 min |
| Turn a playtest complaint into a scripted probe | The league had never contained an enemy waiting behind a pillar (0 of 12,482 samples) | an afternoon |
| Count the goal per route | Training took 220 of 269 box-hours for 5.2 minutes of the operator's play; written programs gave 21.2 | one review |

## Mistake classes left out

These had one incident each:
- A pass verdict no measured policy could reach (arena #8).
- Several changes made at once (arc-agi #6).
- Arms averaged over different sets of games (arc-agi #8); the same-seeds instruction in lever 6 covers part of it.

Measuring a stale worktree (arc-agi #7) is counted with the harness class and has no example of its own. Arc-agi #20 records a check that worked.
