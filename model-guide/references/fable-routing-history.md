# Fable routing history

Superseded by the 2026-09-05 plan and transport correction in SKILL.md. These excerpts are byte-exact from skills commit 2b29117 and preserve earlier claims, including errors; they are not current routing instructions.

**Claude Fable 5 — status (2026-07-12).** Off the claude.ai Pro/Max/Team subscription since 2026-07-07: continued access is priced at metered usage credits, $10/$50 per MTok (2× Opus 5) — press/pricing-page sourced (techtimes.com, bleepingcomputer.com, claude.com/pricing); reconciliation against observed usage is open, see Verified Transport below. Fable is reachable via `llmx chat -m claude-fable-5-1` (claude-cli transport; prior `claude-fable-5` remains an explicit pin) and headless `claude -p --model claude-fable-5-1` — **not reliably via the Agent tool**, where `fable-high`/`fable-low`-style dispatches currently serve `claude-sonnet-5` regardless of the pin (measured 2026-07-12, see Verified Transport — this is a mechanism bug, not a re-dormancy). Route gated/briefed/review dispatch to **opus-low** ($0 subscription); reach for Fable (via llmx, not the Agent tool) only with a named Fable-specific capability-edge justification over Opus `max`. Re-license trigger: Anthropic restores Fable to subscription plans.


## Verified Transport — what actually serves what (as-of 2026-07-14)

Routing *judgment* (which model you want) and routing *mechanism* (whether the lane you dispatch
to actually delivers that model) are different questions — this table is the second one, and it
currently has a serious hole. Re-verify any row before a tier-sensitive decision leans on it;
mechanisms drift faster than judgment.

