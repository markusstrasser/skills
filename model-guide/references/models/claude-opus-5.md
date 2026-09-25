# Claude Opus 5 — exact-ID lane

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L228-251.

## Claude Opus 5 - exact-ID lane (primary Claude 2026-07-24 to 2026-09-22)

**Use for:** lanes pinned to `claude-opus-5`, cyber and dual-use biology work that Opus 5.5's classifiers block, and as the comparison baseline. Opus 5.5 replaced it as the recommended default on 2026-09-22, and the `opus` alias no longer reaches it. Transport readiness and workload quality are separate checks.

**Operational specs:** `claude-opus-5`, 1M context (default = max), 128K max output (300k batch beta), **$5/M input and $25/M output** (same as 4.8). Fast mode ~2.5× speed at 2× price ($10/$50). Adaptive thinking on by default; effort default `high` on API/Code. Knowledge cutoff **May 2026** (training). **Subscription-routable** (`lite_allowed_models`). Cyber-classifier refusals can auto-fallback to `claude-opus-4-8`; bio refusals on Fable now route here.

**Launch routing line (2026-07-24):** near-Fable capability at half Fable's price; Anthropic claims SOTA on Frontier-Bench, GDPval-AA, and best cost-efficiency on OSWorld 2.0 / AutomationBench / ARC-AGI 3 (≈3× next-best). Efficiency at `low`/`medium` effort is a real lever — re-sweep effort defaults. **Most aligned** of recent Claude models on Anthropic's automated behavioral audit (misalignment score 2.3). Prompting deltas vs 4.8: longer default verbosity (prompt for concision), stronger self-verification (remove redundant "verify again" scaffolding — it over-verifies), more subagent-eager (cap delegation), thinking-disabled capped at `high` effort. Digest: [references/opus-5-system-card.md](../opus-5-system-card.md). Prior 4.8 card kept for calibration history: [references/opus-4-8-system-card.md](../opus-4-8-system-card.md).

**Two shape-changes the launch line misses** (system card §8.12 / §8.2 / §2.2 — read 2026-07-25, `agent-infra research/2026-07-25-opus5-arc-agi-generalization.md`):

- **Tools beat effort — spend the budget there first.** §8.12 verbatim: *"agentic tool-use is generally a more cost-effective method of scaling test-time compute than adaptive thinking by itself."* Before raising a dispatch one effort tier, give it a verification command / probe / read-back tool instead — cheaper **and** stronger. This is a *cost* lever, not only a quality one.
- **Attach the image.** SWE-bench Multimodal 38.4→**59.4 (+21pp)** is the single largest coding delta in the release; OSWorld 2.0 +15pp. Screenshot-the-render / plot / broken-UI and hand it the source, instead of describing the visual defect in prose. Applies to rendered frames, QC plots, dashboards, CAD.
- **Its exploration gain is verifier-conditioned — this is the liveness rule.** ARC-AGI-3 1.5→30.2 (20×, dense per-action score) sits in the same card as §2.2, where two Opus 5 arms of a 24h autonomous design campaign delivered nothing and one **went silent for its final 8 hours in self-verification loops** (no in-loop verifier). Give any long autonomous run a per-step check it can score against, and bind completion to an advancing artifact — a live PID proves the process runs, not that it progresses.

**Prompting and API rules:**
- Use XML tags; adaptive thinking explicit (`thinking:{"type":"adaptive"}`); no manual `budget_tokens`.
- Default effort `high`; **`max` for architecture/design/high-reasoning critique** (operator 2026-06-20); `xhigh` for serious coding/review/long agentic work; `low` for gated mechanical dispatch (see Dispatch Economics).
- **Measured effort curve (Artificial Analysis, 2026-07-25) — `max` is a poor default:** AA Intelligence Index by effort — low **51** ($556 / 12M out-tok), medium **56** ($1,115 / 29M), high **59** ($1,974 / 52M), max **61** ($3,836 / 100M). low→max = **+10 points for 6.9× cost**; **high→max = +2 points for +$1,862**. At max AA flags it *"very verbose"* (100M vs 63M median); at high, *"fairly concise."* With §8.12 (tools scale test-time compute better than thinking), the rule is: **default `high`, escalate to `max` only for architecture/irreversible calls, and spend the delta on an in-loop verifier instead of the top tier.** AA's task mix ≠ ours — a strong prior, not a workload-specific verdict.
- **Calibration warning (AA, independent):** AA-Omniscience **Index 31 — below Fable 5's 40**, despite Opus 5 leading the Intelligence Index at 61. It leads on intelligence and trails on confident-wrongness — keep provenance tagging and claim verification on for factual work. Direction corroborated by the card itself (§6.5: *"hallucinates factual claims slightly more than Opus 4.8, despite being more accurate overall"*). ⚠ A widely-quoted *"hallucination +14pp → 50%"* figure is **UNVERIFIED** — it traces to a search-engine summary of an @ArtificialAnlys X post, and AA's own pages do not publish per-model accuracy/hallucination for Opus 5. Cite the Index gap (verified), not the 50%.
- Mid-conversation `role:"system"` messages supported immediately after a user turn — use for permission/budget/environment updates without rebuilding the prompt.
- No non-default `temperature`/`top_p`/`top_k` (400 on 4.7+); no assistant prefill; min cacheable prompt 1,024 tokens.
- Put long documents first and the query/instructions last.

Full guide: `references/PROMPTING_CLAUDE.md`.
