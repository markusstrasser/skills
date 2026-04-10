# Verified Disposition — 2026-04-10

**Claims:** 13 total — 6 CONFIRMED, 0 HALLUCINATED, 7 UNVERIFIABLE


| # | Verdict | Claim | Notes |
|---|---------|-------|-------|
| 1 | CONFIRMED | **[CRITICAL]** BSD `mktemp` template in `generate-overview.sh` will fail on macO... | generate-overview.sh exists |
| 2 | CONFIRMED | **[CRITICAL]** BSD `mktemp` templates in `run-cycle.sh` are incompatible with ma... | run-cycle.sh exists |
| 3 | CONFIRMED | **[CRITICAL]** Double-wait logic in generate-overview.sh --auto causes spurious ... | generate-overview.sh exists |
| 4 | UNVERIFIABLE | **[HIGH]** llmx guard applies chat-only validation to non-chat subcommands | no file references |
| 5 | UNVERIFIABLE | **[HIGH]** Rate-limited research cycle routing allows invalid phase selection | no file references |
| 6 | UNVERIFIABLE | **[HIGH]** Missing workflow-level regression tests for hooks and cycle routing | no file references |
| 7 | CONFIRMED | **[HIGH]** `model-review.py` bypasses the shared dispatch abstraction | model-review.py exists |
| 8 | UNVERIFIABLE | **[HIGH]** `shared.llm_dispatch.dispatch()` lacks centralized schema normalizati... | no file references |
| 9 | UNVERIFIABLE | **[MEDIUM]** Duplicated model-to-profile mapping creates migration drift risk | no file references |
| 10 | CONFIRMED | **[MEDIUM]** Provider-specific schema mutation is duplicated in `model-review.py... | model-review.py exists |
| 11 | UNVERIFIABLE | **[MEDIUM]** Shared dispatch layer lacks a parallel or bulk invocation API | no file references |
| 12 | CONFIRMED | **[LOW]** `run-cycle.sh` mixes prompt text into a temporary context file instead... | run-cycle.sh exists |
| 13 | UNVERIFIABLE | **[LOW]** Inconsistency between guard implementation and documented manual debug... | no file references |

