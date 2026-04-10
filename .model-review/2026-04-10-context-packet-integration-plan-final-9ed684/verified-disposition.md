# Verified Disposition — 2026-04-10

**Claims:** 24 total — 8 CONFIRMED, 0 HALLUCINATED, 16 UNVERIFIABLE


| # | Verdict | Claim | Notes |
|---|---------|-------|-------|
| 1 | UNVERIFIABLE | **[HIGH]** `DispatchProfile` does not expose input-token limits needed for budge... | no file references |
| 2 | CONFIRMED | **[HIGH]** `build_plan_close_context.py` truncates diffs by raw character count ... | build_plan_close_context.py exists |
| 3 | CONFIRMED | **[HIGH]** `generate-overview.sh` uses an inaccurate `wc -c / 4` token heuristic | generate-overview.sh exists |
| 4 | CONFIRMED | **[HIGH]** `llm_dispatch.py` recomputes context hashes instead of consuming buil... | llm_dispatch.py exists |
| 5 | CONFIRMED | **[HIGH]** `parse_status_paths` in `build_plan_close_context.py` breaks on space... | build_plan_close_context.py exists |
| 6 | UNVERIFIABLE | **[HIGH]** Missing failure rule for budget vs protected blocks | no file references |
| 7 | UNVERIFIABLE | **[HIGH]** Under-defined hash taxonomy for content vs payload | no file references |
| 8 | UNVERIFIABLE | **[HIGH]** Unspecified handling of non-text source entities | no file references |
| 9 | UNVERIFIABLE | **[HIGH]** Ambiguous equivalence target for Overview live/batch | no file references |
| 10 | UNVERIFIABLE | **[HIGH]** Inconsistent token budget metadata in dispatch profiles | no file references |
| 11 | CONFIRMED | **[MEDIUM]** `llm_dispatch.py` still contains a duplicate `assemble_context` pac... | llm_dispatch.py exists |
| 12 | UNVERIFIABLE | **[MEDIUM]** Batch overview generation still assembles JSONL via raw string inte... | no file references |
| 13 | CONFIRMED | **[MEDIUM]** Overview payloads collide with `llm_dispatch.py` prompt wrapping | llm_dispatch.py exists |
| 14 | UNVERIFIABLE | **[MEDIUM]** There is no canonical shared context-packet module | no file references |
| 15 | UNVERIFIABLE | **[MEDIUM]** Overview generation should be rewritten in Python rather than orche... | no file references |
| 16 | CONFIRMED | **[MEDIUM]** `model-review.py` still uses ad hoc file-spec parsing instead of sh... | model-review.py exists |
| 17 | UNVERIFIABLE | **[MEDIUM]** Truncation logic may leave markdown code fences unclosed | no file references |
| 18 | UNVERIFIABLE | **[MEDIUM]** Context artifacts lack deterministic manifest/provenance hashes | no file references |
| 19 | UNVERIFIABLE | **[MEDIUM]** Phase ordering and test criteria sequencing inconsistency | no file references |
| 20 | UNVERIFIABLE | **[MEDIUM]** Lack of automated enforcement against helper duplication | no file references |
| 21 | UNVERIFIABLE | **[MEDIUM]** Incomplete selector precedence rules for migration | no file references |
| 22 | CONFIRMED | **[LOW]** `model-review.py` keeps constitutional/preamble logic inline instead o... | model-review.py exists |
| 23 | UNVERIFIABLE | **[LOW]** Low-value CLI surface expansion | no file references |
| 24 | UNVERIFIABLE | **[LOW]** Domain-specific logic leak in shared preamble helper | no file references |

