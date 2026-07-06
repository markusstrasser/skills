---
name: x-api
description: "Use when: monitoring curated X accounts, cashtags, finance tweet pulls. Paid API ($/post). NOT general search (/research)."
user-invocable: true
argument-hint: "[probe USERNAME | pull --config FILE]"
allowed-tools: [Read, Glob, Grep, Bash, Write]
effort: low
---

# X API v2 Client

Generic, project-agnostic interface to the X (Twitter) API v2 pay-per-use
developer tier. Built for daily-batch monitoring of a curated account list.

**Authentication:** Bearer token from `X_API_BEARER_TOKEN` env var. Caller is
responsible for loading the token (e.g., from `.env.local`, `~/.env`, or
launchd plist EnvironmentVariables).

## Subcommands

### `probe USERNAME [MAX_RESULTS] [START_TIME_ISO]`

Smoke-test auth, pull recent tweets from a single account, dump JSON to
`.scratch/x_probe_<username>.json`. Reports cost.

```
python3 ~/Projects/skills/x-api/scripts/probe.py aleabitoreddit 10
python3 ~/Projects/skills/x-api/scripts/probe.py aleabitoreddit 100 2026-04-01T00:00:00Z
```

### `pull --config FILE [--since-hours 24] [--max-pages 2] [--digest-out PATH] [--tracked-tickers-file PATH] [--themes-dir PATH]`

Read a JSON account-list, pull tweets since N hours ago, filter for cashtags
and material-claim keywords, emit a markdown digest with coverage delta.

Hard cap $100/month spend (refuses to run if MTD exceeds). Cost ledger is
wallet-scoped at `~/.local/state/x-api/cost_ledger.jsonl` (NOT CWD-scoped —
spend from every repo counts against the one monthly cap).

```
python3 ~/Projects/skills/x-api/scripts/pull.py \
    --config .claude/config/x_curated_accounts.json \
    --tracked-tickers-file <(ls analysis/entities/*.md | xargs -I {} basename {} .md) \
    --themes-dir analysis/themes \
    --digest-out .scratch/social_digest_$(date -u +%Y-%m-%d).md
```

## Library

`scripts/x_api.py` — `get_user`, `get_user_tweets`, `CostTally`, `log_cost`,
`month_to_date_usd`. Import from external scripts via:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Projects/skills/x-api/scripts"))
from x_api import CostTally, get_user, get_user_tweets, log_cost, month_to_date_usd
```

## Pricing reference (2026-05-01)

| Resource | Price | Note |
|---|---|---|
| Post read | $0.005 | Each tweet returned, not per request |
| User lookup | $0.010 | Per `/users/by/username` or `/users/:id` |
| Owned reads | $0.001 | Reads of the auth'd app's own data only |
| Monthly post-read cap | 2,000,000 | Hard limit at PPU tier |

See `~/Projects/intel/.scratch/x_api_features_research.md` for full feature map
(Lists endpoint, mentions endpoint, context_annotations).

## Architecture notes

- **Lists endpoint refactor deferred** until curated list grows past ~5
  accounts. `/2/lists/:id/tweets` cuts request count ~10x for the same
  per-post cost; not worth the refactor for 1-3 accounts.
- **Server-side cashtag extraction** is enabled via `tweet.fields=entities`.
  Each tweet's `entities.cashtags` field returns X's own ticker tagging,
  more accurate than text regex (skips `$` in money figures and quoted text).
- **Material-claim regex** is a starting heuristic. Replace with LLM
  classification (Haiku/Flash) once enough volume justifies the cost.

## What this skill does NOT do

- Posting tweets, DMs, or any write actions
- Real-time streaming (Filtered Stream — defer until >50 accounts)
- Account discovery (curated list management is caller's responsibility)
- LLM claim extraction (text classification belongs in caller, model choice
  varies per project)
- Auto-updates to track-record memory files (caller decides when to write)
