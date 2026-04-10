# Verified Disposition — 2026-04-10

**Claims:** 10 total — 4 CONFIRMED, 0 HALLUCINATED, 6 UNVERIFIABLE


| # | Verdict | Claim | Notes |
|---|---------|-------|-------|
| 1 | CONFIRMED | **[HIGH]** `pretool-llmx-guard.sh` can be bypassed with absolute or relative `ll... | pretool-llmx-guard.sh exists |
| 2 | UNVERIFIABLE | **[CRITICAL]** Shell scripts invoke a non-existent dispatcher path | no file references |
| 3 | CONFIRMED | **[HIGH]** Unsound and non-portable concurrency logic in generate-overview.sh | generate-overview.sh exists |
| 4 | UNVERIFIABLE | **[HIGH]** Shared dispatch environment instability via unpinned uv run | no file references |
| 5 | UNVERIFIABLE | **[MEDIUM]** Guard test does not validate the emitted command path | no file references |
| 6 | CONFIRMED | **[MEDIUM]** Silent failure in run-cycle.sh automation | run-cycle.sh exists |
| 7 | UNVERIFIABLE | **[MEDIUM]** Duplicated profile and model mapping in shell logic | no file references |
| 8 | UNVERIFIABLE | **[MEDIUM]** Gemini profile may send unsupported `reasoning_effort` parameter | no file references |
| 9 | UNVERIFIABLE | **[MEDIUM]** Dispatcher CLI may be missing the `--error-output` argument expecte... | no file references |
| 10 | CONFIRMED | **[LOW]** Fragile coupling to private shared helpers in model-review.py | model-review.py exists |

