---
name: oura-ring
description: "Use when: Oura Ring API pull, sleep/HRV/readiness dashboards, wearable→NeuroKit2. NOT generic biosignal code without Oura (/neurokit2)."
---

# Oura Ring API (v2)

```bash
uv pip install oura-ring   # v1.0.1, MIT, Python >=3.12
```

**Get token**: https://cloud.ouraring.com/personal-access-tokens

> **v1.x breaking changes vs 0.3.x** (this skill is verified against `oura-ring==1.0.1`):
> - Constructor is now `OuraClient(access_token=None, *, personal_access_token=None)` — a
>   personal access token MUST be passed by keyword: `OuraClient(personal_access_token=...)`.
>   The first positional arg is an OAuth2 access token.
> - Date params renamed: daily/sleep endpoints take `start_date=` / `end_date=`;
>   time-series endpoints (`get_heart_rate`, `get_ring_battery_level`) take
>   `start_datetime=` / `end_datetime=`. The old `start=` / `end=` now raise `TypeError`.
> - Python floor raised to **>=3.12**.
> - OAuth2 flow added via `OuraAuth(client_id, client_secret)`; `OuraClient` is a context manager (`close()` / `with`).

## Quick Start

```python
import os
from oura_ring import OuraClient

# Personal access token → keyword arg (positional is now OAuth2 access_token)
with OuraClient(personal_access_token=os.environ["OURA_PAT"]) as client:

    # Daily sleep score + contributors (deep, REM, latency, timing)
    sleeps = client.get_daily_sleep(start_date="2026-02-01", end_date="2026-02-18")

    # Heart rate (5-min samples) — note *_datetime params
    hr = client.get_heart_rate(start_datetime="2026-02-17", end_datetime="2026-02-18")

    # Readiness score + contributors — omit end_date for a single day
    readiness = client.get_daily_readiness(start_date="2026-02-01")

# All range methods return list[dict] → easy DataFrame conversion
import pandas as pd
df = pd.DataFrame(sleeps)
```

## Available Endpoints

Range methods share the signature `(start_date=None, end_date=None, document_id=None)` unless noted.
Time-series methods use `(start_datetime=None, end_datetime=None, latest=None)`.

| Method | Returns |
|--------|---------|
| `get_daily_sleep` | Sleep score, contributors (deep, REM, latency, timing) |
| `get_sleep_periods` | Detailed sleep stages (awake/light/deep/REM per period) |
| `get_sleep_time` | Recommended/optimal bedtime windows |
| `get_daily_activity` | Steps, calories, movement, inactivity alerts |
| `get_daily_readiness` | Score, HRV balance, body temperature, recovery |
| `get_daily_resilience` | Resilience level + contributors |
| `get_daily_stress` | Stress score, high/low periods |
| `get_daily_spo2` | Blood oxygen average |
| `get_daily_cardiovascular_age` | Estimated cardiovascular age |
| `get_vo2_max` | VO₂ max estimate |
| `get_heart_rate` *(datetime)* | 5-min HR samples (bpm + source) |
| `get_ring_battery_level` *(datetime)* | Ring battery time-series |
| `get_sessions` | Meditation/breathing sessions |
| `get_workouts` | Activity type, duration, calories, HR |
| `get_rest_mode_period` | Rest-mode windows |
| `get_tags` / `get_enhanced_tag` | User tags / enhanced tags |
| `get_ring_configuration` | Ring hardware/config (`document_id` only) |
| `get_personal_info()` | Age, weight, height, biological sex |

OAuth2 scopes (`oura_ring.SCOPES`): `email, personal, daily, heartrate, workout, tag, session, spo2Daily, stress, heart_health, ring_configuration`.

## HRV Analysis with NeuroKit2

```python
import neurokit2 as nk
import numpy as np

# Detailed sleep stages (per-period)
sleep_periods = client.get_sleep_periods(start_date="2026-02-17")

# Extract R-R intervals from sleep period (if available via export)
# Oura CSV exports have rr_intervals column
rr_intervals = np.array([...])  # ms, from Oura CSV export

# NeuroKit2 HRV analysis
hrv = nk.hrv(rr_intervals, sampling_rate=None, show=False)
# Returns 50+ metrics: SDNN, RMSSD, pNN50, LF/HF ratio, SD1/SD2...
```

## Oura CSV Export (richer than API)

Oura app → Settings → Export Data → CSV files include:
- `sleep.csv` — per-night: total, deep, REM, light, awake, latency, efficiency
- `readiness.csv` — daily readiness + contributors
- `activity.csv` — steps, calories, active time
- `heart_rate.csv` — 5-min samples
- `oura_sleep_rr_intervals.csv` — **raw R-R intervals** (not available via API!)

**R-R intervals are the gold standard for HRV analysis** — use CSV export for NeuroKit2.

Existing CSV exports: `data/wearables/`

## Correlation Analysis Pattern

```python
import pandas as pd

# Load Oura + supplement log
sleep_df = pd.DataFrame(client.get_daily_sleep(start_date="2026-01-01"))
# Merge with supplement tracking data on date
# Look for: HRV delta, deep sleep %, sleep efficiency changes
```

## Rate Limits

- **5,000 requests/day** per personal access token
- No per-second limit documented, but be reasonable
- Pagination: responses include `next_token` for large date ranges
