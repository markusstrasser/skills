# Observe scope and arguments

First positional is the mode; the rest are target + options. **Default mode:** `retro` if the
session is wrapping up ("retro", "retrospective") — otherwise `sessions`.

| Option | Applies to | Default |
|--------|-----------|---------|
| `--days N` | retrospective modes | 1 sessions/architecture · 3 harvest · 7 supervision/blindspot · 21 drift/failures |
| `--project P` · `--path DIR` | retrospective · code modes | all projects · repo root |
| `--quick` · `--thorough` · `--deferred` | architecture, audit, forensics | standard pipeline |
| `--force` | sessions, retro (defeats the idempotency stop) | off |
| `--headless` · `--wide-only` · `--multitask` | [analysis dispatch](analysis-dispatch.md) | harness-dependent |
| `--corrections` | sessions: mine user corrections, not anti-patterns | off |
| `--focus` | harvest: hooks·skills·scripts·architecture·rules·all | all |
| `--depth N` | conventions: git history depth | 40 |

**Scope for `maintain`:** default is **all active repos** (agent-infra intel genomics phenome hutter
substrate arc-agi). A repo arg narrows only which repo's rotation/fixes the tick acts on — the SWEEP
always covers every repo, because a red job anywhere is the priority.

## Routing rationale and provenance

One skill, four jobs: **look back** at what happened, **act** on what it found, **look forward** at
what never fails, **apply** the change to a codebase. Merged 2026-09-02 from `observe` + `improve` +
`leverage` + `upgrade` + `sweep` — five skills doing one job in five vocabularies. `/rsi close`
(the session-end ritual) stays separate.

**The structural blind spot, and the modes that cover it.** The retrospective modes learn from what
*failed*. They are blind to work that succeeds while far short of possible, to any axis nothing
measures, and to any tool never tried — you cannot retro your way to an unused capability. That is
what `lever`/`missing`/`generators` exist for: prospective, external, frontier-scanning. Reaching
for a retro when the real gap is an unframed axis is the most common mis-route into this skill.
