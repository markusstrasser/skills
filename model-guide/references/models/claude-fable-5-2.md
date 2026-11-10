# Claude Fable 5.2 — named-edge lane

> Replaced Fable 5.1 on 2026-11-10 (this file was `claude-fable-5-1.md`; git history keeps the 5.1 guidance, including the Endless Exam `high`-vs-`medium` output-cap finding). Card digest: [fable-5-2-system-card.md](../fable-5-2-system-card.md).

## Specs

**`claude-fable-5-2`, released 2026-11-09.** $8/$40 per MTok (Fable 5.1 was $10/$50), cache read $0.20 (2.5% of input), 5m write $10, 1h write $16; Fast mode $16/$80 (up to 2.5× faster output). 1M context, 128K output. Adaptive thinking is always on; effort `low|medium|high|xhigh|max`, API default `high` (Claude apps and Claude Code default `medium`). Forced `tool_choice` (`any`/`tool`) returns 400; omit `temperature`/`top_p`/`top_k`. The preserved-thinking prefix check applies to every account: editing `system`, `tools` or an earlier turn invalidates later thinking blocks and returns 400. [Overview](https://platform.claude.com/docs/en/models/fable-5-2/overview), [prompting guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2).

Mythos 5.2 shares the weights with fewer cyber and bio safeguards, and is limited to verification-program organizations. We have no Mythos access.

**Transport (verified 2026-11-10, Claude Code 2.1.321, key stripped):** `claude -p --model claude-fable-5-2` and the `fable` alias both report `modelUsage` = `claude-fable-5-2`. The `fable` alias moved from 5.1 on release day, so `fable-high`, `fable-low` and every `--model fable` lane already serve 5.2. Plan terms at launch: Fable counts within up to 50% of the weekly limit on Pro and standard Team seats (launch promotion); paid plans got one to three Fable usage resets. Claude stays subscription-only.

## Role

Opus 5.5 stays the default Claude. The vendor also recommends Opus 5.5 as the daily driver, and the operator re-selected Opus 5.5 as the interactive default on 2026-11-10. Use Fable 5.2 for a named edge:

- **Knowledge, table and business-workflow work:** OfficeQA 83.4 vs Opus 5.5 78.9; Remote Labor Index 41.3 vs 21.3; AutomationBench 51.4 vs 42.5 (Gemini 4 Carbon 53.9).
- **Long-horizon agentic coding at `high` or `xhigh`:** FrontierCode 2.0 45.3 at `high` for $6.72 per task, level with Opus 5.5's best (45.5, $12.82); 49.1 at `xhigh` for $14.19. `max` scores lower (45.7) at $44.70 per task.
- **Hard reasoning cheaply:** the vendor reports HLE with tools at `low` matching Opus 5.5's best at under a tenth of the cost per task, and WANDR at `medium` matching Opus 5.5's best at about 40% of the cost.
- **Orchestrator/advisor:** the vendor positions it as a planner that delegates to smaller models. At `xhigh` and `max` it starts subagents to review its own work.

All of these are vendor-run numbers (principle 8). No local eval has compared Fable 5.2 with Opus 5.5 yet. The open question is whether 5.2 at `low`/`medium` beats Opus 5.5 at `high` per token on our research and synthesis lanes; that comparison decides `fable-low`'s license. Until it is measured, the license stays suspended.

## Watch-items (card digest has the sections)

- **Long context regressed.** ProgramBench 85.6 vs Opus 5.5 91.2, because it ran out of its 1M context on 68% of tasks; a visible remaining-token counter lifted it to 91.6. Give long single-agent runs compaction or a budget, or use Opus 5.5.
- **Early stopping at lower effort.** It left 6–13% of coding sessions incomplete (Fable 5.1: 4%) and quit 63% of open-ended research sessions at `medium`. For unattended work use `high` or add the vendor "Finishing work" block (PROMPTING_CLAUDE.md).
- **Answer-key guessing.** Reward-hack attempts are no more frequent than in earlier models, but they succeed about twice as often, and it sometimes skips required tool use. Verifiers must check the method, not only the answer.
- **Calibration is contested.** The card reports the best AA-Omniscience net score so far (0.72), but internal users reported confident claims the code did not support. Keep facts tool-sourced (principle 6).
- **Self-preference below Opus 5.5** (§6.5.4). It is the same lab, so it still cannot serve as the cross-lab reviewer (principle 5).
- **Classifier fallbacks:** cyber goes to Opus 4.8; bio and frontier-model development go to Opus 5. About 55% fewer classifier blocks than Fable 5.1. Injection-heavy coding input fell back to Opus 4.8 99.5% of the time in the card's adaptive-attacker test. For untrusted tool output use Sonnet 5.5 or Haiku 5.5, and send cyber and bio work by exact id to `claude-opus-5` (principle 9).
- **Instructions written for earlier models.** "Answer directly without deliberating" no longer suppresses thinking at `medium`+; lower effort instead. Standing delegation lines and accumulated "never" cautions are followed closely and can stall routine work. See PROMPTING_CLAUDE.md § Fable 5.2 deltas.
