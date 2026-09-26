# Claude Fable 5.1 — named-edge lane

> Moved from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Retired-model content pruned 2026-09-25 (git history keeps it). Source lines: L27, L268-274.

**Fable plan status — corrected 2026-09-05.** Fable 5.1 is included in Max and premium Team/seat-based Enterprise plans, within up to 50% of the shared weekly allowance. Pro and standard seats use credits. API calls and credits beyond the plan allowance remain metered; the operator's policy is Claude subscription only unless explicitly authorized otherwise. Fable 5.1 requires Claude Code ≥2.1.255; installed 2.1.261 supports it. [Anthropic plan rules](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan). Earlier blanket “off subscription” claims are superseded.

## Claude Fable 5.1

**`claude-fable-5-1`, released 2026-09-01.** API $10/$50 per MTok, cache read $0.25, 1M context and 128K output; adaptive thinking is always on, default effort `high`. [Official overview](https://platform.claude.com/docs/en/models/fable-5-1/overview). The global Claude setting selects `claude-fable-5-1[1m]`; explicit launcher effort takes precedence over saved settings. Preserve the operator's effort selection.

The September prompting guidance recommends testing effort per workload: names do not imply equivalent quality across models, low effort may search less, and high effort can duplicate long deliverables in reasoning and the reply. Use the requested effort; tune only against the task's verifier. The existing source digest and migration dispositions are in agent-infra `research/2026-09-01-fable-5.1-tabula-rasa.md` §1 and §10.

**Against Opus 5.5 (2026-09-22 card):** Fable 5.1 keeps a narrow lead on OfficeQA table reasoning (80.2 vs 78.9) and is marginally less evasive on controversial topics. It ties on DRACO deep research and trails on most other rows at 2.5 times the token price. Its `low` effort holds up on research far better than Opus 5.5's. Details in § Claude Opus 5.5.
