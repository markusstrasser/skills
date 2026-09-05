# Observe: harvest

Read [candidate lifecycle](candidate-lifecycle.md) for stream classification, dedup, ranking, promotion, and queue backpressure. Load only the source entries needed from [harvest sources](harvest-sources.md).

Cross-artifact harvester: read what the producers found, deduplicate, rank, surface what fell
through. **You consume artifacts. You do not produce analysis.**

**Two jobs: gather NEW, and drain the actionable OPEN queue.** Draining is real but small — the
bigger lever is keeping the streams separate *at entry* so the count stays honest. So the first move
every run is to classify the backlog by stream ([candidate lifecycle](candidate-lifecycle.md)), THEN drain the actionable residue.
Two classes to weight when they appear: **agent self-process anti-patterns** (re-guessing before
measuring, fix-spirals, `--no-verify` escape-hatching — they recur silently because no error fires;
`[obs]` unless there is a concrete guard to build) and **dead infra / generation without
consumption** (a generator with no consumer — genuinely `[ ]`: delete it or wire it).

**Before minting proposals/questions, enforce [queue backpressure](candidate-lifecycle.md#queue-backpressure).**

**Sources — live streams first**, then legacy artifact dirs behind an mtime guard (reordered
2026-07-05: the original producers went quiet April-June 2026 and the signal plane moved to the
deterministic miners). Read a source's entry in [harvest-sources.md](harvest-sources.md) before working it.

| # | Source | Note |
|---|--------|------|
| 2a | `.claude/blindspot-digest.md` (§2i) | highest-signal live source; top cluster → candidate detector (dedup vs existing hooks) |
| 2b | `~/.claude/reflect-quarantine/*.jsonl` (§2e) | pre-deduped FM-routed proposals; `just reflect-review`; promote for human disposition, **never auto-apply** |
| 2c | `just orphan-findings` (§2f) | **the canonical finding-routing protocol** other generators cite — never restate it. Only live, discrete, undone items, title verbatim; one `RECONCILIATION:` entry clears a fully-dispositioned memo |
| 2d | session-retro / design-review / session-analyst / suggest-skill dirs | mtime guard FIRST — skip any dir with nothing in-window |
| 2g | `artifacts/observe/*/failures/shell-env-candidate.jsonl` | auto-staged; high-priority infra, never `[obs]` |
| 2h | `just memory-harvest` | dedup against the suggested target FIRST; only generalizable ≥2-project lessons; cross-skill factoring is propose-only |
| 3a | `scripts/extract_user_tags.py --days N --tag f` | user `#f` feedback — highest signal, ground-truth corrections |
| 3b | git corrections | `log --since=CUTOFF --grep='Evidence:'`; `--oneline -- .claude/rules/ improvement-log.md`; skills `-- '*/SKILL.md' hooks/`. Three commits fixing hook edge cases signals weak hook testing |

Then dedup + classify (`hook`·`skill`·`script`·`architecture`·`rule`·`config`), apply `--focus`,
rank both streams, and write `artifacts/harvest/{DATE}-{SID}-harvest.md`: window, focus, **sources
scanned with denominators**, items found → after dedup → after focus, a summary table, and per-item
type · priority with its factors · status NEW|REINFORCED|VETOED-BUT-REVISIT · sources with paths and
quoted findings · proposed action · dedup notes.
