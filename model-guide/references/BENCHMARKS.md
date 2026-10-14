# Frontier Model Benchmarks

**Last updated:** 2026-10-14
**Active scope:** Claude Opus 5.5 (primary since 2026-09-22), Fable 5.1, Claude Opus 5 (exact-ID lanes), GPT-6 Astra, Grok 4.7 (vendor launch table in [grok-4-7.md](models/grok-4-7.md)). Retired models' tables were removed 2026-09-25; git history keeps them. Comparisons to retired models remain only where a vendor used them as a baseline for a current model.

## Gemini 4 Argon launch (2026-10-13) — Google table, sources split

Who ran the evaluation decides how much each row is worth. "3P" means a third party ran it. "G" means Google ran Argon, and sometimes the rivals too. Read 2026-10-14; the per-row source attribution comes from emergent.sh, and the Vals rows were checked at vals.ai.

| Evaluation | Argon | GPT-6 Astra | Fable 5.1 | Opus 5.5 | Source | Routing read |
|---|---:|---:|---:|---:|---|---|
| Vals Index | **68.9** | 63.1 | 65.8 | 67.0 | 3P Vals | Knowledge work → Argon competitive at ½ cost |
| Vals Finance Agent v2 | **65.4** | 53.5 | 58.9 | 58.6 | 3P Vals | |
| AutomationBench | **51.3** | 41.4 | 31.4 | 42.5 | 3P Zapier (AA run reports 77.5: settings differ) | |
| FrontierSWE v2 | 55.0 | **65.5** | 56.3 | 62.3 | 3P Proximal | Coding → not Argon |
| Terminal-Bench 4.0 | 57.4 | 58.2 | 57.9 | **66.4** | G (Vals 57.6 agrees) | |
| Terminal-Bench Science 0.1 | 57.6 | **68.1** | 52.6 | 63.3 | G, 6× verifier timeout; Vals measured 44.3 | Inflated |
| DeepSWE v1.1 | **77.9** | 74.1 | 67.4 | 74.2 | G harness | Unreplicated headline |
| GraphWalks 256K–1M | **84.2** | 71.8 | 65.0 | 66.8 | G ran all | Long-context edge, unreplicated |
| LVBench | **91.7** | 87.5 | 79.7 | 83.7 | G, unequal frame budgets | Not comparable |
| AA Intelligence Index | 53 | – | – | **58** | 3P AA (Argon at High, rivals at max) | |

Price $2/$10 intro, $4/$20 standard. Full read: [models/gemini.md](models/gemini.md).

## Claude Opus 5.5 launch (2026-09-22) — system card Table 8.1.A

Vendor-run except where noted; max effort, mean of five trials. Full tables, effort curves and section numbers: [opus-5-5-system-card.md](opus-5-5-system-card.md).

| Evaluation | Opus 5.5 | Fable 5.1 | Opus 5 | GPT-6 Astra | Routing read |
|---|---:|---:|---:|---:|---|
| SWE-bench Pro | **89.9** | 81.2 | 79.2 | – | Coding → 5.5 |
| Terminal-Bench 4.0 | **66.4** (`xhigh`) | 55.8 | 52.3 | 57.9 | Terminal work → 5.5 or Astra |
| FrontierCode v1.1 Main | **54.4** | 50.3 | 48.0 | 53.3 | 5.5 peaks at `medium` (54.6) |
| HLE no tools / tools | **64.4** / **67.7** | 60.9 / 65.6 | 56.6 / 63.6 | – / 57.2 | |
| ArXivMath Aug 2026, no tools / tools | **91.2** / **96.9** | 82.9 / 92.1 | 78.1 / 90.4 | – | Derivation → 5.5 |
| GDPval-AA v2.1 (AA-run Elo) | **1846** | 1735 | 1708 | 1542 | Knowledge work → 5.5 |
| AA-Briefcase v1.1 (AA-run Elo) | **1822** | 1678 | 1673 | 1569 | |
| AutomationBench (Zapier-run) | 40.0 | 31.4 | 26.9 | **41.4** | Tie with Astra |
| DRACO deep research | 87.4 | 87.7 | **88.3** | – | Tie; 5.5 at `low` 72.5 |
| WANDR wide research (soft F1) | **72.3** | 68.7 | 67.1 | – | 5.5 at `low` 31.2 |
| OfficeQA / Pro | 78.9 / 67.7 | **80.2** / **69.0** | 78.1 / 66.9 | – | Fable slightly ahead |
| Chartography no tools / tools | **64.4** / **89.0** | 44.8 / 88.4 | 29.8 / 83.4 | – | |
| AA-Omniscience public split, incorrect / abstain | **17%** / 7% | 21% / 2% (Mythos 5.1) | 22% / 6% | – | Anthropic's run; not comparable with AA's published rates |

Price $4/$20 (Fable 5.1 $10/$50; Opus 5 $5/$25). Independent remeasure still pending: AA Intelligence Index and AA-Omniscience.

## Claude Opus 5 launch (2026-07-24) — vendor Pareto claims

Anthropic did **not** publish a full fixed-score table like prior system cards for every public bench row. Launch post emphasizes **effort × cost Pareto** charts. Until Artificial Analysis remeasures, treat the following as **vendor-reported direction**, not independent scores.

| Signal | Vendor claim | Routing read |
|---|---|---|
| Frontier-Bench v0.1 | SOTA; >2× Opus 4.8 reward at lower $/task | Default agentic coding → Opus 5 |
| CursorBench 3.2 | Within 0.5% of Fable 5 peak @ max, ½ $/task | Prefer Opus 5 over Fable for daily coding |
| ARC-AGI 3 | ~3× next-best | Novel problem-solving → Opus 5 |
| AutomationBench (Zapier) | ~1.5× next-best at same $/task; low effort still leads | Agentic SaaS → Opus 5 |
| OSWorld 2.0 | Best cost curve; beats Fable best at ~⅓ cost | Computer use → Opus 5 |
| GDPval-AA / HLE / DeepSearchQA | Launch charts claim best / most efficient | Knowledge work → Opus 5 |
| Life sciences (internal suite) | Beats 4.8 all rows; +10.2pp org chem, +7.7pp protein | Bio research (non-Mythos) → Opus 5 |
| Alignment audit score | 2.3 misalignment (lowest of recent Claude) | Prefer for long autonomous runs |
| Cyber (OSS-Fuzz) | Near Mythos at find; far behind at exploit | Keep cyber classifiers; fallback 4.8 |

**Price:** $5/$25 (same as 4.8). Fast mode $10/$50. Model ID `claude-opus-5`.

## Calibration (AA-Omniscience non-hallucination, 2026-06-18 read)

Of not-fully-correct answers, the share that were abstentions rather than confident fabrications. Current routed models: **GLM-5.2 72%**, Haiku 4.5 74%. **DeepSeek V4 Pro ~6%** — never use for unsourced facts or epistemic guardrails. Current Claude/GPT-6 remeasure pending; see [selection-trilemma.md](selection-trilemma.md).

## Specs And Pricing

| Model | Input/MTok | Cached input/MTok | Output/MTok | Context | Max output | Knowledge cutoff | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| Claude Opus 5 | $5.00 | - | $25.00 | 1M | 128K | May 2026 | Primary default 2026-07-24. Fast mode $10/$50 ~2.5×. |

## Sources

- Anthropic system-card registry: `https://www.anthropic.com/system-cards`
- OpenAI pricing/model docs: `https://openai.com/api/pricing/`, `https://developers.openai.com/api/docs/models/compare`
