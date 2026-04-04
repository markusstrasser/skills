<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Error Handling (v0.6.0+)

## Exit Codes

Branch on these, don't parse stderr:

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | — |
| 1 | General error | Read stderr for details |
| 2 | API key missing/invalid | Check env vars |
| 3 | Rate limit (429/503, transient) | Wait, or add `--stream` (API transport has separate capacity from CLI) |
| 4 | Timeout | Increase `--timeout`, or add `--stream` for API transport |
| 5 | Model error (context too large, bad params) | Fix request |
| 6 | **Quota/billing exhausted** (permanent) | Top up billing. NOT transient — retries won't help |

## Structured Diagnostics (stderr, JSON)

```json
{"error": "rate_limit", "provider": "google", "model": "gemini-3.1-pro-preview", "exit_code": 3, "action": "wait or use --stream (API transport)"}
```

## Additional stderr Signals

- Transport switch: `[llmx:TRANSPORT] gemini-cli → google-api (max_tokens not supported by CLI)`
- Truncation warning: `[llmx:WARN] output may be truncated`
- Model suggestion: `"gemini-3.1-pro not found; did you mean gemini-3.1-pro-preview?"`

## `--fallback MODEL`

Exists but **not recommended**. Silent model switching masks failures. If you asked for Pro, you should get Pro or an error. If CLI rate-limited, use `--stream` (forces API transport) rather than `--fallback` (switches to a weaker model).

## Python Error Handling Pattern

```python
result = subprocess.run(
    ['llmx', '-m', 'gemini-3.1-pro-preview', '--timeout', '300'],
    input=prompt, capture_output=True, text=True, timeout=360
)
if result.returncode == 3:  # rate limit — API transport has separate capacity
    print(f"Rate limited: {result.stderr}")
elif result.returncode == 4:  # timeout
    print(f"Timeout: {result.stderr}")
```
