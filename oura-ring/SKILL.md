---
name: oura-ring
description: "Use when: Oura Ring API pull, sleep/HRV/readiness dashboards, wearable→NeuroKit2. NOT generic biosignal code without Oura (/neurokit2)."
---

# Oura Ring API (v2)

```bash
uv pip install oura-ring   # v0.3.0, MIT, Python >=3.10
```

**Get token**: https://cloud.ouraring.com/personal-access-tokens

## Quick Start

```python
import os
from oura_ring import OuraClient

client = OuraClient(os.environ["OURA_PAT"])

# Sleep details (stages, HRV, HR, movement)
sleeps = client.get_daily_sleep(start="2026-02-01", end="2026-02-18")

# Heart rate (5-min intervals)
hr = client.get_heart_rate(start="2026-02-17", end="2026-02-18")

# Readiness score + contributors
readiness = client.get_daily_readiness(start="2026-02-01")

# All methods return list of dicts → easy DataFrame conversion
import pandas as pd
df = pd.DataFrame(sleeps)
```

## Available Endpoints

| Method | Returns |
|--------|---------|
| `get_daily_sleep(start, end)` | Score, contributors (deep, REM, latency, timing) |
| `get_daily_activity(start, end)` | Steps, calories, movement, inactivity alerts |
| `get_daily_readiness(start, end)` | Score, HRV balance, body temperature, recovery |
| `get_daily_stress(start, end)` | Stress score, high/low periods |
| `get_daily_spo2(start, end)` | Blood oxygen average |
| `get_heart_rate(start, end)` | 5-min HR samples (bpm + source) |
| `get_sleep_periods(start, end)` | Detailed sleep stages (awake/light/deep/REM per period) |
| `get_sessions(start, end)` | Meditation/breathing sessions |
| `get_workouts(start, end)` | Activity type, duration, calories, HR |
| `get_personal_info()` | Age, weight, height, biological sex |

All date params are `YYYY-MM-DD` strings. Omit `end` for single day.

## HRV Analysis with NeuroKit2

```python
import neurokit2 as nk
import numpy as np

# Get detailed sleep data with HRV
sleep_periods = client.get_sleep_periods(start="2026-02-17")

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
sleep_df = pd.DataFrame(client.get_daily_sleep(start="2026-01-01"))
# Merge with supplement tracking data on date
# Look for: HRV delta, deep sleep %, sleep efficiency changes
```

## Rate Limits

- **5,000 requests/day** per personal access token
- No per-second limit documented, but be reasonable
- Pagination: responses include `next_token` for large date ranges
