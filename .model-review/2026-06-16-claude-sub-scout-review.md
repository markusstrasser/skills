Reviewed against the actual source (not the packet's self-description). Findings are cited to `model-review.py` / `llm_dispatch.py` line numbers.

## 1. Strengths and Weaknesses

**Strengths (verified):**
- **auth/mode plumbing is real and correct.** `llmx.api.chat` (`~/Projects/llmx/llmx/api.py:383`) pops `auth`/`mode`/`api_only` from kwargs and runs them through `resolve_auth` + `auth_to_llmx_kwargs`, so `dispatch()` passing them at `llm_dispatch.py:771-772` actually takes effect. `_resolve_call_auth` rejects passing both `auth=` and `api_only=` (570) and validates the token (574). `api_only` is kept as a deprecated path → existing callers don't break. This is clean.
- **`claude_review` profile** is `auth="subscription"` / `mode="chat"` (181-182) — matches the "never Claude API unless explicit" rule. No footgun there.
- **Graceful skip on missing binary** (672-684) genuinely doesn't block the review.
- `build_context`'s new `premise_scout_path` is keyword-only, default `None` (1085) → backward compatible; so is the dead-`api_only` path.

**Weaknesses (verified):**
- **The conviction gate the ADR sells does not exist.** `conviction` is only printed to stderr (2627-2629) and stuffed into the result dict (2690). Nothing consumes it — grep confirms zero gating logic. So "VOI *sequencing* — cheap scout raises conviction before expensive adjudication" is not implemented. What's built is "inject one more context section"; adjudication runs identically regardless of scout outcome.
- **Scout is synchronous and foreground, before dispatch** (2615-2623). The 300s timeout (539) is added to **every** review's wall-clock. Risk #2 in your packet is real, not hypothetical.
- **Default-on** (`--scout` default `True`, 2552): every existing `--context` caller now spawns a `cursor-agent` subprocess or eats skip overhead + a stderr warning. Silent new external dependency for CI/automation callers.

## 2. What Was Missed

1. **Skip conflates "couldn't run" with "low conviction."** No-binary (680), timeout (726), and non-zero-exit (739) all emit `conviction_after: "low"`. A genuine scout that ran and was unconvinced *also* emits "low" (and parse-failure emits "medium", 756). This is a textbook silent-proxy violation (your epistemic principle #8): the absence of a tool reads as a substantive low-confidence verdict. The moment anyone wires the ADR's `low → block` gate, **every environment without cursor-agent blocks all reviews.** Skip must be a distinct sentinel (`skipped=True` / `conviction="unknown"`), never "low".

2. **`--trust` on the live project tree.** `cmd` passes `--trust` with `cwd=project_dir` and `--workspace <repo>` (700-719), no worktree. Read-only safety rests *entirely* on `--mode ask`. That contradicts your own subagent safety rule (analysis agents must not write; default worktree isolation). One wrong mode flag = unsupervised edits to the repo under review, with permission prompts suppressed.

3. **Self-reported probe execution is never verified.** The prompt (542-579) asks Composer to run greps and report `disposition: "executed"` + a `result` string. Nothing validates the probe ran. A model can emit `{"action":"grep callers","disposition":"executed","result":"3 callers"}` without ever shelling out — i.e. the *exact* packet-only-invention failure mode the scout exists to kill, relocated one layer up. The ADR's "revisit if invents >1/10 scouts" guardrail has **no measurement harness** wired in.

4. **Model identity is double-sourced.** `PROFILES["premise_scout"].model = "composer-2.5"` (224) *and* `run_premise_scout` hardcodes `"composer-2.5"` in `cmd` (702). The profile is otherwise dead (no dispatch consumer). That's both dead metadata and a drift hazard (your epistemic principle #9): two definitions of the same invariant that can silently diverge. Either drive the subprocess from the profile or delete the profile.

5. **Scout output is pinned above the packet.** Scout block is `priority=450, drop_if_needed=False` (1107-1108); the actual provided context is `priority=400, drop_if_needed=False` (1122-1123). A verbose Composer dump ranks higher than the packet and neither can be trimmed → latent budget overflow that evicts nothing but can blow the limit.

## 3. Better Approaches

- **Make conviction load-bearing or drop the word "VOI."** Minimum: implement the ADR contract — `if conviction=="low" and irreversible: escalate/checkpoint`. Until then, rename honestly to "premise pre-check context injection." Don't ship the sequencing claim without the sequencing code.
- **Distinct skip sentinel.** Return `conviction=None` + `skipped=True` for no-binary/timeout/exit; reserve `low/medium/high` for *executed* scouts only. Fixes finding #1 permanently and pre-empts the gate landmine.
- **Run scout in a worktree, drop `--trust`.** Or verify cursor-agent's `ask` mode is provably non-mutating and assert it; live-tree + `--trust` is the riskiest combination available.
- **Background the scout** (your Risk #2): launch it concurrently with the slowest axis dispatch and join before integrate, instead of blocking 0-300s up front. Or cap timeout far lower (60-90s) since the prompt only asks for `<60s` deterministic probes.
- **Spot-check probe honesty:** for one claimed `executed` probe per scout, re-run the grep in-process and compare — turns "trust Composer" into a measurable invention rate (the ADR's revisit-trigger needs this data anyway).

## 4. What I'd Prioritize Differently

Order: (1) skip-sentinel fix — cheap, prevents a future global outage; (2) decide conviction gate *now* — either implement it or strike the VOI framing, because shipping the name without the mechanism guarantees a future reviewer re-derives this gap; (3) worktree/`--trust`; (4) background/timeout; (5) dead profile. I would **not** ship default-on until the scout latency is bounded and at least one real run shows Composer actually executes (not hallucinates) probes — flip the default to off, prove value on real packets, then promote.

## 5. Goals & Principles Alignment

- **Theater vs real fix:** As built, leaning toward theater. The mechanism that would make it a *fix* (conviction gating the expensive step) is absent; what remains is appending an unverified, self-reported premise check to the same packet the axes already see. It *can* help (repo-grounded premises are better than none) but it's "more context," not "value-of-information sequencing," and it imports the invention risk it was meant to remove.
- **Conviction=low gate (your Q5):** ADR says block only on `low AND irreversible`. Code blocks on **neither** — conviction is inert. Recommendation: implement `low + irreversible → human checkpoint` exactly as the ADR specifies, *after* the skip-sentinel fix, so "couldn't run" can never trip it. Don't escalate on bare "low".
- **Silent proxy (#8) and single-definition (#9):** both violated, as above. These are the two findings most aligned with your own stated principles and the ones I'd hold hardest on.

## 6. Blind Spots In My Own Analysis

- I did **not** run the test suite or a live scout — the `--trust`/`--mode ask` write-safety claim rests on my reading of the flags, not on cursor-agent's actual mode semantics; verify that `ask` is genuinely non-mutating before trusting #2's severity.
- "Theater" in §5 is partly a design judgment, not a pure fact — the injected premise section may reduce blindness even without gating; I can't quantify that without the `critique_replay` probe the ADR cites.
- I traced `voi-scout.json` consumers only within `critique/scripts/*.py` and the skill docs; if an orchestrator or `review_gate` elsewhere reads conviction, my "gate unimplemented" claim weakens — worth a repo-wide grep before acting on it.
- Test-gap list (timeout path, non-zero exit, malformed-JSON→medium fallback, 120k truncation cap, context-files-only warn-skip, auth/mode validation in `_resolve_call_*`) is inferred from `PremiseScoutTest` covering only 3 cases (916-961); I didn't confirm no other test file exercises them.