| Lane | Actually serves | Status | Evidence / rederive |
|---|---|---|---|
| **Agent tool, any `subagent_type`, WITH an explicit `model:` param or agent-def `model:` frontmatter** (`fable-high`, `fable-low`, `opus-low`, custom agents) | **`claude-sonnet-5`** — the pin is silently ignored | **MEASURED, BROKEN — RECONFIRMED 2026-07-19 at scale** | arc-agi session 41f9b649, 2026-07-12: fable pin **5/5 self-reports**; opus pin **1/1**. **Re-measured 2026-07-19 (arc-agi team-lead 6f4a8626): explicit `model:"fable"` param → sonnet-5; explicit `model:"opus"` and hook-injected opus → sonnet-5 on every checked dispatch (raw-readers, builders) — ~15/15 cumulative. The Agent tool is currently a sonnet-only surface, full stop.** **[SUPERSEDED FOR OPUS PINS 2026-07-29: hook-injected `model:opus` → `claude-opus-5[1m]` self-reports 5/5 across five independent Agent-tool lanes in one night (arc-agi session e863d547: kaggle-envelope, negatives-audit, reasoning-study, routing-ab-rerun, harvest — each read back from a first-line self-report). Opus pins are HONORED on this evidence; the sonnet-only claim is STALE for opus. FABLE pins remain UNMEASURED since 07-19 — the verified-fable-dispatch two-stage llmx protocol stays in force for Fable until a fresh fable-pin probe. Grader-continuity consequence, live example: the 07-29 attack-routing rerun's grader served opus-5 where the 07-25 pass served sonnet-5, so its 0.875-1.000 replication band is cross-grader-MODEL agreement — confidence capped in that memo.]** Frontier-agent alternative VERIFIED same day: headless `env -u ANTHROPIC_API_KEY claude -p --model claude-opus-5` self-reports opus correctly (key-strip mandatory — with ANTHROPIC_API_KEY set it bills API and can fail "Credit balance too low"). Rederive: open the dispatch with "self-report your model ID from your own environment-info block, first line," read the answer back. |
| Agent tool, no `model:` param (bare `general-purpose` etc.) | `claude-sonnet-5` (`CLAUDE_CODE_SUBAGENT_MODEL`) | MEASURED, **correct** — this is the documented default, not the bug above | 2026-06-29 finding, unchanged |
| `llmx chat -m claude-fable-5-1` (claude-cli transport) | **Genuinely Fable 5.1** | Config-level 2026-09-05; 5 measured 2026-07-12 | Current Fable slug. Prior `claude-fable-5` remains an explicit pin. `llmx info --write-mirror` lists both. Dry-run: `llmx chat --dry-run --subscription -m claude-fable-5-1 -e high`. |
| Headless `claude -p --model claude-fable-5-1` (key-stripped) | Genuinely Fable 5.1 | Config-level; 5 measured 2026-07-04 | Interactive Claude Code on this machine already runs 5.1. Re-probe headless before a batch. |
| `llmx chat --subscription -m claude-opus-5` / `-m gpt-6-astra` / `-m gpt-5.6*` | Named model | Config-level, not self-report-verified | `~/.claude/cache/llmx-routing.json` `lite_allowed_models` confirms *routable*. |
| `cursor-agent --model cursor-grok-4.5-high --mode ask --workspace <repo>`; llmx exact `cursor-grok-4.5-*` slugs | Grok 4.5 through Cursor subscription | **MEASURED, CURRENT** (2026-07-14) | Live registry exposes low/medium/high plus trailing `-fast`; named high smoke and an unrevealed exact repo-HEAD canary passed. Critique preflight enforces registry + canary before dispatch. Bare `grok-4.5` remains xAI API, never Cursor subscription. |
| codex-cli / `llmx --subscription -m gpt-6-astra` | `gpt-6-astra` | Config-level 2026-09-05 | Operator Codex config `model = "gpt-6-astra"`. Omit `-m` to use it. Named `gpt-5.6-*` pins stay on the allowlist. `gpt-5.5` remains retired (exit 2). |

**Until the Agent-tool bug is fixed:** any Agent-tool dispatch where the model tier is
load-bearing (a cost claim, an eval arm, a "frontier vs cheap" comparison) needs a one-line
self-report opening the brief, read back before trusting the result. One line catches a silent
tier swap that otherwise bills or behaves as the wrong model.

**Fable cost status is unreconciled, not merely unverified:** the "$10/$50 metered" claim is
press/pricing-page sourced; the llmx usage log shows `claude-cli`-transport Fable calls
completing normally (large completions, zero errors) through 2026-07-12, after the cited
cutoff, and the log has no cost/auth-mode field to say which billing path fired. Whether Claude
Code's own OAuth entitlement is a separate pool from the claude.ai Pro/Max/Team plans the press
covered is **unverified (2026-07-12)** — check actual Console billing before a batch decision
hinges on "still $0" or "now expensive."


## Claude Fable 5 - "The Operator" (metered opt-in — reference only)

**Claude Fable 5.1 (`claude-fable-5-1`, 2026-09-01) — the 5 notes below are superseded where they conflict.** Same $10/$50, cache read $0.25 (was $1.00), 1M context, effort levels `low|medium|high|xhigh|max` with `high` the default. The guide's operative claims: effort names do NOT map across models — re-run any effort sweep per model; `medium` ≈ Fable 5 quality at lower cost; `low` is often competitive with Opus/Sonnet on cost per task while scoring higher, so include it wherever a smaller model at higher effort would run; at `low` it searches less (keep the research-skill gate on low-effort lanes); at `xhigh`/`max` it may draft a long deliverable in thinking and again in the reply — run long outputs at `high`, and only raise effort where a measured gain justifies it. Interactive Claude Code on this machine runs it on the Max subscription (the environment API key is rejected in `customApiKeyResponses`, verified 2026-09-02); the launcher passes `--effort max`, which the guide argues against as a default. Headless lanes stay on Opus 5 (`$0` subscription) unless a Fable-specific edge is named. Full delta and card evidence: agent-infra `research/2026-09-01-fable-5.1-tabula-rasa.md` §1.

Routability + economics: see the status note at the top of this skill (metered usage
credits 2026-07-07; llmx/headless lanes confirmed live and paid, Agent tool currently can't
reach it at all — see Verified Transport). Specs ($10/$50, 2× Opus), API shape (adaptive-only thinking,
hidden CoT, `reasoning_extraction` classifier, refusal→Opus 5 (bio) / Opus 4.8 (cyber classifier default) fallback), system-card insights
(two-source honesty regression vs Opus: AA-Omniscience 45% vs 64%), and prompting rules:
[references/fable-5-dormant.md](references/fable-5-dormant.md).


## Prior Agent-tool default guidance

**Agent-tool DEFAULT model is NOT the session model (2026-06-29).** `general-purpose`/most subagents default to **`CLAUDE_CODE_SUBAGENT_MODEL`** (now `claude-sonnet-5` — Sonnet 4.6 RETIRED 2026-07-07, never route to it), NOT the parent's Opus. A bare `Agent(...)` with no `model:` runs Sonnet 5 — fine for bounded work, a **tier silently-wrong trap when the dispatch IS the measurement** (an eval baseline, a "frontier agent" arm). **The previously-recommended fix — pass `model:` explicitly, then `grep '"model"'` the transcript — is not proven sufficient as of 2026-07-12:** the newer bug (Verified Transport) shows a pin can be requested and still not be served, and whether transcript-grep reflects the request or the actual serve is untested (ASSUMPTION: probably the request, since that would explain why grep-verification didn't already catch this). Require a first-line self-report instead — the one channel confirmed to reflect the true served model. Second footgun, same 2026-06-29 session: an open-ended "be exhaustive" prompt to `general-purpose` triggered **sub-delegation + stall** (6 children spawned, "I'll pause here," 72K tokens burned, nothing delivered) — for bounded research dispatches, define the scope and resource budget of any sub-delegation; prohibit further spawning only when that lane needs a fixed information or resource boundary.

## Contradictory Opus role wording corrected 2026-09-05

The active paragraph called Opus both the default and fallback-only. Current callers retain the default role. Prior wording:

**Opus 5** (`claude-opus-5`) is Anthropic's active top-tier model (released 2026-07-24): near-Fable intelligence at Opus price ($5/$25), 1M context, adaptive thinking on by default, SOTA on Frontier-Bench / GDPval-AA / ARC-AGI 3 / AutomationBench / OSWorld 2.0 cost-efficiency. Default for hardest Claude work, security/cyber/biology (Fable bio blocks now route here), and cross-lab review. **Architecture → `max` effort.** Keep `claude-opus-5` only as the documented cyber-classifier fallback target.
