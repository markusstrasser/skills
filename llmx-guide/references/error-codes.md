<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Error Handling (v0.6.0+)

## Exit Codes

Branch on these, don't parse stderr:

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | — |
| 1 | General error | Read stderr for details |
| 2 | API key missing/invalid | Check env vars |
| 3 | Rate limit / service-unavailable (429/503/overload, transient) | **llmx now AUTO-RETRIES these** (backoff+jitter, `LLMX_MAX_RETRIES` default 4; llmx@0e24d5c) — exit 3 means retries were already EXHAUSTED. Don't add your own retry loop; raise `LLMX_MAX_RETRIES` or wait. |
| 4 | Timeout | Set `--timeout` explicitly (1800-3600 for xhigh; default 300s, auto-scaled to 600/1200 for high/xhigh as a net; ceiling 3600s), or add `--stream` |
| 5 | Model error (context too large, bad params) | Fix request |
| 6 | **Quota/billing exhausted** (permanent) | Top up billing. NOT transient — retries won't help |

## Structured Diagnostics (stderr, JSON)

```json
{"error": "rate_limit", "provider": "google", "model": "gemini-3.5-flash", "exit_code": 3, "action": "wait or use --stream (API transport)"}
```

## Additional stderr Signals

- **Auto-retry: `[llmx:RETRY] google/<model> service_unavailable (attempt 2/4) — sleeping 4.5s`** — a transient 429/503/overload was caught and is being retried (backoff+jitter). Informational; the call has NOT failed. Only if all attempts exhaust do you get exit 3.
- Transport switch: `[llmx:TRANSPORT] codex-cli → openai-api (--search not supported by CLI)` (Gemini has no CLI since 2026-05-31; switches now only affect Codex CLI)
- Truncation warning: `[llmx:WARN] output may be truncated`
- Model suggestion: `"gemini-3.5-flsh not found; did you mean gemini-3.5-flash?"`

## `--fallback MODEL`

Exists but **not recommended**. Silent model switching masks failures. If you asked for Pro, you should get Pro or an error. If CLI rate-limited, use `--stream` (forces API transport) rather than `--fallback` (switches to a weaker model).

## Session-Level Fallback Rules

- **Gemini 503/rate-limit:** llmx now auto-retries (backoff+jitter) BEFORE surfacing exit 3, so a surfaced 503 already exhausted `LLMX_MAX_RETRIES` attempts — a *manual* retry of the same model is still pointless. If exit 3 persists across calls (sustained outage, not a blip), switch to GPT/Flash for the rest of the session or raise `LLMX_MAX_RETRIES`. (Pre-auto-retry, this rule was "switch after the FIRST 503" — 4 incidents of 4-6 wasted manual retries; auto-retry absorbs the blips now.)
- Exit 6 (billing) is permanent — never retry; exit 3 is transient (and auto-retried).

## Cost / Usage Diagnostics

- Every API-transport call appends one record to `~/.claude/llmx-usage.jsonl` (model, effort, prompt/completion/reasoning/cached tokens, latency, caller). CLI-transport calls have null tokens. Use `jq` for ad-hoc cost rollups. Override path with `LLMX_USAGE_LOG=`.
- llmx is editable-installed (`uv tool install --editable`) — source changes in `~/Projects/llmx/` propagate to the `llmx` command instantly, no reinstall.

## Python Error Handling Pattern

```python
result = subprocess.run(
    ['llmx', '-m', 'gemini-3.5-flash', '--timeout', '300'],
    input=prompt, capture_output=True, text=True, timeout=360
)
if result.returncode == 3:  # rate limit — API transport has separate capacity
    print(f"Rate limited: {result.stderr}")
elif result.returncode == 4:  # timeout
    print(f"Timeout: {result.stderr}")
```
