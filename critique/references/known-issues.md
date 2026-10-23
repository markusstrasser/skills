# Critique dispatch — known issues (append-only bug log)

> Moved from critique/SKILL.md (2026-07-06, progressive disclosure). Append new dispatch
> bugs HERE; SKILL.md keeps a one-paragraph pointer. Entries whose fix fully landed and
> carry no live operational guidance were pruned at the move (2026-04-11 Python-version
> mismatch, 2026-04-16 `.js`→`.json` anchor aliases, 2026-06-18 scout-budget cascade) —
> git history has them.

- **[2026-04-25] Claude Code verifier auth split** — `claude --bare -p`
  is the documented scripted/API-key path, but bare mode skips OAuth/keychain
  reads and uses `ANTHROPIC_API_KEY` or an explicit `apiKeyHelper`. On this
  machine the inherited API key path can fail with `Credit balance is too low`
  even while the local Claude subscription auth works. For read-only Claude
  Code verification from Codex/agent shells, prefer:
  `uv run python3 ~/Projects/skills/scripts/claude-code-verify.py --repo "$(pwd)" --prompt-file prompt.md --output claude-review.md`.
  The wrapper unsets `ANTHROPIC_API_KEY`, runs from a tiny temp cwd, passes the
  prompt on stdin, and restricts tools to read-only inspection by default. Use
  `--use-api-key` only when explicitly testing the API-key path.
