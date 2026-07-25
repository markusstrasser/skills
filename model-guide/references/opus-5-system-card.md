# Claude Opus 5 — System Card / Launch Digest

**Released:** 2026-07-24  
**Model ID:** `claude-opus-5`  
**Price:** $5 / $25 per MTok (same as Opus 4.8); Fast mode 2× price (~2.5× speed)  
**Context:** 1M tokens (default = max); max output 128k (300k batch beta)  
**Knowledge:** reliable cutoff May 2026 (training); adaptive thinking default on  
**Primary sources:** [announcement](https://www.anthropic.com/news/claude-opus-5), [models overview](https://platform.claude.com/docs/en/about-claude/models), [prompting guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5), [system card](https://www.anthropic.com/claude-opus-5-system-card)

## Positioning

Near-Fable intelligence at **half** Fable 5's price ($5/$25 vs $10/$50). New default on Claude Max; strongest model on Claude Pro. Designed as the everyday frontier driver for long-running agents, coding, and professional work. Mythos 5 remains ahead on pure cybersecurity exploitation.

## Headline capability claims (vendor, launch charts)

Anthropic publishes effort×cost Pareto charts rather than a single fixed score table for every row. Qualitative claims from the launch post (treat as vendor-reported until AA independent remeasure):

| Area | Claim |
|---|---|
| **Frontier-Bench v0.1** | SOTA; **>2× Opus 4.8** mean reward at lower cost/task (mini-SWE-agent harness) |
| **CursorBench 3.2** | Within **0.5% of Fable 5** peak at max effort, half the cost/task; best cost-efficiency at high/xhigh/max |
| **AA Coding Agent Index** | Leads cost/performance frontier (launch chart) |
| **ARC-AGI 3** | **~3×** next-best model on novel-problem solve |
| **Zapier AutomationBench** | **~1.5×** next-best pass rate at same cost/task; lowest effort still beats other models' best |
| **OSWorld 2.0** | Best at any given cost; beats Fable's best at ~⅓ cost |
| **GDPval-AA v2 / HLE / DeepSearchQA** | Best / most cost-efficient on launch charts |
| **Life sciences (internal)** | Beats 4.8 on every life-sci eval; +10.2pp organic chem spectroscopy; +7.7pp protein-variant effect |
| **Vision / artifacts** | Stronger visual outputs (wind-tunnel / cell demos) |

**Cybersecurity (OSS-Fuzz):** near Mythos at *finding* vulns; substantially behind Mythos at *exploit development*. Cyber classifiers intentionally block binary-based scanning, pentesting, exploit gen; ~85% fewer classifier interventions than Fable. Flagged requests in Claude.ai/Code/Cowork fall back to **Opus 4.8** by default; API can enable automatic fallbacks.

**Biology:** same safeguard suite as 4.8; Fable bio blocks now route to **Opus 5** (not 4.8). Still limited on long-running autonomous bio research (Mythos stronger).

## Alignment (vendor automated behavioral audit)

- **Most aligned** of recent Claude models: overall misaligned-behavior score **2.3** (lowest).
- Best Constitution adherence vs Opus 4.8 / Sonnet 5 / Fable 5.
- Lowest deceptive behavior; least susceptible to misuse tricks.
- Safest on hard-to-reverse reckless actions.

## Prompting deltas vs Opus 4.8 (load-bearing)

From Anthropic's Opus 5 prompting guide:

1. **Default responses are longer** — effort controls *thinking*, not visible length. Prompt for concision explicitly if product-facing.
2. **Stronger self-verification** — remove "add a final verification step" / "double-check" scaffolding; it causes **over-verification** token waste with no quality gain.
3. **Scope expansion risk** — constrain narrow tasks: deliver what was asked; surface better approaches in one sentence, don't silently widen.
4. **More subagent-eager** — cap delegation; only spawn for large independent parallel tracks; don't use subagents to re-verify own work.
5. **Thinking disabled only at effort ≤ high** — prefer lower effort with thinking on over thinking off. Thinking-off can leak tool calls as text or internal XML tags.
6. **Code review** — if prompt says "only high-severity," it may under-report; ask for everything and filter later.
7. **Efficiency at low/medium effort** is a real primary control — re-run effort sweeps; do not carry 4.8 effort defaults blindly. For coding/agentic, `xhigh` remains the recommended starting point.
8. **Tools before effort** (§8.12, card text): *"agentic tool-use is generally a more cost-effective method of scaling test-time compute than adaptive thinking by itself."* Adding a verification command/probe to the brief beats bumping an effort tier — on cost and on quality.
9. **Hand it images, not descriptions** — SWE-bench Multimodal 38.4→**59.4 (+21pp)**, the largest coding delta in the release; OSWorld 2.0 55.7→70.6. Screenshot the render/plot/UI and attach the source.

## Verifier-conditioning — the liveness rule (§2.2 vs §8.14.2)

Two results from the same card, read together (`agent-infra research/2026-07-25-opus5-arc-agi-generalization.md`):

| Setting | Verifier | Result |
|---|---|---|
| ARC-AGI-3 interactive game envs | dense score every action | **30.2%** — 4× next-best (GPT-5.6 Sol 7.8 @ max), 20× Opus 4.8 |
| §2.2 24h/$10k autonomous protein-design campaign | none in-loop | both arms failed; one shipped 17 unranked designs, the other **shipped nothing and went silent for 8 hours** in self-verification loops (Mythos 5 delivered all 30) |

Same model. The discriminator is whether something scores each step. Consequences:

- Stripping over-verification scaffolding (delta 2) is a **liveness** fix, not token hygiene.
- Long autonomous runs need an **artifact-advance** watchdog, not just process liveness — `ps -p <pid>` stays green while the agent verifies in circles.
- Card caveats it as an early snapshot, not run at scale, presented as a *safety* result.

Note also §6.1.3: the model **relays subagent claims to users without verifying them**, and Anthropic concedes limited multi-agent coverage. Manifest-diff subagent returns; do not accept a summary as a result.

## API / product notes

- Effort default `high` on Claude API and Claude Code.
- Fast mode: ~2.5× speed, 2× base price (same shape as 4.8).
- Beta: mid-conversation tool changes without busting prompt cache; automatic fallbacks on classifier refusal.
- No data-retention requirements for general access (consistent with prior Opus).
- Tokenizer: same family as Opus 4.7+ (~30% more tokens vs pre-4.7 text).

## Local routing (this fleet, 2026-07-24)

| Surface | Pin |
|---|---|
| Default Claude headless / critique cosign | `claude-opus-5` |
| Cyber classifier fallback (vendor) | `claude-opus-4-8` (keep on llmx allowlist) |
| Fable (metered opt-in) | `claude-fable-5` when a named edge justifies 2× price |
| Interactive Max default | Anthropic product default is Opus 5; local `~/.claude/settings.json` may still pin Fable until operator flips |

## Open measurements (do not invent)

- AA-Omniscience non-hallucination / Intelligence Index for Opus 5 — **unmeasured locally**; 4.8's 64% non-hallucination stays the last independent Claude calibration point until re-run.
- Local effort-tier re-sweep (anim-workbench style) — **pending**.
- Subscription entitlement on Claude Code OAuth — dry-run routes; live self-report still required before tier-sensitive claims.
