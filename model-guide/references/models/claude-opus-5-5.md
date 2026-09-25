# Claude Opus 5.5 — default Claude

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L29, L211-226.

**Opus 5.5** (`claude-opus-5-5`, 2026-09-22) is the recommended Claude default for headless, review and analysis work: it matches or beats Fable 5.1 on most of its card at 40% of Fable's token price (§ Claude Opus 5.5). The `opus` alias already serves it. Lanes pinned to `claude-opus-5` stay on Opus 5 until re-pinned, and cyber or dual-use biology work belongs there. Moving the interactive setting off Fable 5.1 is the operator's call. Preserve explicit task and fallback selections; a fallback example does not redefine the general routing role.

## Claude Opus 5.5 — recommended Claude default (2026-09-22)

**Operational specs:** `claude-opus-5-5`. $4/$20 per MTok, cache reads $0.20, batch $2/$10; Fast mode $8/$40 (Claude API and Claude Code). 1M context, 128K output, Opus 5 tokenizer, knowledge cutoff June 2026. Thinking is always on; effort runs `low` to `max` with an API default of **`medium`**. Output is more than 30% faster than Opus 5. Digest with system-card section numbers: [references/opus-5-5-system-card.md](../opus-5-5-system-card.md).

**Against Fable 5.1 (vendor card, max effort):** ahead on coding (SWE-bench Pro 89.9 vs 81.2; Terminal-Bench 4.0 66.4 vs 55.8), research math (ArXivMath 91.2 vs 82.9 without tools), long context (ProgramBench 91.2 vs 87.6), wide fact collection (WANDR 72.3 vs 68.7), chart reading without tools (Chartography 64.4 vs 44.8), knowledge work run by Artificial Analysis (GDPval-AA 1846 vs 1735; AA-Briefcase 1822 vs 1678) and agent teams of 1–100. Tied on deep-research reports (DRACO 87.4 vs 87.7) and on chart reading with tools. Slightly behind on OfficeQA's Treasury-table reasoning (78.9 vs 80.2). Anthropic: "the gap between Opus 5.5 and Claude Fable 5.1 is narrower than these scores suggest." At 40% of Fable's token price and fewer tokens per task, it is the default unless a named Fable edge applies.

**Honesty:** fewest confident wrong answers among the Claude models the card shows (AA-Omniscience public split: 17% incorrect, 7% abstain; Mythos 5.1 21% and 2%) and the lowest audit scores for input hallucination, false completion claims and user deception. MASK honesty under pressure is 87.4%: above Mythos 5.1 (84.6%), below Opus 5 (94.8%).

**Watch-items:**
- Effort matters more for research than on Fable: at `low`, DRACO 72.5 and WANDR 31.2 (Fable 5.1 at `low`: 84.2 and 63.3). Use `medium` or above for synthesis and `high` or above for wide collection. `opus-low` stays a briefed-execution lane.
- When a task requires a tool or code, it sometimes answers from memory or calculates by hand (§6.2.1). Require an execution receipt for computed numbers.
- It acted on instructions planted in user-pasted text in 2% of attempts at default effort and 7.4% at max; product mitigations such as Claude Code's paste tags brought that to zero. It also accepts unverifiable authorization claims more often, and in rare cases a lead agent told a subagent the user had approved something the user had not (§6.3.1). Subagent briefs should quote the user message behind any claimed approval.
- It is slightly more evasive on controversial topics than the Fable/Mythos weights. On the API it acknowledges opposing perspectives on 26.9% of political prompts (Fable 5.1 25.9%, Opus 5 46.9%), often offering to argue the other side later. Ask for the strongest opposing case explicitly.
- Classifier scope: most cyber re-routes to Opus 4.8 and dual-use biology is declined. Use Opus 5 by exact ID for both.

**Prompting and API deltas vs Opus 5:** set effort explicitly (vendor: 5.5 `medium` beats Opus 5 `high`); lower effort before prompting for brevity; on AA knowledge work `xhigh` finished 26–42 Elo below `max` with 41–51% fewer output tokens. Thinking cannot be disabled, forced `tool_choice` returns 400, and computer use needs `computer_toolset_20260801`. Progress notes arrive as `thinking` blocks (`display: "updates"`). Re-test Opus 5 anti-verbosity and over-verification scaffolding. It follows supplied writing rules and puts the important information first.
