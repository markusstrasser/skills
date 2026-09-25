# GPT-5.6 suite — Sol / Terra / Luna (superseded)

Moved out of SKILL.md on 2026-09-25 when GPT-6 Sol and Luna (2026-09-22) took over the cost tiers. The 5.6 ids stay registered in llmx for evaluation pins and named reproductions. Text below is unchanged from SKILL.md as of 2026-09-23.

**Naming:** generation number (`5.6`) + durable tier (`Sol` / `Terra` / `Luna`). Alias `gpt-5.6` → `gpt-5.6-sol`. **GPT-5.5 is removed** — do not route, upgrade, or price it.

| Tier | Model ID | $/MTok in/out | Role |
|---|---|---|---|
| **Sol** | `gpt-5.6-sol` | $5 / $30 | Flagship — coding, agentic, hard reasoning, cross-lab critique peer to Opus |
| **Terra** | `gpt-5.6-terra` | $2 / $12 (cut -20% 2026-07-30) | Mid tier — opt-in between Luna and Sol |
| **Luna** | `gpt-5.6-luna` | **$0.20 / $1.20** (cut -80% 2026-07-30) | **Everyday GPT** — ≈ prior GPT-5.5 perf at ~1/10 that price; also mechanical/lint at low effort; at this price the API lane is viable for BULK long-context fan-out (transcript reads ~$0.20/MTok in) without touching the codex subscription quota |

**Operational specs (all three):** 1.05M context, 128K max output, knowledge cutoff Feb 16 2026. Reasoning effort: `none` \| `low` \| `medium` \| `high` \| `xhigh` \| **`max`** (new beyond-xhigh). Default effort `medium`.

**Pro mode (not a separate slug):** API `reasoning.mode: "pro"` on Sol/Terra/Luna — more compute at the **same** $/MTok (higher token use). ChatGPT "Sol Pro" for Pro/Enterprise.

**`ultra`:** ChatGPT/Codex multi-agent setting (4 agents default) — not an llmx effort token yet; build via Responses multi-agent beta if needed.

**Cache (5.6+):** writes 1.25× uncached input; reads 90% discount; 30-min minimum cache life + explicit breakpoints.

**Routing defaults (this fleet is now the named cost-tier, not the GPT flagship):**
- GPT flagship / everyday Codex / formal review → **GPT-6 Astra**
- Mechanical lint / bulk extract → **Luna** (`low`)
- Mid-cost API bump → **Terra** (explicit `-m`)
- Named 5.6 Sol pin: `llmx chat --subscription -m gpt-5.6-sol`

**Calibration:** re-measure AA-Omniscience on 5.6 before trusting abstention. Until then, treat GPT critique as adversarial pressure on *reasoning*, not a fact source.
