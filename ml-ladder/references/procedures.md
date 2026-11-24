**Verdict:** done. The classic sources agree on one ladder: look at the data and environment, build the pipeline end to end with dumb and constant baselines, overfit something tiny, solve probes a correct learner masters in seconds, then grow one thing at a time. Before believing a score: beat a dummy model, run seeds with intervals, keep an untuned split, and watch episodes. No source gives a numeric stop-tuning rule. Ng comes closest: diagnose bias, variance or mismatch, then run his Optimization Verification test, which says whether to fix the objective or the optimizer (E). The 2026 papers cover three of our four failures: tuning instead of instrumenting [CA], marginal tweaks without a change of direction [AR, EV], and validating on seen seeds [CA]. None measures the constant-policy failure.

Tags: **VERIFIED** means the quoted words were matched against the primary text, using pdftotext of the PDF or the page source (`qcheck.py`). **UNVERIFIED** means the item is a paraphrase I could not match, or a source I did not read.

Sources: K Karpathy [Recipe](https://karpathy.github.io/2019/04/25/recipe/); J [Jones](https://andyljones.com/posts/rl-debugging.html); S [Schulman](http://joschu.net/docs/nuts-and-bolts.pdf); I [Irpan](https://www.alexirpan.com/2018/02/14/rl-hard.html); H arXiv 1709.06560; A arXiv 2108.13264; G [Tuning Playbook](https://github.com/google-research/tuning_playbook); L arXiv 2108.02497; KN arXiv 2207.07048; P [37 PPO details](https://iclr-blog-track.github.io/2022/03/25/ppo-implementation-details/); N Ng, *Machine Learning Yearning* draft; DM [DeepMind specification gaming](https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/); SU [Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html); CA arXiv 2609.18996; AR arXiv 2609.30541; EV arXiv 2609.13299.

## A. The ladder when a learner fails

1. **Look before modelling.** "The first step to training a neural net is to not touch any neural net code at all" [K, VERIFIED]. For RL: "Visualize random policy: does it sometimes exhibit desired behavior?"; "Histogram observations and rewards" [S, VERIFIED]. If a random policy never shows the desired behaviour, the problem is exploration or the reward, not the learner.
2. **Prove the task solvable without learning.** Try "Human control" [S, VERIFIED], or a hand-written automaton policy [J, UNVERIFIED paraphrase]. If a cheat agent fed leaked information still fails: "how the heck can I expect it to solve the original problem?" [J, VERIFIED].
3. **Start from known-good code and change one thing at a time.** "writing things from scratch is the most catastrophically self-sabotaging thing you can do" [J, VERIFIED].
4. **Build an end-to-end skeleton with dumb baselines.**
   - "Verify that your loss starts at the correct loss value" [K, VERIFIED].
   - An input-independent baseline "should perform worse than when you actually plug in your data" [K, VERIFIED].
   - "Run Your Baselines", but "Don't expect them to work with default parameters" [S, VERIFIED].
5. **Overfit something tiny.** "Overfit a single batch of only a few examples (e.g. as little as two)" [K, VERIFIED]. A loss that does not reach about zero means a bug in the loss, the labels or the optimizer.
6. **Run the probe environments in order** [J]:
   1. Constant reward: tests the value loss and the optimizer.
   2. Observation-dependent reward: tests backprop.
   3. Two-step delayed reward: tests discounting.
   4. Action-dependent reward: tests the advantage and the policy update.
   5. Action plus observation: tests batching.

   "it should only take a second or two to learn them" [J, VERIFIED]. A value "more than an epsilon away from the correct value, it means you've got a bug" [J, VERIFIED].
7. **Keep tests to seconds.** "don't try to debug your implementation by just running it on your full task" [J, VERIFIED].
8. **Unit-test the tricky arithmetic:** discounting at resets, advantages, and the pairing of rewards with observations [J, UNVERIFIED paraphrase]. In PPO, "approx_kl stays below 0.02, and if approx_kl becomes too high it usually means the policy is changing too quickly and there is a bug" [P, VERIFIED].
9. **Read the health indicators, not only the return:**
   - "Premature drop in policy entropy ⇒ no learning" [S, VERIFIED].
   - "KL spike ⇒ drastic loss of performance" [S, VERIFIED].
   - Explained variance of the value function [S, VERIFIED].
   - "Look at min/max/stdev of episode returns, along with mean"; "Look at episode lengths" [S, VERIFIED].
10. **Chase anomalies.** "Give up on your plan for the day and chase the anomaly instead" [J, VERIFIED].
11. **Add complexity one item at a time.**
    - "Don't throw the kitchen sink at your model at the start" [K, VERIFIED].
    - "Always Be Ablating" [S, VERIFIED].
    - "only adopt changes that produce improvements that outweigh any complexity they add" [G, VERIFIED].

## B. Before believing a score

1. **Beat a dummy model.** "a dummy model which always predicts the same class label has an accuracy of 50% or 90% depending on the distribution of class labels" [L, VERIFIED]. Imbalanced accuracy "can get a high accuracy score by always predicting the majority class" [KN, VERIFIED]. Baselines "are chosen to demonstrate that any complexity in the new model is necessary" [L, VERIFIED].
   - After the leakage was corrected, complex models "do not perform substantively better than decades-old Logistic Regression models" [KN, VERIFIED].
   - For RL: random-policy and cross-entropy baselines [S]; a constant-action policy is my extension. No shuffled-label or sham control appeared in the sections read.
2. **Run several seeds and report intervals.**
   - "statistically different distributions can be attained just from the random seeds with the same exact hyperparameters" [H, VERIFIED].
   - Report "interval estimates via stratified bootstrap confidence intervals, as opposed to point estimates", along with IQM and "probability of improvement" [A, VERIFIED].
   - The sources give no fixed seed count. Henderson says "power analysis methods can be used" [H, VERIFIED].
3. **Check sensitivity.** "If too sensitive, it doesn't really work, you just got lucky" [S, VERIFIED].
4. **Never reuse the test set while you iterate.** Lones on sequential overfitting: "you train multiple models in succession, using knowledge gained about each model's performance to guide the configuration of the next one, and you use the same test set to evaluate each model" [L, VERIFIED].
5. **Check for leakage** [KN, VERIFIED]:
   - L1: train and test are not cleanly separated (preprocessing or feature selection on both, duplicates).
   - L2: illegitimate features.
   - L3: the test set does not come from the distribution of interest.

   Found in "20 papers across 17 fields … collectively affecting 329 papers".
6. **Watch single episodes.** "it is important to show not only returns but demonstrations of the learned policy in action" [H, VERIFIED]. Authors often report metrics "without giving any insight into what it actually learnt" [L, VERIFIED]. Irpan: "The much more common case is a poor local optima" [I, VERIFIED].
7. **Distrust big jumps and the study design.**
   - "implementation differences which are often not reflected in publications can have dramatic impacts on performance" [H, VERIFIED].
   - If the best trials sit at the edge of the search space, widen it [G, UNVERIFIED paraphrase].
   - "Never tune the `max_train_steps` number in a study" [G, VERIFIED].

## C. When to stop tuning and change the task or representation

The classic sources give heuristics only.

- **Assume a bug first.** "Most often, it turns out they've got a bug" [J, VERIFIED].
- **Shrink the task.** "New Task? Make It Easier Until Signs of Life" [S, VERIFIED]. "Why work on a hard problem when you don't even know the easier one is solvable?" [I, VERIFIED].
- **Question the method.** "domain-specific algorithms work faster and better than reinforcement learning" [I, VERIFIED].
- **Explore before exploiting.** "Most of the time, our primary goal is to gain insight into the problem" [G, VERIFIED]. No numeric saturation rule appeared in the sections read.
- **2026 operational rule** [AR, VERIFIED], from one deployment:
  - Search-direction stagnation means "continues making marginal tweaks producing changes within noise, without recognizing the search direction is exhausted".
  - The redirect fires after a 5-iteration window at an 8% relative-gain threshold: "3 iterations was too frequent (firing on noise); 8 iterations was too late".
  - Config-level search "plateaued around baseline". "the human-driven Phase 3→4 pivot from content-only to behavioral+content embeddings produced the campaign best".
- **A failed search is not a verdict on the task.** "Stopping can waste an opportunity when the previous search tested only one representation" [EV, VERIFIED].

## D. What 2026 work says about agents as ML researchers

[CA]'s agents write game controllers, not learners; its findings transfer to research decisions.

- **Tuning versus instrumenting.** "frontier models build instruments while weaker models tune constants and re-run" [CA, VERIFIED]. After a near-timeout win, "Rather than tune parameters, the agent re-ran the scenario with instrumentation and found the cause", then "won the retest in 67% fewer loops". Another agent "blamed enemy attacks and built escorts, twice, and both fixes failed in replay" [CA, VERIFIED].
- **Plateau.** Agents reach "nine tenths of its final level within the first quarter to two fifths of the session". Late first-time clears are "essentially zero in all 21 cells" [CA, VERIFIED].
- **Stale validation.**
  - "65 of 91 self-terminated roguelike sessions ship without a single seed they had never tried".
  - In seven of nine models, "the last evaluation re-runs an unchanged policy, mostly on seeds already used" [CA, VERIFIED].
- **Fresh validation is the fix.** Refreshing the panels mid-session raised shipped success by a mean of +12.4 points, in "nine of nine completed pairs of twelve initiated" [CA, VERIFIED].
- **Stops follow the transcript budget, not the evidence.** The agent "stops when its transcript budget runs out far more often than when the evidence says done" [CA, VERIFIED].
- **Production failures** [AR, VERIFIED].
  - About 65% of 150+ iterations were productive. The rest was "waste from infrastructure failures, re-tests, and marginal tweaks".
  - Metric fixation: the agent "never questions whether it is the right metric, whether targets are feasible, whether the tradeoffs to meet the metric are reasonable, or whether the evaluation design has flaws".
- **Unscoped conclusions.** Agents "can remember an experiment yet carry forward a conclusion it does not justify". A coordinator restated a novelty-only rejection "as measured closure" [EV, VERIFIED].

## E. Which lever to pull

Ng's diagnosis comes first. Training error minus the optimal (human) error is avoidable bias; dev minus train is variance; when the training data differs from the target, a training-dev set separates variance from data mismatch [N]. Then match the symptom to a lever:

| Symptom (observable) | Lever the sources prescribe | Lever they warn against |
|---|---|---|
| Learner fails even on a trivial probe, a tiny batch or the initial loss | **Code.** "Most often, it turns out they've got a bug" [J, VERIFIED] | Architecture or hyperparameters: bugs are "a damn sight faster to find and fix than validating" a new architecture [J, VERIFIED] |
| Random policy never shows the desired behaviour; no signs of life | **Task or goal (make it easier), observation.** "Make It Easier Until Signs of Life", "Provide good input features", "Shape reward function" [S, VERIFIED] | Shaping that is not potential-based: "shaping rewards can change the optimal policy if they are not potential-based" [DM, VERIFIED] |
| High training error (avoidable bias) | **Architecture or size.** "If you have high avoidable bias, increase the size of your model" [N, VERIFIED]. Error analysis on ~100 training examples [N, VERIFIED] | Assuming the fix is permanent: "Increasing the model size generally reduces bias, but it might also increase variance" [N, VERIFIED] |
| Train good, dev bad, same distribution (variance) | **Data.** "Adding more training data will probably help close the gap between dev error and training error" [N, VERIFIED]. Karpathy calls real data "the by far best and preferred way to regularize" [K, VERIFIED] | Spurious inputs: "Any added spurious input is just another opportunity to overfit" [K, VERIFIED] |
| Train and training-dev good, dev bad | **Data distribution.** "You have a data mismatch problem" [N, VERIFIED]. Get data that resembles the dev set, possibly synthesised | Synthetic data that only looks right to people: "easier to create synthetic data that appears realistic to a person than it is to create data that appears realistic to a computer" [N, VERIFIED] |
| Learner reaches a high reward but does the wrong thing | **Reward or loss and the eval.** Ng's Optimization Verification test: if the true better output scores lower under your objective, it is an "Objective (scoring function) problem"; otherwise "you have a search algorithm problem and should focus on that" [N, VERIFIED]. Watch the behaviour [H, VERIFIED] | Trusting the literal reward. Specification gaming happens when an agent "exploit a loophole in the task specification"; task specification "includes not only reward design, but also the choice of training environment and auxiliary rewards" [DM, VERIFIED] |
| Metric improves but the thing you care about does not | **The eval itself.** "If your metric is no longer measuring what is most important to you, change the metric"; "If you later realize that your initial dev/test set or metric missed the mark, by all means change them quickly" [N, VERIFIED] | Metric fixation (agent never questions the metric) [AR, VERIFIED]. Tuning on the test set (sequential overfitting) [L, VERIFIED] |
| Dev or "Eyeball" set improves much faster than held-out | **The eval set.** "you have overfit the Eyeball dev set and should consider acquiring more data for it" [N, VERIFIED] | Continuing to select on the same set [L, VERIFIED; CA stale seeds, VERIFIED] |
| Tuning gains within noise for several rounds | **Representation, task or search direction.** Redirect after a window of 5 at an 8% gain threshold [AR, VERIFIED]. | More of the same knobs: "marginal tweaks producing changes within noise" [AR, VERIFIED]. Comparing ideas with nuisance hyperparameters left untuned [G, UNVERIFIED paraphrase] |
| Curves still rising at the step limit | **Keep training or add compute.** "Are the trials still improving at the end of training?" means compute-bound [G, VERIFIED]. "networks keep training for unintuitively long time" [K, VERIFIED]. "Run with More Samples Than Expected" [S, VERIFIED] | Tuning `max_train_steps` inside a study [G, VERIFIED] |
| Hand-built features versus general learning | **Long run: compute.** "general methods that leverage computation are ultimately the most effective, and by a large margin" [SU, VERIFIED]. A trend, not a decision rule | "building in how we think we think does not work in the long run" [SU, VERIFIED]. This conflicts with Schulman's short-run advice to add features: use them to get signs of life, then remove them |

Ng's guidance on speed and error analysis also applies here: "build and train a basic system as quickly as possible—perhaps in a few days"; "I usually create a spreadsheet and fill it out while looking through ~100 misclassified dev set images" [N, VERIFIED].

## Gaps

- [GAP] Suarez/PufferLib: no primary text found. A third-party paraphrase says fast environments matter or "results can be purely noise" [UNVERIFIED].
- [GAP] The Ng-Harada-Russell 1999 PDF has no text layer. The potential-based shaping claim rests on DeepMind's restatement.
- [GAP] Not read: GEAR 2605.13874, Heuresis 2606.25198.
