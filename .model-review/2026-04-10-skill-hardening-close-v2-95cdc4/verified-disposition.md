# Verified Disposition — 2026-04-10

**Claims:** 11 total — 1 CONFIRMED, 0 HALLUCINATED, 10 UNVERIFIABLE


| # | Verdict | Claim | Notes |
|---|---------|-------|-------|
| 1 | CONFIRMED | **[CRITICAL]** `--extract` is documented but rejected by `model-review.py` | model-review.py exists |
| 2 | UNVERIFIABLE | **[HIGH]** Path instability in selective manifest linting mode | no file references |
| 3 | UNVERIFIABLE | **[HIGH]** Validator crash on malformed uses.* entries | no file references |
| 4 | UNVERIFIABLE | **[MEDIUM]** Custom questions JSON is read without error handling | no file references |
| 5 | UNVERIFIABLE | **[MEDIUM]** Review artifacts anchored to process CWD instead of project directo... | no file references |
| 6 | UNVERIFIABLE | **[MEDIUM]** Manifest validator ignores `requires_packet` and `requires_gpt` mod... | no file references |
| 7 | UNVERIFIABLE | **[MEDIUM]** CLI tests omit the documented `--extract` path | no file references |
| 8 | UNVERIFIABLE | **[MEDIUM]** Brainstorm schema registry underspecifies documented artifact contr... | no file references |
| 9 | UNVERIFIABLE | **[LOW]** JSONL output escapes Unicode despite using UTF-8 file handles | no file references |
| 10 | UNVERIFIABLE | **[LOW]** Contradictory fallback policy in review documentation | no file references |
| 11 | UNVERIFIABLE | **[LOW]** Prompt documentation embeds Bash subshells that may leak literal contr... | no file references |

