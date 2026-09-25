# Transport — verified lanes and llmx facts

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L31-46, L104-117, L146-161.

## Verified Transport — configuration and execution evidence

| Lane | Verified state | Practical limit |
|---|---|---|
| Codex / `llmx chat --subscription -m gpt-6-astra` | Global model is Astra; llmx accepts the canonical ID and effort | Configuration and offline checks do not prove a new live request or workload result. |
| `llmx chat --subscription -m claude-fable-5-1` | 2026-09-05 dry-run: `claude-cli`, subscription auth, exact 5.1 ID and requested effort | No live headless 5.1 canary in this check. Subscription never permits silent API fallback. |
| Interactive Claude Code | Committed global setting `claude-fable-5-1[1m]`; on 2026-09-22 the working `settings.json` drops that pin (uncommitted) and this session ran `claude-opus-5-5[1m]` on CLI 2.1.280 | Existing September 2 local billing evidence is recorded in agent-infra’s Fable memo §10. Plan allowance and current remaining usage are separate. |
| Claude Agent-tool model pins | Opus pins recovered in the July 29 observations; Fable pins have no later verification here | Treat old failures as dated evidence. For model-sensitive evaluations inspect the provider run record; self-report alone is not independent proof. |
| `opus` alias (`claude -p --model opus`) | 2026-09-22 probe, CLI 2.1.280, key stripped: JSON `modelUsage` reports `claude-opus-5-5` | The alias moved from Opus 5 to 5.5 on release day for every alias-based lane (`opus-low`, `--model opus` scripts). The Agent-tool `model: opus` pin was not probed. Pin `claude-opus-5` where Opus 5 behavior is required. |
| `llmx chat --subscription -m claude-opus-5-5` | 2026-09-22 dry-run: `claude-cli`, subscription auth, exact ID, no warnings | Configuration only; no live llmx canary. The `lite_allowed_models` mirror does not list 5.5 yet. |
| Cursor Grok 4.7 | **Verified live 2026-09-23** with `cursor-agent` signed in: `cursor-agent models` lists 4.7 as `grok-4.7-{low,medium,high,xhigh}[-fast]` — no `cursor-` prefix; the 2026-09-22 guess `cursor-grok-4.7-*` does not exist. 4.6 keeps its `cursor-grok-4.6-*` prefix. [historical: Grok ≤4.6 retired 2026-09-25, Pareto-frontier prune] Critique pin corrected to `grok-4.7-high`. `-e` is ignored on cursor-cli. | The IDE subagent slug `grok-4.7-high-fast` seen 2026-09-22 was already the real CLI form, not a separate IDE-only id. |
| Grok Build CLI (`~/.grok/bin/grok`) | Updated 1.0.13 → **1.0.41** 2026-09-23; `grok models` now lists `grok-4.7` (default) and `grok-4.7-build-fast` alongside `grok-4.6`/`grok-4.5`. Live: `grok -p -m grok-4.7` replied; `grok-4.7-max` refused. | Every call carries ~26K tokens of CLI context. llmx default for `-p grok` is `grok-4.7`; 4.6 remains an explicit `-m`. [historical: retired 2026-09-25, Pareto-frontier prune] |

The [historical transport record](fable-routing-history.md) preserves
old routing failures and their later corrections. Validate the actual lane a
caller uses; an alias or successful dry-run establishes configuration only.

## Transport facts (llmx — not judgment)

**Read before dispatch:** `~/.claude/cache/llmx-routing.json` (regenerate: `llmx info --write-mirror`). Transport table, effort maps, exit classes live there — not in this skill.

**Claude policy:** NEVER `anthropic-direct`/API by default. Subscription only (`llmx chat --subscription`, `claude -p` with key stripped, Agent tool) unless the user explicitly requests metered API billing.

**Probe subscription path before critique batches:**

```bash
llmx chat --dry-run --subscription -m claude-opus-5 -e max
# or: uv run python3 ~/Projects/skills/critique/scripts/model-review.py --preflight
```

Mechanics and footguns: `/llmx-guide`.

- **`llmx vision` is multi-provider as of 2026-07-22 (llmx `2b12289`) — it used to be Gemini-only
  and off-ledger.** It now routes through the normal dispatch path, so `-m` takes any
  vision-capable model id (`gemini-3.6-flash` [historical: retired 2026-09-25, Pareto-frontier prune], `gpt-6-astra`, `gpt-6-luna`, `claude-opus-5`),
  provider is inferred, and `-e` effort works. Three consequences worth knowing:
  (1) it is **spend-guarded and policy-gated** like everything else — a Gemini vision call now
  needs `LLMX_GEMINI_OK=1`, where it previously dispatched freely;
  (2) it **writes real token counts to the usage ledger**, so vision cost no longer has to be
  estimated (evals/figure_vision_bakeoff had been substituting a `len(response)/4` proxy);
  (3) media **fails loud** rather than being dropped — video to an OpenAI-compat endpoint, an
  oversized inline upload, or any media sent through a CLI transport (claude-cli/codex/cursor)
  raises, because a model asked about a figure it never received invents an answer.
  Footgun retained for back-compat with the documented convention: in `llmx vision`, `-p` is the
  PROMPT, not `--provider` (use `--provider` to override the inferred one).
  **This unblocks a cross-family vision judge**, which the figure-vision eval previously could not
  have — its qualitative judge was Gemini-flash grading a Gemini-flash candidate, a same-family
  COI it documented as forced by the tool. Pass `--judge gpt-6-astra` there now.
