# Verified Disposition — 2026-04-10

**Claims:** 19 total — 2 CONFIRMED, 1 HALLUCINATED, 16 UNVERIFIABLE

**Hallucination rate:** 5%


| # | Verdict | Claim | Notes |
|---|---------|-------|-------|
| 1 | UNVERIFIABLE | **[HIGH]** Overview scripts estimate tokens with a naive `wc -c / 4` heuristic | no file references |
| 2 | CONFIRMED | **[HIGH]** `build_plan_close_context.py` relies on brittle `git status --short` ... | build_plan_close_context.py exists |
| 3 | UNVERIFIABLE | **[HIGH]** Phase 4 preserves bash orchestration instead of eliminating it | no file references |
| 4 | HALLUCINATED | **[HIGH]** God-module risk in context_selectors.py | context_selectors.py not found |
| 5 | UNVERIFIABLE | **[HIGH]** Deterministic hashing lacks normalization contract | no file references |
| 6 | UNVERIFIABLE | **[HIGH]** `ContextPacket` budget handling lacks model-aware tokenizer integrati... | no file references |
| 7 | UNVERIFIABLE | **[MEDIUM]** `overview.conf` parsing is duplicated in fragile bash code | no file references |
| 8 | UNVERIFIABLE | **[MEDIUM]** Python migration does not absorb atomic write and metadata injectio... | no file references |
| 9 | UNVERIFIABLE | **[MEDIUM]** Deterministic hashing strategy is unresolved with embedded generate... | no file references |
| 10 | UNVERIFIABLE | **[MEDIUM]** Incomplete overview migration allows continued drift | no file references |
| 11 | UNVERIFIABLE | **[MEDIUM]** Unification fails due to inconsistent budget metrics | no file references |
| 12 | UNVERIFIABLE | **[MEDIUM]** Model-review creates redundant context files | no file references |
| 13 | UNVERIFIABLE | **[MEDIUM]** Constitutional preamble should be a non-truncatable block type | no file references |
| 14 | UNVERIFIABLE | **[MEDIUM]** Migration plan lacks golden output-equivalence tests | no file references |
| 15 | UNVERIFIABLE | **[MEDIUM]** Repomix capture strategy does not address large stdout handling | no file references |
| 16 | UNVERIFIABLE | **[MEDIUM]** BuildArtifact underspecified for overview requirements | no file references |
| 17 | UNVERIFIABLE | **[MEDIUM]** Missing policy for non-text files | no file references |
| 18 | UNVERIFIABLE | **[LOW]** Grep-based enforcement is architecturally weak | no file references |
| 19 | CONFIRMED | **[LOW]** Python batch overview rewrite may require missing batch abstractions i... | llm_dispatch.py exists |