- **[2026-03-27] shared dispatch output — never use shell redirects (> file) for review artifacts; the shared review script writes directly to files. Shell redirects buffer until process exit, producing 0-byte files.**
- **[2026-04-09; updated 2026-06-11] GPT-5.5 xhigh dispatch — set `--timeout 1800`-`3600` explicitly (xhigh runs 30-45 min; the 300s default is the footgun, auto-scaled to 1200s only as a net) and run it via `run_in_background` (foreground Bash caps at 10 min). llmx also treats `--max-tokens` as the visible-output budget with reasoning headroom added on top, so xhigh no longer returns-nothing-from-token-starvation. Parallel xhigh calls may still hit rate limits — run sequentially or use high effort.**
- **[2026-04-09] xhigh vs high for architectural review — marginal quality delta. High-effort adversarial review (4 min) found the sharpest insight across 6 reviews. xhigh (15 min each) had more words, similar signal density. Reserve xhigh for formal math only. For deep dives: 2-3 parallel high queries with focused questions > 1 xhigh mega-query.**
- **[2026-04-09] Context formatting matters — GPT-5.5 performs better with XML `<doc>` tags around context sections. Gemini needs query at END, critical constraints at END. Consult /model-guide before assembling context for manual dispatch.**
- **[2026-04-13] --verify pass can hang on a single finding** — model-review.py's `--verify` pass verifies each extracted finding serially. If one verification call gets stuck on a network round-trip, the whole process goes quiet even though extraction + per-model outputs are already written. Symptom: `arch-output.md`, `formal-output.md`, and `formal-extraction.parsed.json` are present in `.model-review/<topic>-<hash>/` but no `verified-disposition.md`. The process is alive but using <1s CPU. Action: kill the hung process and work from the extracted findings directly (`formal-extraction.parsed.json` is already machine-readable). Don't wait — the timeout doesn't help when the hang is inside the verify loop.
- **[2026-04-16] Never pipe `model-review.py` through `tail`** — stdout is full structured JSON (can be hundreds of lines). `| tail -40` silently drops the artifact paths and findings and keeps only closing braces. Read the artifacts from the review dir directly (`disposition.md`, `coverage.json`) or let the full stdout land in the shell. The script now prints a trailing `=== model-review summary ===` block that DOES survive tail truncation — if you must tail, tail ≥20 lines to catch it.
- **[2026-06-03] Cross-repo reviews — pass `--sibling-roots` or the HALLUCINATED rate lies.** The `--verify` pass resolved anchors only against `--project`. On a cross-repo packet (e.g. a genomics↔phenome bridge review where half the diff lives in phenome), every sibling-repo anchor was marked HALLUCINATED — a 5-axis bridge review hit **50.8% "hallucinated", and 2 of the 3 real bugs were in the sibling repo**, nearly buried. **FIXED:** `_resolve_reference` now also resolves against explicitly-passed `--sibling-roots` (exact + basename, tagged `exact_sibling`/`basename_sibling`); default empty so single-repo reviews are unchanged. When a close/model review spans repos, pass `--sibling-roots ~/Projects/phenome` (repeatable). Until then, treat HALLUCINATED on a cross-repo packet as "verify manually against the sibling," not "discard."
- **[2026-06-09] Code-symbol citations inflated HALLUCINATED — 3rd anchor-inflation class.** Findings citing a SYMBOL as if it were a file (`GenomeObserver.observe()`, `_VcfRecord`, `parse_variant_key()`) miss every file-resolution branch and got marked HALLUCINATED. A genomics close hit ~38% "hallucinated" that was really ~10% (the rest real findings citing real symbols). **FIXED:** `_resolve_reference`, before declaring `missing`, detects a code-symbol reference (dotted identifier, optional `()`, non-source suffix) and greps `def`/`class <leaf>` across `*.py/*.ts/*.tsx/*.js` under project + sibling roots; a definition hit returns `symbol_def`, treated as anchor-confirmed (the def existing IS the grounding; a symbol's "line" is meaningless). Until fully trusted, treat HALLUCINATED on a method/class/function citation as "grep for the def," not "discard."
- **[2026-06-10] PLAN reviews need ≥1 repo-access axis — packet-only reviewers critique the design; tool-having reviewers falsify the premises.** Evo behavior-tables plan: 3 packet-only axes (Gemini 3.5 Flash, GPT-5.5, Opus 4.8) produced solid design-level corrections — and all 3 missed that the plan's Phase-3 conversion target had ZERO production dispatch sites (dead parallel implementation), that a cited scenario-ID join didn't exist in the doc, and that the proposed compression already existed as a helper. The Fable SUBAGENT axis (repo tools, grepped dispatch sites) found all three, verdict REJECT; every claim verified. Rule: when reviewing a PLAN (not a diff — diffs carry their own ground truth), dispatch at least one axis with repo access (fable-subagent pattern, or any Agent-tool reviewer with Read/Grep), and tell it to verify the plan's premises (do the named functions have callers? do the cited join keys exist on BOTH sides?) before critiquing the design. Packets can never disprove "the code this plan converts is alive." *Second confirmation (2026-06-10, emb elevation plan): 24 packet-only findings (Gemini 3.5 Flash + GPT-5.5) missed both falsifiable premises — a "live caller" that was behind a never-passed flag (dormant LateChunker) and an overfetch hack justified by a stale comment (emb filters pre-ranking); the Fable repo-axis caught both plus a dead integration target (intel relevant_methods.py, zero invocations). Two-for-two on the same day.*
- **[2026-06-15] Repo-scale audit plans — lanes before packet-only critics; verify before trust.** Genomics lingering-bugs: orchestrator + 8 parallel lanes found load-bearing seams (`execution_plan` ≠ `freshness_verdict`, wrapper finalize) that packet-only 4-axis missed or drowned in noise (76 findings). Rule: `/critique audit-plan` requires repo-premise evidence before lean critics — parallel readonly lanes on first pass (or fresh lane manifest from same session), lane-partition completeness check, mechanical merge with lane-count manifest, then verify decision-dependent claims, then 2 orthogonal critics (sequencing + premise-soundness). Invariant: **no packet-only critic judges a repo-scale plan whose premises are unverified.** Parallel lanes are mandatory on first audit pass because orchestrator context omits module clusters — not replaceable by `build_plan_close_context.py` on unknown scope. llmx Claude: `llmx chat --subscription -m claude-opus-4-8` (API key in env without `--subscription` → "Credit balance too low"); critics run in background — orchestrator inspects task output and kills manually; no skill-prescribed `--timeout`. Commit convergence to `docs/audit/`; `.model-review/` stays gitignored.
- **[2026-07-06] FIXED — below-floor `budget_seconds` is now a triage hard error.** `review_gate
  triage` refuses (exit 2, no dispatch.json) any budget below the largest resolved axis-profile
  timeout of the selected axes (600s for `standard`), instead of letting model-review skip every
  axis as `budget_insufficient_for_profile` at dispatch (silent no-op; recurrence of the 2026-06-18
  class, caught in the 2026-07-06 skill-value audit). Floor is computed from model-review's own
  axis→profile tables (`review_gate.axis_budget_floor`); covered by `test_review_gate.py`.
- **[2026-07-09] FIXED — deterministic review triage hung inside configured external diff.**
  `review_gate.py triage` calls the shared Python `run_git`, so it bypassed the interactive shell hook
  that injects `--no-ext-diff`; on a dirty `uv.lock`, `difft` ran for minutes and the gate emitted no
  manifest or error. `shared.git_context.run_git` now injects `--no-ext-diff` for every `git diff`
  subprocess, with a regression test that asserts the exact command. Machine-consumed Git output must
  not depend on an interactive external renderer.
- **[2026-07-09] FIXED — repo-grounded Grok xhigh was guaranteed to time out on deep plan packets.**
  Two parallel arc-agi plan reviews completed all four standard axes but produced empty Grok outputs
  at exactly 600s. The profile slug was `grok-4.5-xhigh`, but its timeout remained 600s and the dispatch
  executor itself waited only 720s. `grok_review` now gets 1200s and the executor wait is 1230s; tests
  assert both timeout contracts so the axis cannot silently regress below its own xhigh budget.
- **[2026-07-10] FIXED — Opus Max review was killed at the profile boundary, then the
  executor encoded the same ceiling independently.** A healthy subscription probe completed, but a
  consequential genomics architecture review hit the `claude_review` 600s timeout and left a zero-byte
  artifact. That artifact is transport failure, never reviewer evidence. `claude_review` now has a
  finite 3600s bound at explicit `max` effort, matching llmx's canonical Max floor. The parallel
  executor derives its collection wait from the longest selected profile plus propagation grace.
  Tests cover the exact Opus effort/timeout
  profile and mixed Grok/Opus headroom.
- **[2026-07-13] FIXED — the repo-grounded Grok axis survived after Cursor removed the
  model.** Two `arc-agi` architecture reviews requested `grok-4.5-xhigh`; `cursor-agent`
  rejected the slug immediately and printed a live registry containing no Grok model. This was
  a capability-registry failure, not evidence from a reviewer, and it contradicted the standing
  cursor-agent contract that only Composer is supported. The `grok` axis/profile/model aliases and
  foreign-model workspace dispatcher were deleted. `--axes ...,grok` now fails before dispatch
  with the dated transport reason; the existing Composer premise scout remains the repo-grounded
  falsifier. Re-enable only after a registry check, exact named-model smoke, and repo-access test.
- **[2026-07-14] SUPERSEDES the 2026-07-13 Grok disable — Cursor restored Grok 4.5
  under new exact slugs.** Live `cursor-agent models` exposes
  `cursor-grok-4.5-{low,medium,high}` and matching `-fast` variants; there is no xhigh slug.
  A named `cursor-grok-4.5-high` ask-mode smoke and an exact repo-HEAD canary both passed;
  the expected HEAD is withheld from the prompt so a compliant echo cannot fake repo access.
  The opt-in `grok` axis is restored only through the read-only workspace dispatcher and now
  enforces exact registry plus the unrevealed repo canary before dispatch. The July-13 entry
  remains the evidence for why registry and serve checks are mandatory rather than inferred from
  old aliases.
- **[2026-07-14] FIXED — subscription review profiles inherited API-only output controls.**
  Moving `gpt_general` and `mechanical_review` to the Codex CLI subscription transport left their
  old `max_tokens` defaults in place, so `/critique` correctness/contracts failed before sampling.
  Removing that field exposed the same latent mismatch in extraction: the subscription path also
  cannot enforce JSON Schema. Subscription extraction now uses a strict JSON-only prompt and local
  parsing, while an all-profile invariant test rejects future subscription defaults that request
  `max_tokens` or search. The llmx fail-safe against silent metered fallback remains unchanged.
- **[2026-09-05] Documentation routing consolidated; historical defaults are not live authority.**
  The former root and adversarial lens disagreed on presets, model versions, Fable transport,
  and diff ownership. Active dispatch now points to the script's `AXES`/`PRESETS` and shared
  profiles; superseded guidance is preserved in [history.md](history.md). Diffs use code-review
  only. Initial closeout design review uses `triage --mode model`; `--mode close` is the later
  readiness gate because it requires `verified-disposition.md` already to exist. This documents
  the existing gate contract rather than routing a blocked manifest into the model.

- **[2026-09-05] Manifest validation crashed when --manifest used a relative path, including diagnostic output for external files. The CLI now resolves paths and renders external locations safely; subprocess regressions cover success and invalid JSON.**

- **[2026-09-16] GPT axes reported empty_output with codex exit 1 and a banner-only error: that was a ChatGPT subscription usage limit hidden by llmx keeping the head of codex stderr. Fixed in llmx@9a3deae (ERROR lines surface; plan limits exit 6 as quota). If a GPT axis fails in seconds, run one tiny llmx call and read the exit code before re-dispatching.**

- **[2026-09-30] FIXED — close triage treated literal fenced evidence as missing local files.**
  The tox feasibility packet was blocked by a CLI placeholder, a truncated quoted
  link, remote Volume paths and runtime `SUCCESS.json` literals. The dead-reference
  scanner now excludes fenced blocks while retaining blocking checks for prose
  references and Markdown links outside them. It also preserves absolute and
  parent-relative paths instead of stripping their leading path characters.
  Regressions reproduce both failures and retain a genuinely missing-file control.
  This check establishes local reference existence, not semantic validity of quoted
  code or examples; those remain part of native review.

- **[2026-10-07] RETIRED — Composer 2.5 premise scout and `composer` axis.** Operator: Composer
  2.5 is outdated; successor GPT-6 Astra at low effort (codex-cli subscription), with GPT-6 Sol at
  high effort as the plan-limit fallback. The premise scout now runs `codex exec -s read-only -C
  <project>` and records `served_model`, effort, token usage and attempts in `voi-scout.json`;
  the `composer` axis refuses with a pointer, and `review_gate` blocks a manifest that names it.
  Earlier entries that call the Composer scout the repo-grounded falsifier describe the lane as it
  was.
- **[2026-10-11] Invalid Gemini key passed preflight.** `--preflight` probed only the Claude
  subscription, so an `API_KEY_INVALID` Gemini key failed the arch and gaps axes mid-critique.
  Preflight now makes one bounded live Gemini call whenever the requested axes include a Gemini axis
  or name none (`run_gemini_preflight`); a persistent rate limit (llmx exit 3) is reported as
  degraded, not failed, because the arch axis falls back to GPT. Regression:
  `GeminiPreflightTest` in `scripts/test_model_review.py`.

- **[2026-10-14] 2026-10-14 genomics post-ship plan: packet-only axes (gemini-flash x2, astra x2, opus) plus a low-effort scout missed 15 code-level findings (3 blockers) that a repo-grounded codex exec -s read-only gpt-6.1-sol high review then found, all verified at source (~10 min, 5.3M input tokens mostly cached); for plans whose premises are live callers, add a repo-grounded Sol reviewer before adjudication**

- **[2026-10-14] Pre-existing failure, seen 2026-10-14: critique/scripts/test_build_plan_close_context.py::test_manifest_includes_review_targets fails on HEAD as well (checked in a clean worktree), so it is not caused by the Argon/Opus preset change. Not yet diagnosed.**

- **[2026-10-14] 2026-10-14 immigration-research: the documented 'uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py' run from the reviewed repo made uv remove and rebuild that repo's .venv (CPython 3.13.15, 35 locked packages). Docs and review_gate's suggested command now use 'uv run --no-project'; regression scripts/test_skill_commands.py.**

- **[2026-10-14] Manual repo-access review via `codex exec` from a run_in_background Bash hangs at "Reading additional input from stdin..." (0 CPU, no session file) when stdin is left open; pass `< /dev/null` or give the prompt on stdin as model-review.py's scout does (pitchtest 2026-10-14, lv20 route review).**

- **[2026-10-14] 4th anchor-inflation class: verify_claims marked claims HALLUCINATED ("<file> not found") for files that exist. Five rows in two immigration-research reviews; over 161 saved reviews (5,460 claims) the fix moves HALLUCINATED 1,302 → 1,104 and adds none. Causes: (1) an "ambiguous" resolution carries found_path=None and the missing branch tested that first (builder.py: 24 files, RESULT.md: 254); (2) the review's own packet file sits under the excluded .model-review/ (premise-scout.md); (3) the ref regex had no end boundary, so model.json read as model.js, x.cljc as x.clj, outside.tsv as outside.ts, square.shift as square.sh. FIXED: ambiguous is tested first, the packet's source_paths resolve before "missing", an extension must end the name (tsx, cljs added); regression VerifyClaimsExistingFileTest.**

- **[2026-10-14] Finding-key drift: CLI extraction cannot enforce FINDING_SCHEMA, and from 2026-07 most findings said file_path/proposed_fix, which every findings.json reader ignored (disposition "File: N/A", no structured ref for verify, review_gate and integration_audit matching an empty file/fix). FIXED: the extraction prompt names the schema keys; shared/finding_keys.py maps the aliases for every reader (integration_audit.load_findings serves review_gate and outcome_link); any other off-schema key is printed and recorded in coverage.json extraction.key_drift and the disposition header. Reading the field exposed false HALLUCINATED classes, also fixed: module names (<name>.py), URLs/placeholders/globs, paths only the reviewed context or the fix names, "<repo>/path" next to the project, absolute paths inside it, files only in cache/worktree copies; an anchor read off the cited path no longer confirms (118 rows). 161-review probe: HALLUCINATED 1,104 → 211 (735 rows now named in the reviewed context; 550 of their 813 names are tracked files deleted or moved since); 5 new, all names absent from disk. Regression FindingKeyDriftTest, VerifyStructuredAnchorTest.**

- **[2026-10-14] verify_claims walked the whole tree once per reference (Path.rglob) and re-read every source file once per code symbol: 529 s for one 66-reference genomics review, whose tree holds 494k entries, mostly in .claude/worktrees, .claude/cache and .uv-cache. FIXED: _TreeIndex answers rglob for literal patterns from one walk that skips cruft dirs (the cruft dirs are walked once, only when a reference is otherwise missing); def/class names are indexed once; .uv-cache joins the cruft dirs (its dependency copies made genome-sync files ambiguous and ext-swapped candidates.txt to pip's candidates.py). The same review takes 28.5 s cold, 9 s warm; all 161 saved reviews 164 s. Rows match per-reference rglob on 5,460/5,460 claims; the .uv-cache change moves 4. Regression TreeIndexParityTest.**

- **[2026-10-14] 2026-10-14: model-review Gemini axes (arch, gaps) failed 'API key missing for google' in a session whose shell predates the dotfiles secret-env-policy change mapping GEMINI_API_KEY_CRITIQUE_ONLY -> GEMINI_API_KEY_METERED; llmx reads only GEMINI_API_KEY[_METERED] or the Keychain. Workaround: GEMINI_API_KEY_METERED="$GEMINI_API_KEY_CRITIQUE_ONLY" on the dispatch, or start a new shell. Permanent fix: rename the store entry (policy comment).**

- **[2026-10-15] 2026-10-15 recurrence (immigration-research, session 75b08f57): same shell predating the secret-env policy; Argon axes of two packets failed at launch while Opus ran on. The 2026-10-14 workaround held (export GEMINI_API_KEY_METERED from GEMINI_API_KEY_CRITIQUE_ONLY on the dispatch); the permanent store rename is still open.**

- **[2026-10-15] 2026-10-15: Claude CLI stream cut → CLI injects a resume turn → llmx refuses ('forced to continue after answering'); the complete answer sits in ~/.cache/llmx/refused-claude-streams/<id>.json 'result'. If it holds every section from the start, salvage it verbatim with a note instead of re-running (r6 WB, U1).**

- **[2026-10-16] FIXED — preflight blocked a Gemini/Astra panel on unused Claude quota.**
  The subscription probe was hardcoded to Claude even when no Claude axis was requested.
  `--preflight-subscription-model gpt-6-astra` now probes the actual GPT route; Gemini's
  live check remains active. The default remains Claude for existing callers. A failed
  selected-model probe still blocks. Regression: `PreflightTest` and
  `ModelReviewMainTest` in `scripts/test_model_review.py`. Evidence: SIPP work-response
  review, Claude quota exhausted while the requested Astra and Gemini routes were available.

## 2026-10-18: explicit Claude API authorization was unreachable

The Claude review axis fixed the subscription profile and exposed no billing-route
opt-in, so exhausted monthly CLI allowance blocked an explicitly authorized API review.
`--claude-api` now selects one registered direct-Anthropic API profile for that axis only;
the original subscription profile is unchanged and failures never trigger billing fallback.
Offline controls cover absent flag, mixed axes, quota failure, direct dry-run validation,
wrong-route refusal and incompatible entitlement-probe selection. Preflight keeps the GPT
subscription probe but does not make a paid Claude call. Evidence: genomics
`.claude/cache/handoff-1015/p35-review-transport-repair-r1/` retains authentic old-source
RED, exact patch and native focused controls. A dry route is not API entitlement proof.

Review correction: `dispatch_config_auth` describes helper configuration only, even on
dependency/bootstrap failure before any transport. Missing metadata remains null; no
observed-auth claim is made. Offline regressions retain failure status and exercise both
bootstrap metadata and absent metadata through the review result/receipt boundary.

## 2026-10-18: empty artifacts hid structured dispatch failures

The first genomics P3.5 two-axis review retained helper status/error_type `rate_limit`
and `Native Claude transport unavailable`, but its execution receipt said `empty_output`
and its failure collection said `nonzero_exit`. The review adapter had dropped the
helper cause/retryability, and later reporting replaced the reason based on output size.
The adapter, axis result, failure collection and execution receipt now preserve structured
status, error type/message, retryability and error/metadata locators. Existing fallback
paths retain the initial result snapshot as well as the final result; their triggers and
call limits are unchanged. Zero-exit empty output remains `empty_output`; budget/thread
skip reasons and usable parse-error output retain their distinct behavior. Missing helper
evidence stays unknown. Neither error text nor configured auth proves HTTP 429, served
authentication, or transport capability. Regression: `StructuredDispatchFailureTest`;
original partial/native2 evidence remains under genomics `.model-review/` and the repair's
offline RED/GREEN custody is in `.claude/cache/handoff-1015/p35-review-failure-reason-repair-r1/`.

Parent source correction: the helper overwrites its metadata/error paths on fallback and
removes the final error file after success, so initial locators cannot point to those mutable
files. Before either existing fallback, exact initial output (when present), metadata and error
bytes are now copied to distinct `.initial` locators with exclusive creation and fsync. An
existing retained destination refuses before the fallback; no historical bytes are overwritten.
Controls use the real shared helper artifact lifecycle for both fallback success and failure.
- 2026-10-20: Gemini 429 RESOURCE_EXHAUSTED "exceeded its monthly spending cap ... https://ai.studio/spend" was classified as a transient rate limit everywhere, and /critique fell back from gemini-4-argon to gpt-6-astra labelled only `gemini_rate_limit`. Fix: spend-cap markers ("spending cap", "spend cap", "ai.studio/spend", "spend limit") win over rate-limit markers as quota/QuotaError in llmx `providers.py`, `cli_backends._QUOTA_MARKERS`, `dispatch_api.classify_dispatch_error`, and skills `shared/llm_dispatch.classify_error`; model-review keeps the fallback but sets `fallback_reason="gemini_spend_cap"` and prints `[DEGRADED]`. Tests: llmx `test_gemini_spend_cap_is_quota_not_rate_limit`, `test_gemini_spend_cap_classifies_as_quota`; skills `ClassifyErrorSpendCapTest`, `test_dispatch_falls_back_after_gemini_spend_cap_degraded`.

- **[2026-10-22] 2026-10-22 genomics: model-review GPT axes failed "GPT API billing/quota failure" then fell back to exhausted codex subscription, while `llmx chat -p openai --auth api -m gpt-6-astra` with the same key succeeded (3 calls). Also no CLI flag routes GPT axes to the metered API (only --claude-api); add --gpt-api and find why the script API path reports billing failure. Receipts: .model-review/2026-10-22-codebase-reduction-rev2-subpart-*/dispatch-failures.json**
