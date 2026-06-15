---
name: neurokit2
description: "Use when: ECG/PPG/HRV/EDA processing, biosignal pipelines, wearables analysis code. NOT Oura API auth/pull (/oura-ring)."
---

# NeuroKit2

```bash
uv pip install neurokit2
```

## Quick Start — HRV from R-R Intervals

Most relevant for Oura ring / wearable data (v0.2.13+):

```python
import neurokit2 as nk
import numpy as np

# From R-R intervals (ms) — typical wearable output
rr_intervals = np.array([800, 810, 790, 820, ...])  # ms

# Pass as dict with RRI + RRI_Time keys (correct API for raw intervals)
rr_time = np.cumsum(rr_intervals) / 1000  # timestamps in seconds
hrv_indices = nk.hrv({"RRI": rr_intervals, "RRI_Time": rr_time}, show=False)
# Returns DataFrame with 50+ metrics across all domains

# WARNING: Do NOT pass a raw array — it will be interpreted as peak sample
# indices, not intervals. Always use the {"RRI": ..., "RRI_Time": ...} dict.
```

## Signal Processing Pipelines

Each signal type follows: **clean → detect peaks → delineate → analyze**

```python
# ECG — full pipeline
signals, info = nk.ecg_process(ecg_signal, sampling_rate=1000)
hrv = nk.hrv(info['ECG_R_Peaks'], sampling_rate=1000)

# EDA (skin conductance)
signals, info = nk.eda_process(eda_signal, sampling_rate=100)

# Respiratory
signals, info = nk.rsp_process(rsp_signal, sampling_rate=100)
rrv = nk.rsp_rrv(signals, sampling_rate=100)

# EMG
signals, info = nk.emg_process(emg_signal, sampling_rate=1000)

# Multi-modal (all at once)
bio, info = nk.bio_process(ecg=ecg, rsp=rsp, eda=eda, sampling_rate=1000)
results = nk.bio_analyze(bio, sampling_rate=1000)
```

## HRV Domains

```python
hrv_time = nk.hrv_time(peaks)          # SDNN, RMSSD, pNN50, SDSD
hrv_freq = nk.hrv_frequency(peaks, sampling_rate=1000)  # ULF, VLF, LF, HF power
hrv_nonlinear = nk.hrv_nonlinear(peaks, sampling_rate=1000)  # Poincaré SD1/SD2, entropy
hrv_rsa = nk.hrv_rsa(peaks, rsp_signal, sampling_rate=1000)  # Respiratory sinus arrhythmia
```

## Complexity & Entropy

```python
# All complexity metrics at once
cx = nk.complexity(signal, sampling_rate=1000)

# Individual measures
nk.entropy_approximate(signal)
nk.entropy_sample(signal)
nk.entropy_permutation(signal)
nk.fractal_dfa(signal)           # Detrended fluctuation analysis
nk.fractal_higuchi(signal)
nk.complexity_lyapunov(signal, sampling_rate=1000)
```

## Key Behaviors

- **Auto analysis mode**: `*_analyze()` detects duration — <10s = event-related (epoch), ≥10s = interval-related (resting state)
- **Signal simulation**: `nk.ecg_simulate(duration=60, sampling_rate=1000)` for testing
- **Filtering**: `nk.signal_filter(signal, sampling_rate=1000, lowcut=0.5, highcut=40)`
- **Peak detection**: `nk.signal_findpeaks(signal)` — works on any signal type
- **Event-related**: `nk.events_find()` → `nk.epochs_create()` → `nk.ecg_eventrelated()`
