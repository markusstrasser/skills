# Model Review Context Packet

- Project: `/Users/alien/Projects/skills`
- Axes: `arch,formal`

## Preamble

## DEVELOPMENT CONTEXT

# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler or hacky approaches because they are faster to implement
- Cost-benefit analysis should filter on maintenance burden, supervision cost, complexity budget, and blast radius — not creation effort
- Implementation effort is not a meaningful cost dimension here; only ongoing drag matters

## Provided Context

### .model-review/context-packet-plan-close-focused.md

```text
# Plan-Close Review Packet

- Repo: `/Users/alien/Projects/skills`
- Mode: `worktree`
- Ref: `HEAD vs current worktree`

## Scope

- Target users: FILL ME
- Scale: FILL ME
- Rate of change: FILL ME

## Touched Files

### Touched Files

- `.claude/plans/2026-04-10-context-packet-integration-plan.md`
- `review/scripts/build_plan_close_context.py`
- `review/scripts/test_build_plan_close_context.py`
- `review/scripts/model-review.py`
- `review/scripts/test_model_review.py`
- `scripts/generate_overview.py`
- `scripts/test_generate_overview.py`
- `shared/context_packet.py`
- `shared/context_renderers.py`
- `shared/file_specs.py`
- `shared/git_context.py`
- `shared/llm_dispatch.py`
- `shared/overview_config.py`
- `shared/repomix_source.py`
- `shared/test_context_packet.py`

## Git Status

### git status --short

```text
M .claude/overview-marker-source
 M .claude/overviews/source-overview.md
 M _archive/architect/SKILL.md
 M brainstorm/SKILL.md
 M brainstorm/references/llmx-dispatch.md
 M hooks/epistemic-domain-router.sh
 M hooks/generate-overview-batch.sh
 M hooks/generate-overview.sh
 M hooks/overview-staleness-cron.sh
 M hooks/permission-auto-allow.sh
 M hooks/postmerge-overview.sh
 M hooks/pretool-llmx-guard.sh
 M hooks/sessionend-overview-trigger.sh
 M improve/SKILL.md
 M llmx-guide/SKILL.md
 M observe/SKILL.md
 M research-ops/SKILL.md
 M research-ops/scripts/run-cycle.sh
 M review/SKILL.md
 M review/lenses/plan-close-review.md
 M review/references/context-assembly.md
 M review/scripts/build_plan_close_context.py
 M review/scripts/model-review.py
 M review/scripts/test_model_review.py
 M upgrade/SKILL.md
?? .claude/overviews/.overview-source-codebase.txt
?? .claude/overviews/.overview-source-payload.manifest.json
?? .claude/overviews/.overview-source-payload.txt
?? .claude/plans/2026-04-10-context-packet-integration-plan.md
?? .claude/plans/2026-04-10-llm-dispatch-unification-plan.md
?? .model-review/2026-04-08-plan-close-api-migration-715928/arch-context.md
?? .model-review/2026-04-08-plan-close-api-migration-715928/arch-output.md
?? .model-review/2026-04-08-plan-close-api-migration-715928/formal-context.md
?? .model-review/2026-04-08-plan-close-api-migration-715928/formal-output.md
?? .model-review/2026-04-08-plan-close-final-a19774/arch-context.md
?? .model-review/2026-04-08-plan-close-final-a19774/arch-output.md
?? .model-review/2026-04-08-plan-close-final-a19774/formal-context.md
?? .model-review/2026-04-08-plan-close-final-a19774/formal-output.md
?? .model-review/2026-04-08-skill-dispatch-refactor-6980b4/arch-context.md
?? .model-review/2026-04-08-skill-dispatch-refactor-6980b4/arch-output.md
?? .model-review/2026-04-08-skill-dispatch-refactor-6980b4/formal-context.md
?? .model-review/2026-04-08-skill-dispatch-refactor-6980b4/formal-output.md
?? .model-review/2026-04-10-context-packet-integration-close-08c920/arch-output.md
?? .model-review/2026-04-10-context-packet-integration-close-08c920/arch-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-close-08c920/shared-context.manifest.json
?? .model-review/2026-04-10-context-packet-integration-close-08c920/shared-context.md
?? .model-review/2026-04-10-context-packet-integration-close-full-781cde/arch-output.md
?? .model-review/2026-04-10-context-packet-integration-close-full-781cde/arch-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-close-full-781cde/shared-context.manifest.json
?? .model-review/2026-04-10-context-packet-integration-close-full-781cde/shared-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/arch-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/arch-extraction.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/arch-extraction.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/arch-extraction.parsed.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/arch-output.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/arch-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/disposition.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/domain-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/domain-extraction.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/domain-extraction.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/domain-extraction.parsed.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/domain-output.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/domain-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/findings.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/formal-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/formal-extraction.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/formal-extraction.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/formal-extraction.parsed.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/formal-output.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/formal-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/mechanical-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/mechanical-extraction.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/mechanical-extraction.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/mechanical-extraction.parsed.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/mechanical-output.md
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/mechanical-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-fdd8c8/verified-disposition.md
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/arch-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/arch-extraction.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/arch-extraction.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/arch-extraction.parsed.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/arch-output.md
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/arch-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/disposition.md
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/findings.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/formal-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/formal-extraction.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/formal-extraction.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/formal-extraction.parsed.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/formal-output.md
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/formal-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-final-9ed684/verified-disposition.md
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/arch-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/arch-extraction.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/arch-extraction.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/arch-extraction.parsed.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/arch-output.md
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/arch-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/disposition.md
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/findings.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/formal-context.md
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/formal-extraction.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/formal-extraction.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/formal-extraction.parsed.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/formal-output.md
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/formal-output.meta.json
?? .model-review/2026-04-10-context-packet-integration-plan-revised-3cc1ff/verified-disposition.md
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/arch-context.md
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/arch-extraction.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/arch-extraction.meta.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/arch-extraction.parsed.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/arch-output.md
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/arch-output.meta.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/disposition.md
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/findings.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/formal-context.md
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/formal-extraction.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/formal-extraction.meta.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/formal-extraction.parsed.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/formal-output.md
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/formal-output.meta.json
?? .model-review/2026-04-10-llm-dispatch-focused-close-027c4b/verified-disposition.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/arch-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/arch-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/arch-output.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/disposition.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/domain-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/domain-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/domain-output.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/findings.json
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/formal-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/formal-extraction.json
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/formal-extraction.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/formal-extraction.parsed.json
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/formal-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/formal-output.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/mechanical-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/mechanical-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/mechanical-output.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-close-1f5842/verified-disposition.md
?? .model-review/2026-04-10-llm-dispatch-unification-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/arch-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/arch-extraction.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/arch-extraction.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/arch-extraction.parsed.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/arch-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/arch-output.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/disposition.md
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/findings.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/formal-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/formal-extraction.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/formal-extraction.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/formal-extraction.parsed.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/formal-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/formal-output.meta.json
?? .model-review/2026-04-10-llm-dispatch-unification-final-close-bfa03d/verified-disposition.md
?? .model-review/2026-04-10-llm-dispatch-unification-plan-4b1d66/arch-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-plan-4b1d66/arch-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-plan-4b1d66/domain-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-plan-4b1d66/domain-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-plan-4b1d66/formal-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-plan-4b1d66/formal-output.md
?? .model-review/2026-04-10-llm-dispatch-unification-plan-4b1d66/mechanical-context.md
?? .model-review/2026-04-10-llm-dispatch-unification-plan-4b1d66/mechanical-output.md
?? .model-review/context-packet-plan-close-full.manifest.json
?? .model-review/context-packet-plan-close-full.md
?? .model-review/context-packet-plan-close.manifest.json
?? .model-review/context-packet-plan-close.md
?? .model-review/plan-close-context-integration.manifest.json
?? .model-review/plan-close-context-integration.md
?? .model-review/plan-close-context-llm-dispatch-final.md
?? .model-review/plan-close-context-llm-dispatch-focused.md
?? .model-review/plan-close-context-llm-dispatch.md
?? .model-review/plan-close-scope-llm-dispatch.md
?? hooks/test_pretool_llmx_guard.py
?? scripts/generate_overview.py
?? scripts/llm-dispatch.py
?? scripts/test_generate_overview.py
?? scripts/test_llm_dispatch.py
?? shared/__init__.py
?? shared/context_packet.py
?? shared/context_preamble.py
?? shared/context_renderers.py
?? shared/file_specs.py
?? shared/git_context.py
?? shared/llm_dispatch.py
?? shared/overview_config.py
?? shared/repomix_source.py
?? shared/test_context_packet.py
```

### git diff --stat

```text
review/scripts/build_plan_close_context.py | 309 ++++++++---------------
 review/scripts/model-review.py             | 380 +++++++++++++----------------
 review/scripts/test_model_review.py        |  19 +-
 3 files changed, 287 insertions(+), 421 deletions(-)
```

### Unified Diff

```diff
review/scripts/build_plan_close_context.py --- 1/4 --- Python
  1 #!/usr/bin/env python3                 1 #!/usr/bin/env python3
  2 """Build a single markdown review p    2 """Build a single markdown review p
  . acket for plan-close / post-impleme    . acket for plan-close / post-impleme
  . ntation review.                        . ntation review.
  3                                        3 
  4 The packet is intentionally single-    4 The packet is intentionally single-
  . file because llmx multi-file `-f` t    . file because llmx multi-file transp
  . ransport                               . ort has
  5 has recurring loss/truncation failu    5 recurring loss/truncation failures 
  . res in critical review flows.          . in critical review flows.
  6 """                                    6 """
  7                                        7 
  8 from __future__ import annotations     8 from __future__ import annotations
  9                                        9 
 10 import argparse                       10 import argparse
 11 import subprocess                     .. 
 12 import sys                            11 import sys
 13 from pathlib import Path              12 from pathlib import Path
 ..                                       13 
 ..                                       14 ROOT = Path(__file__).resolve().par
 ..                                       .. ents[2]
 ..                                       15 if str(ROOT) not in sys.path:
 ..                                       16     sys.path.insert(0, str(ROOT))
 ..                                       17 
 ..                                       18 from shared.context_packet import B
 ..                                       .. udgetPolicy, CommandBlock, ContextP
 ..                                       .. acket, DiffBlock, FileBlock, ListBl
 ..                                       .. ock, PacketSection, TextBlock
 ..                                       19 from shared.context_renderers impor
 ..                                       .. t render_markdown, write_packet_art
 ..                                       .. ifact
 ..                                       20 from shared.file_specs import parse
 ..                                       .. _file_spec, read_file_excerpt
 ..                                       21 from shared.git_context import coll
 ..                                       .. ect_diff, collect_diff_stat, curren
 ..                                       .. t_status, diff_ref, resolve_touched
 ..                                       .. _files
 ..                                       22 
 ..                                       23 
 ..                                       24 BUILDER_VERSION = "2026-04-10-v1"
 14                                       25 
 15                                       26 
 16 def log_progress(message: str) -> N   27 def log_progress(message: str) -> N
 .. one:                                  .. one:
 17     print(f"[build-plan-close-conte   28     print(f"[build-plan-close-conte
 .. xt] {message}", file=sys.stderr)      .. xt] {message}", file=sys.stderr)
 18                                       .. 
 19                                       .. 
 20 def run_git(repo: Path, args: list[   .. 
 .. str], *, check: bool = True) -> str   .. 
 .. :                                     .. 
 21     proc = subprocess.run(            .. 
 22         ["git", "-C", str(repo), *a   .. 
 .. rgs],                                 .. 
 23         capture_output=True,          .. 
 24         text=True,                    .. 
 25     )                                 .. 
 26     if check and proc.returncode !=   .. 
 ..  0:                                   .. 
 27         raise RuntimeError(proc.std   .. 
 .. err.strip() or f"git {' '.join(args   .. 
 .. )} failed")                           .. 
 28     return proc.stdout                .. 
 29                                       .. 
 30                                       .. 
 31 def diff_ref(base: str | None, head   .. 
 .. : str | None) -> str | None:          .. 
 32     if base and head:                 .. 
 33         return f"{base}..{head}"      .. 
 34     if base:                          .. 
 35         return f"{base}..HEAD"        .. 
 36     if head:                          .. 
 37         return f"HEAD..{head}"        .. 
 38     return None                       .. 
 39                                       .. 
 40                                       .. 
 41 def parse_status_paths(status_text:   .. 
 ..  str) -> list[str]:                   .. 
 42     paths: list[str] = []             .. 
 43     seen: set[str] = set()            .. 
 44     for raw_line in status_text.spl   .. 
 .. itlines():                            .. 
 45         line = raw_line.rstrip()      .. 
 46         if len(line) < 4:             .. 
 47             continue                  .. 
 48         path_field = line[3:]         .. 
 49         if " -> " in path_field:      .. 
 50             path_field = path_field   .. 
 .. .split(" -> ", 1)[1]                  .. 
 51         if path_field and path_fiel   .. 
 .. d not in seen:                        .. 
 52             seen.add(path_field)      .. 
 53             paths.append(path_field   .. 
 .. )                                     .. 
 54     return paths                      .. 
 55                                       .. 
 56                                       .. 
 57 def unique_paths(paths: list[str])    .. 
 .. -> list[str]:                         .. 
 58     seen: set[str] = set()            .. 
 59     ordered: list[str] = []           .. 
 60     for path in paths:                .. 
 61         if path not in seen:          .. 
 62             seen.add(path)            .. 
 63             ordered.append(path)      .. 
 64     return ordered                    .. 
 65                                       29 
 66                                       30 
 67 def resolve_touched_files(            31 def build_scope(scope_text: str | N
 ..                                       .. one, scope_file: Path | None) -> st
 ..                                       .. r:
 68     repo: Path,                       .. 
 69     *,                                .. 
 70     base: str | None,                 .. 
 71     head: str | None,                 .. 
 72     files: list[str] | None,          .. 
 73     tracked_only: bool,               .. 
 74 ) -> list[str]:                       .. 
 75     if files:                         32     if scope_file is not None:
 76         return unique_paths(files)    .. 
 77                                       .. 
 78     ref = diff_ref(base, head)        .. 
 79     if ref:                           .. 
 80         names = run_git(repo, ["dif   .. 
 .. f", "--name-only", ref, "--"]).spli   .. 
 .. tlines()                              .. 
 81         return [name for name in na   33         return scope_file.read_text
 .. mes if name.strip()]                  .. ().strip()
 82                                       .. 
 83     if tracked_only:                  34     if scope_text:
 84         names = run_git(repo, ["dif   .. 
 .. f", "--name-only", "HEAD", "--"], c   .. 
 .. heck=False).splitlines()              .. 
 85         return [name for name in na   35         return scope_text.strip()
 .. mes if name.strip()]                  .. 
 86                                       .. 
 87     status_text = run_git(repo, ["s   .. 
 .. tatus", "--short", "--untracked-fil   .. 
 .. es=all"])                             .. 
 88     return parse_status_paths(statu   36     return (
 .. s_text)                               .. 
 89                                       37         "- Target users: FILL ME\n"
 90                                       38         "- Scale: FILL ME\n"
 91 def current_status(repo: Path, *, t   39         "- Rate of change: FILL ME"
 .. racked_only: bool) -> str:            .. 
 92     args = ["status", "--short"]      40     )
 93     args.append("--untracked-files=   .. 
 .. no" if tracked_only else "--untrack   .. 
 .. ed-files=all")                        .. 
 94     return run_git(repo, args, chec   .. 
 .. k=False).strip()                      .. 
 95                                       .. 
 96                                       .. 
 97 def untracked_paths(repo: Path) ->    .. 
 .. set[str]:                             .. 
 98     raw = run_git(repo, ["ls-files"   .. 
 .. , "--others", "--exclude-standard"]   .. 
 .. , check=False)                        .. 
 99     return {line.strip() for line i   .. 
 .. n raw.splitlines() if line.strip()}   .. 
100                                       .. 
101                                       .. 
102 def collect_diff_stat(repo: Path, *   .. 
... , ref: str | None, files: list[str]   .. 
... ) -> str:                             .. 
103     tracked_files = [path for path    .. 
... in files if path not in untracked_p   .. 
... aths(repo)]                           .. 
104     if not tracked_files:             .. 
105         return "(no tracked diff st   .. 
... at available)"                        .. 
106     args = ["diff", "--stat"]         .. 
107     if ref:                           .. 
108         args.append(ref)              .. 
109     else:                             .. 
110         args.append("HEAD")           .. 
111     args.append("--")                 .. 
112     args.extend(tracked_files)        .. 
113     return run_git(repo, args, chec   .. 
... k=False).strip() or "(empty diff st   .. 
... at)"                                  .. 
114                                       .. 
115                                       .. 
116 def collect_diff(repo: Path, *, ref   .. 
... : str | None, files: list[str]) ->    .. 
... str:                                  .. 
117     tracked_files = [path for path    .. 
... in files if path not in untracked_p   .. 
... aths(repo)]                           .. 
118     if not tracked_files:             .. 
119         return "(no tracked unified   .. 
...  diff available)"                     .. 
120     args = ["diff", "--unified=3"]    .. 
121     if ref:                           .. 
122         args.append(ref)              .. 
123     else:                             .. 
124         args.append("HEAD")           .. 
125     args.append("--")                 .. 
126     args.extend(tracked_files)        .. 
127     return run_git(repo, args, chec   .. 
... k=False).strip() or "(empty diff)"    .. 
128                                       .. 
129                                       .. 
130 def read_excerpt(path: Path, max_ch   .. 
... ars: int) -> str:                     .. 
131     try:                              .. 
132         text = path.read_text(error   .. 
... s="replace")                          .. 
133     except OSError as exc:            .. 
134         return f"[read failed: {exc   .. 
... }]"                                   .. 
135                                       .. 
136     if len(text) <= max_chars:        .. 
137         return text                   .. 
138                                       .. 
139     head = max_chars // 2             .. 
140     tail = max_chars - head           .. 
141     return (                          .. 
142         text[:head]                   .. 
143         + "\n\n... [truncated for r   .. 
... eview packet] ...\n\n"                .. 
144         + text[-tail:]                .. 
145     )                                 .. 
146                                       .. 
147                                       .. 
148 def file_section(repo: Path, rel_pa   .. 
... th: str, *, max_chars: int) -> str:   .. 
149     path = repo / rel_path            .. 
150     if not path.exists():             .. 
151         return f"### {rel_path}\n\n   .. 
... (deleted or absent in current workt   .. 
... ree)\n"                               .. 
152                                       .. 
153     return (                          .. 
154         f"### {rel_path}\n\n"         .. 
155         f"```text\n{read_excerpt(pa   .. 
... th, max_chars)}\n```\n"               .. 
156     )                                 .. 
157                                       41 
158                                       42 
159 def build_packet(                     43 def build_packet_model(
160     repo: Path,                       44     repo: Path,
161     *,                                45     *,
162     base: str | None,                 46     base: str | None,

review/scripts/build_plan_close_context.py --- 2/4 --- Python
168     max_diff_chars: int,              52     max_diff_chars: int,
169     max_file_chars: int,              53     max_file_chars: int,
170     max_files: int,                   54     max_files: int,
171 ) -> str:                             55 ) -> ContextPacket:
172     log_progress("resolving touched   56     log_progress("resolving touched
...  files")                              ..  files")
173     touched = resolve_touched_files   57     touched = resolve_touched_files
... (repo, base=base, head=head, files=   .. (repo, base=base, head=head, files=
... files, tracked_only=tracked_only)     .. files, tracked_only=tracked_only)
174     ref = diff_ref(base, head)        58     ref = diff_ref(base, head)
...                                       59 
175     log_progress("collecting git st   60     log_progress("collecting git st
... atus")                                .. atus")
176     status_text = current_status(re   61     status_text = current_status(re
... po, tracked_only=tracked_only) or "   .. po, tracked_only=tracked_only) or "
... (clean)"                              .. (clean)"
177     log_progress(f"collecting diffs   62     log_progress(f"collecting diffs
...  for {len(touched)} touched files")   ..  for {len(touched)} touched files")
178     diff_stat = collect_diff_stat(r   63     diff_stat = collect_diff_stat(r
... epo, ref=ref, files=touched) if tou   .. epo, ref=ref, files=touched) if tou
... ched else "(no touched files)"        .. ched else "(no touched files)"
179     diff_text = collect_diff(repo,    64     diff_text, diff_truncated = col
... ref=ref, files=touched) if touched    .. lect_diff(repo, ref=ref, files=touc
... else "(no touched files)"             .. hed, max_chars=max_diff_chars) if t
...                                       .. ouched else ("(no touched files)", 
...                                       .. False)
180     if len(diff_text) > max_diff_ch   .. 
... ars:                                  .. 
181         diff_text = diff_text[:max_   .. 
... diff_chars] + "\n\n... [diff trunca   .. 
... ted] ..."                             .. 
182                                       .. 
183     if scope_file is not None:        .. 
184         scope_block = scope_file.re   .. 
... ad_text()                             .. 
185     elif scope_text:                  .. 
186         scope_block = scope_text      .. 
187     else:                             .. 
188         scope_block = (               .. 
189             "- Target users: FILL M   .. 
... E\n"                                  .. 
190             "- Scale: FILL ME\n"      .. 
191             "- Rate of change: FILL   .. 
...  ME\n"                                .. 
192         )                             .. 
193                                       65 
194     packet = [                        66     touched_section = PacketSection
...                                       .. (
195         "# Plan-Close Review Packet   67         "Touched Files",
... ",                                    .. 
196         "",                           .. 
197         f"- Repo: `{repo}`",          .. 
198         f"- Mode: `{'commit-range'    .. 
... if ref else 'worktree'}`",            .. 
199         f"- Ref: `{ref or 'HEAD vs    .. 
... current worktree'}`",                 .. 
200         "",                           .. 
201         "## Scope",                   .. 
202         "",                           .. 
203         scope_block.strip(),          .. 
204         "",                           .. 
205         "## Touched Files",           .. 
206         "",                           .. 
207     ]                                 .. 
208                                       .. 
209     if touched:                       .. 
210         packet.extend(f"- `{path}`"   68         [ListBlock("Touched Files",
...  for path in touched)                 ..  [f"- `{path}`" for path in touched
...                                       .. ] if touched else ["- (none)"])],
211     else:                             69     )
212         packet.append("- (none)")     .. 
213                                       .. 
214     packet.extend(                    70     git_section = PacketSection(
...                                       71         "Git Status",
215         [                             72         [
216             "",                       .. 
217             "## Git Status",          73             CommandBlock("git statu
...                                       .. s --short", status_text),
218             "",                       .. 
219             "```text",                .. 
220             status_text,              .. 
221             "```",                    .. 
222             "",                       .. 
223             "## Diff Stat",           74             CommandBlock("git diff 
...                                       .. --stat", diff_stat),
224             "",                       75             DiffBlock(
225             "```text",                .. 
226             diff_stat,                .. 
227             "```",                    .. 
228             "",                       .. 
229             "## Unified Diff",        76                 "Unified Diff",
230             "",                       .. 
231             "```diff",                .. 
232             diff_text,                77                 diff_text,
233             "```",                    78                 truncated=diff_trun
...                                       .. cated,
234             "",                       79                 truncation_reason="
...                                       .. diff_char_limit" if diff_truncated 
...                                       .. else None,
235             "## Current File Excerp   80             ),
... ts",                                  .. 
236             "",                       81         ],
237         ]                             .. 
238     )                                 82     )
239                                       83 
240     display_files = touched[:max_fi   84     display_files = touched[:max_fi
... les]                                  .. les]
241     log_progress(f"reading excerpts   85     log_progress(f"reading excerpts
...  for {len(display_files)} files")     ..  for {len(display_files)} files")
...                                       86     file_sections_blocks = []
242     for rel_path in display_files:    87     for rel_path in display_files:
...                                       88         spec_path = repo / rel_path
...                                       89         spec = parse_file_spec(str(
...                                       .. spec_path))
243         packet.append(file_section(   90         text, truncated, omission_r
... repo, rel_path, max_chars=max_file_   .. eason = read_file_excerpt(spec, max
... chars))                               .. _chars=max_file_chars)
244                                       91         metadata: dict[str, object]
...                                       ..  = {}
...                                       92         if omission_reason:
...                                       93             metadata["omission_reas
...                                       .. on"] = omission_reason
...                                       94         block = FileBlock(
...                                       95             rel_path,
...                                       96             text,
...                                       97             range_spec=spec.range_s
...                                       .. pec,
...                                       98             truncated=truncated,
...                                       99             truncation_reason="file
...                                       .. _excerpt_limit" if truncated else N
...                                       .. one,
...                                      100             original_chars=None if 
...                                      ... not truncated else len(spec_path.re
...                                      ... ad_text(errors="replace")),
...                                      101             metadata=metadata,
...                                      102         )
...                                      103         file_sections_blocks.append
...                                      ... (block)
245     omitted = len(touched) - len(di  104     omitted = len(touched) - len(di
... splay_files)                         ... splay_files)
246     if omitted > 0:                  105     if omitted > 0:
247         packet.append(f"\n(Omitted   106         file_sections_blocks.append
... {omitted} additional touched files   ... (TextBlock("Omitted Files", f"(Omit
... from excerpts.)\n")                  ... ted {omitted} additional touched fi
...                                      ... les from excerpts.)"))
...                                      107     files_section = PacketSection("
...                                      ... Current File Excerpts", file_sectio
...                                      ... ns_blocks or [TextBlock("Current Fi
...                                      ... le Excerpts", "(none)")])
248                                      108 
249     return "\n".join(packet)         109     return ContextPacket(
...                                      110         title="Plan-Close Review Pa
...                                      ... cket",
...                                      111         sections=[touched_section, 
...                                      ... git_section, files_section],
...                                      112         scope=build_scope(scope_tex
...                                      ... t, scope_file),
...                                      113         metadata={
...                                      114             "Repo": str(repo),
...                                      115             "Mode": "commit-range" 
...                                      ... if ref else "worktree",
...                                      116             "Ref": ref or "HEAD vs 
...                                      ... current worktree",
...                                      117         },
...                                      118         budget_policy=BudgetPolicy(
...                                      ... metric="chars", limit=max_diff_char
...                                      ... s, estimate_method="heuristic:chars
...                                      ... _div_4"),
...                                      119     )
...                                      120 
...                                      121 
...                                      122 def build_packet(
...                                      123     repo: Path,
...                                      124     *,
...                                      125     base: str | None,
...                                      126     head: str | None,
...                                      127     files: list[str] | None,
...                                      128     tracked_only: bool,
...                                      129     scope_text: str | None,
...                                      130     scope_file: Path | None,
...                                      131     max_diff_chars: int,
...                                      132     max_file_chars: int,
...                                      133     max_files: int,
...                                      134 ) -> str:
...                                      135     packet = build_packet_model(
...                                      136         repo,
...                                      137         base=base,
...                                      138         head=head,
...                                      139         files=files,
...                                      140         tracked_only=tracked_only,
...                                      141         scope_text=scope_text,
...                                      142         scope_file=scope_file,
...                                      143         max_diff_chars=max_diff_cha
...                                      ... rs,
...                                      144         max_file_chars=max_file_cha
...                                      ... rs,
...                                      145         max_files=max_files,
...                                      146     )
...                                      147     return render_markdown(packet)
250                                      148 
251                                      149 
252 def parse_args() -> argparse.Namesp  150 def parse_args() -> argparse.Namesp
... ace:                                 ... ace:

review/scripts/build_plan_close_context.py --- 3/4 --- Python
279         print(f"not a git repo: {re  177         print(f"not a git repo: {re
... po}", file=sys.stderr)               ... po}", file=sys.stderr)
280         return 2                     178         return 2
281                                      179 
282     packet = build_packet(           180     packet = build_packet_model(
283         repo,                        181         repo,
284         base=args.base,              182         base=args.base,
285         head=args.head,              183         head=args.head,

review/scripts/build_plan_close_context.py --- 4/4 --- Python
293     )                                191     )
294                                      192 
295     log_progress(f"writing packet t  193     log_progress(f"writing packet t
... o {args.output}")                    ... o {args.output}")
296     args.output.parent.mkdir(parent  194     manifest_path = args.output.wit
... s=True, exist_ok=True)               ... h_suffix(".manifest.json")
...                                      195     write_packet_artifact(
...                                      196         packet,
...                                      197         renderer="markdown",
297     args.output.write_text(packet)   198         output_path=args.output,
...                                      199         manifest_path=manifest_path
...                                      ... ,
...                                      200         builder_name="plan_close_co
...                                      ... ntext",
...                                      201         builder_version=BUILDER_VER
...                                      ... SION,
...                                      202     )
298     print(args.output)               203     print(args.output)
299     return 0                         204     return 0
300                                      205 

review/scripts/model-review.py --- 1/21 --- Text (exceeded DFT_GRAPH_LIMIT)
 29 from concurrent.futures import Thre   29 from concurrent.futures import Thre
 .. adPoolExecutor, as_completed          .. adPoolExecutor, as_completed
 30 from datetime import date             30 from datetime import date
 31 from pathlib import Path              31 from pathlib import Path
 ..                                       32 from typing import NamedTuple
 32                                       33 
 33 # llmx is editable-installed as a u   34 ROOT = Path(__file__).resolve().par
 .. v tool; bootstrap from its venv if    .. ents[2]
 .. not importable                        .. 
 34 try:                                  .. 
 35     from llmx.api import chat as ll   .. 
 .. mx_chat                               .. 
 36 except ImportError:                   .. 
 37     import glob                       .. 
 38     _tool_site = glob.glob(str(Path   .. 
 .. .home() / ".local/share/uv/tools/ll   .. 
 .. mx/lib/python*/site-packages"))       .. 
 39     if _tool_site:                    35 if str(ROOT) not in sys.path:
 40         sys.path.insert(0, _tool_si   .. 
 .. te[0])                                .. 
 41     sys.path.insert(0, str(Path.hom   36     sys.path.insert(0, str(ROOT))
 .. e() / "Projects" / "llmx"))           .. 
 42     from llmx.api import chat as ll   .. 
 .. mx_chat                               .. 
 43                                       37 
 ..                                       38 import shared.llm_dispatch as dispa
 ..                                       .. tch_core
 ..                                       39 from shared.context_packet import B
 ..                                       .. udgetPolicy, ContextPacket, FileBlo
 ..                                       .. ck, PacketSection, TextBlock
 ..                                       40 from shared.context_preamble import
 ..                                       ..  build_review_preamble_blocks, find
 ..                                       .. _constitution as shared_find_consti
 ..                                       .. tution
 ..                                       41 from shared.context_renderers impor
 ..                                       .. t write_packet_artifact
 ..                                       42 from shared.file_specs import parse
 ..                                       .. _file_spec, read_file_excerpt
 ..                                       43 
 44 # --- Structured output schema (bot   44 # --- Structured output schema (bot
 .. h models return this) ---             .. h models return this) ---
 45                                       45 
 46 FINDING_SCHEMA = {                    46 FINDING_SCHEMA = {

review/scripts/model-review.py --- 2/21 --- Text (exceeded DFT_GRAPH_LIMIT)
 75 AXES = {                              75 AXES = {
 76     "arch": {                         76     "arch": {
 77         "label": "Gemini (architect   77         "label": "Gemini (architect
 .. ure/patterns)",                       .. ure/patterns)",
 78         "model": "gemini-3.1-pro-pr   78         "profile": "deep_review",
 .. eview",                               .. 
 79         "provider": "google",         .. 
 80         "api_kwargs": {"timeout": 3   .. 
 .. 00},                                  .. 
 81         "prompt": """\                79         "prompt": """\
 82 <system>                              80 <system>
 83 You are reviewing a codebase. Be co   81 You are reviewing a codebase. Be co
 .. ncrete. No platitudes. Reference sp   .. ncrete. No platitudes. Reference sp
 .. ecific code, configs, and findings.   .. ecific code, configs, and findings.
 ..  It is {date}.                        ..  It is {date}.

review/scripts/model-review.py --- 3/21 --- Text (exceeded DFT_GRAPH_LIMIT)
108     },                               106     },
109     "formal": {                      107     "formal": {
110         "label": "GPT-5.4 (quantita  108         "label": "GPT-5.4 (quantita
... tive/formal)",                       ... tive/formal)",
111         "model": "gpt-5.4",          109         "profile": "formal_review",
112         "provider": "openai",        ... 
113         "api_kwargs": {"timeout": 6  ... 
... 00, "reasoning_effort": "high", "ma  ... 
... x_tokens": 32768},                   ... 
114         "prompt": """\               110         "prompt": """\
115 <system>                             111 <system>
116 You are performing QUANTITATIVE and  112 You are performing QUANTITATIVE and
...  FORMAL analysis. Other reviewers h  ...  FORMAL analysis. Other reviewers h
... andle qualitative pattern review. F  ... andle qualitative pattern review. F
... ocus on what they can't do well. Be  ... ocus on what they can't do well. Be
...  precise. Show your reasoning. No h  ...  precise. Show your reasoning. No h
... and-waving.                          ... and-waving.

review/scripts/model-review.py --- 4/21 --- Text (exceeded DFT_GRAPH_LIMIT)
141     },                               137     },
142     "domain": {                      138     "domain": {
143         "label": "Gemini Pro (domai  139         "label": "Gemini Pro (domai
... n correctness)",                     ... n correctness)",
144         "model": "gemini-3.1-pro-pr  140         "profile": "deep_review",
... eview",                              ... 
145         "provider": "google",        ... 
146         "api_kwargs": {"timeout": 3  ... 
... 00},                                 ... 
147         "prompt": """\               141         "prompt": """\
148 <system>                             142 <system>
149 You are verifying DOMAIN-SPECIFIC C  143 You are verifying DOMAIN-SPECIFIC C
... LAIMS in this plan. Other reviewers  ... LAIMS in this plan. Other reviewers
...  handle architecture and formal log  ...  handle architecture and formal log
... ic.                                  ... ic.

review/scripts/model-review.py --- 5/21 --- Text (exceeded DFT_GRAPH_LIMIT)
164     },                               158     },
165     "mechanical": {                  159     "mechanical": {
166         "label": "Gemini Flash (mec  160         "label": "Gemini Flash (mec
... hanical audit)",                     ... hanical audit)",
167         "model": "gemini-3-flash-pr  161         "profile": "fast_extract",
... eview",                              ... 
168         "provider": "google",        ... 
169         "api_kwargs": {"timeout": 1  ... 
... 20},                                 ... 
170         "prompt": """\               162         "prompt": """\
171 <system>                             163 <system>
172 Mechanical audit only. No analysis,  164 Mechanical audit only. No analysis,
...  no recommendations. Fast and preci  ...  no recommendations. Fast and preci
... se.                                  ... se.

review/scripts/model-review.py --- 6/21 --- Text (exceeded DFT_GRAPH_LIMIT)
182     },                               174     },
183     "alternatives": {                175     "alternatives": {
184         "label": "Gemini Pro (alter  176         "label": "Gemini Pro (alter
... native approaches)",                 ... native approaches)",
185         "model": "gemini-3.1-pro-pr  177         "profile": "deep_review",
... eview",                              ... 
186         "provider": "google",        ... 
187         "api_kwargs": {"timeout": 3  ... 
... 00},                                 ... 
188         "prompt": """\               178         "prompt": """\
189 <system>                             179 <system>
190 You are generating ALTERNATIVE APPR  180 You are generating ALTERNATIVE APPR
... OACHES to the proposed plan. Other   ... OACHES to the proposed plan. Other 
... reviewers check correctness.         ... reviewers check correctness.

review/scripts/model-review.py --- 7/21 --- Text (exceeded DFT_GRAPH_LIMIT)
204     },                               194     },
205     "simple": {                      195     "simple": {
206         "label": "Gemini Pro (combi  196         "label": "Gemini Pro (combi
... ned review)",                        ... ned review)",
207         "model": "gemini-3.1-pro-pr  197         "profile": "deep_review",
... eview",                              ... 
208         "provider": "google",        ... 
209         "api_kwargs": {"timeout": 3  ... 
... 00},                                 ... 
210         "prompt": """\               198         "prompt": """\
211 <system>                             199 <system>
212 Quick combined review. Be concrete.  200 Quick combined review. Be concrete.
...  It is {date}. Budget: ~1000 words.  ...  It is {date}. Budget: ~1000 words.

review/scripts/model-review.py --- 8/21 --- Text (exceeded DFT_GRAPH_LIMIT)
227     "full": ["arch", "formal", "dom  215     "full": ["arch", "formal", "dom
... ain", "mechanical", "alternatives"]  ... ain", "mechanical", "alternatives"]
... ,                                    ... ,
228 }                                    216 }
229                                      217 
230 GEMINI_PRO_MODEL = "gemini-3.1-pro-  218 GEMINI_PRO_MODEL = dispatch_core.PR
... preview"                             ... OFILES["deep_review"].model
231 GEMINI_FLASH_MODEL = "gemini-3-flas  219 GEMINI_FLASH_MODEL = dispatch_core.
... h-preview"                           ... PROFILES["fast_extract"].model
232 GEMINI_RATE_LIMIT_MARKERS = (        220 GEMINI_RATE_LIMIT_MARKERS = (
233     "503",                           221     "503",
234     "rate limit",                    222     "rate limit",

review/scripts/model-review.py --- 9/21 --- Text (exceeded DFT_GRAPH_LIMIT)
239 227 )
240 228 
241 229 
... 230 class ContextArtifact(NamedTuple):
... 231     content_path: Path
... 232     manifest_path: Path
... 233 
... 234 
... 235 def context_content_path(value: Path | ContextArtifact) -> Path:
... 236     return value.content_path if isinstance(value, ContextArtifact) else value
... 237 
... 238 
... 239 def context_manifest_path(value: Path | ContextArtifact) -> Path | None:
... 240     return value.manifest_path if isinstance(value, ContextArtifact) else None
... 241 
... 242 
242 243 def slugify(text: str, max_len: int = 40) -> str:
243 244     s = text.lower()
244 245     s = re.sub(r"[^a-z0-9]+", "-", s)

review/scripts/model-review.py --- 10/21 --- Text (exceeded DFT_GRAPH_LIMIT)
249 def _add_additional_properties(sche  250 def _add_additional_properties(sche
... ma: dict) -> dict:                   ... ma: dict) -> dict:
250     """Recursively add additionalPr  251     """Recursively add additionalPr
... operties:false to all objects (Open  ... operties:false to all objects (Open
... AI strict mode)."""                  ... AI strict mode)."""
251     import copy                      252     import copy
...                                      253 
252     s = copy.deepcopy(schema)        254     transformed = copy.deepcopy(sch
...                                      ... ema)
...                                      255 
253     def _walk(obj: dict) -> None:    256     def walk(obj: dict) -> None:
254         if obj.get("type") == "obje  257         if obj.get("type") == "obje
... ct":                                 ... ct":
255             obj["additionalProperti  258             obj["additionalProperti
... es"] = False                         ... es"] = False
256         for v in obj.values():       259         for value in obj.values():
257             if isinstance(v, dict):  260             if isinstance(value, di
...                                      ... ct):
258                 _walk(v)             261                 walk(value)
259             elif isinstance(v, list  262             elif isinstance(value, 
... ):                                   ... list):
260                 for item in v:       263                 for item in value:
261                     if isinstance(i  264                     if isinstance(i
... tem, dict):                          ... tem, dict):
262                         _walk(item)  265                         walk(item)
263     _walk(s)                         ... 
264     return s                         ... 
265                                      266 
...                                      267     walk(transformed)
...                                      268     return transformed
266                                      269
... [diff truncated] ...
```

## Current File Excerpts

### .claude/plans/2026-04-10-context-packet-integration-plan.md

```text
# Context Packet Integration Plan

Date: 2026-04-10
Repo: `~/Projects/skills`
Status: implemented
Decision type: breaking refactor, full migration

## Problem

The repo now has a shared model-dispatch spine, but context creation is still fragmented.

Today there are at least three separate packet/context assembly paths:

1. `review/scripts/build_plan_close_context.py`
   - builds a review packet from git status, diff, and file excerpts
   - owns touched-file resolution, truncation, and markdown packet rendering

2. `review/scripts/model-review.py`
   - owns `parse_file_spec()`, `assemble_context_files()`, constitutional preamble injection, goals injection, and per-axis context file construction

3. `hooks/generate-overview.sh` / `hooks/generate-overview-batch.sh`
   - build prompt/context packets from prompt templates plus `repomix` output
   - own their own source selection, prompt wrapping, token estimation, and rendering

These are all solving versions of the same mechanical problem:

- gather heterogeneous inputs
- order them into sections
- label provenance
- truncate to a budget
- write stable artifacts for models to consume

But they currently do so with different ad hoc code paths, different rendering styles, and different truncation logic.

The result:

- packet drift across skills
- repeated file/range parsing logic
- repeated preamble injection logic
- no single manifest/hash surface for context provenance
- no reusable way for new skills to say “build me a good context packet”

The repo now needs one canonical context-packet layer, analogous to what `shared/llm_dispatch.py` became for model calls.

Important integration reality:

- `shared/llm_dispatch.py` is not a passive downstream consumer today
- it still owns a small context-assembly helper and only publishes output-token limits
- this plan therefore has to include a small `llm_dispatch.py` contract cleanup, not just new packet modules

## Scope

- Target users: agents and hooks consuming `~/Projects/skills` across local repos
- Scale:
  - current: review packets, plan-close packets, overview prompts, skill-local context snippets
  - designed-for: many packet-producing skills across many repos, repeated automated review/research/overview runs
- Rate of change: high; new skills and review surfaces are still being added and modified weekly

## Decision

Build a shared **context packet engine** that generalizes packet construction mechanics, not task semantics.

Concretely:

1. Add a shared library for packet primitives, section composition, truncation, hashing, and rendering.
2. Add builder-specific adapters for plan-close, model-review, and overview generation.
3. Migrate current packet-producing code onto the shared engine.
4. Keep selection logic task-specific; do not force one universal packet schema.
5. Preserve a thin compatibility wrapper where callers already use a specific script path, but move the real logic into shared code.

This is a breaking refactor in the implementation layer:

- shared mechanics move into one module
- duplicated local assembly logic is deleted
- old scripts survive only as thin wrappers if they are already a live entrypoint

## Non-Goal

This is **not** a universal “one packet format for every repo and every task.”

The thing that generalizes is:

- file blocks
- diff blocks
- text blocks
- command/output blocks
- ordering
- truncation
- hashing
- rendering

The thing that does **not** generalize is:

- which files matter for a given task
- how a repo selects those files
- what sections are semantically relevant
- what “good context” means for a review vs an overview vs a research packet

The correct abstraction boundary is:

- shared packet mechanics
- task-specific builders/selectors

not:

- one giant schema with dozens of optional branches

Additional non-goal:

- do not force overview generation into the same markdown packet renderer used by review/plan-close if the live prompt-wrapped format (`<instructions>`, `<codebase>`) is materially part of its behavior

## Evidence From Current Code

### 1. Plan-close already has a packet renderer

`review/scripts/build_plan_close_context.py` already implements:

- touched file resolution
- diff and diff-stat collection
- scope block insertion
- excerpt truncation
- markdown packet rendering

This is clearly reusable machinery.

### 2. Model-review already has a second context-assembly path

`review/scripts/model-review.py` separately implements:

- `parse_file_spec()`
- `assemble_context_files()`
- constitution/goals preamble injection
- per-axis context file writing

This overlaps strongly with the plan-close builder but is not sharing code.

### 3. Overview generation has a third packet path

`hooks/generate-overview.sh` and `hooks/generate-overview-batch.sh` both:

- collect source trees via `repomix`
- wrap prompt instructions and source content into structured sections
- estimate token size
- write prompt/context artifacts

That is packet assembly, but done in shell and duplicated across live and batch paths.

### 4. Review docs already assume a single-file context packet is better

`review/references/context-assembly.md` and `review/lenses/plan-close-review.md` already converge on the same discipline:

- one assembled context file
- explicit scope
- constitutional preamble when relevant
- avoid multi-file transport loss

The architecture is already implicit in the docs. The code just hasn’t been unified yet.

### 5. Dispatch still owns context assembly and incomplete budget metadata

`shared/llm_dispatch.py` currently still:

- has `assemble_context(...)`
- computes its own `context_sha256`
- publishes `max_tokens` for output, but not explicit input-budget metadata

That means the packet layer cannot be truly canonical unless dispatch consumes packet artifacts and exposes model-facing input-budget data.

## Target Architecture

### 1. Shared packet core

Add:

- `shared/context_packet.py`

Core responsibilities:

- block types
- packet c

... [truncated for review packet] ...

packet.py`

Capabilities:

- render packet from file specs
- emit manifest
- support named builders (`plan-close`, `overview`, later `review`)

Exit condition:

- at least two live callers use the CLI surface without custom glue

### Phase 6: tighten enforcement

Add:

- tests preventing new ad hoc packet builders in active scripts
- import-boundary checks for active entrypoints
- guidance updates in `review` docs and any skill that assembles large context blobs

Exit condition:

- future packet drift gets caught automatically

## Specific File-Level Recommendations

### `review/scripts/build_plan_close_context.py`

- keep script path
- delete private packet rendering logic
- convert into `PlanClosePacketBuilder`
- keep CLI contract if users/scripts already call it

### `review/scripts/model-review.py`

- keep review-specific prompts and axis orchestration
- move packet mechanics out
- keep constitutional anchoring, but source the preamble assembly from shared selectors/helpers
- stop writing N semantically identical context payloads when one shared payload hash would suffice

### `shared/llm_dispatch.py`

- stop owning packet assembly
- publish input-budget metadata needed by packet builders
- prefer packet manifest / payload hash as the provenance source
- keep model/provider dispatch, retries, and output artifact ownership

### `hooks/generate-overview.sh`

- stop assembling packet text directly in shell
- stop parsing config and building include patterns in shell
- stop injecting generated metadata in shell
- target removal in favor of a Python entrypoint; keep only as a thin wrapper if the path still has live callers
- call a Python packet builder that returns:
  - context file path
  - manifest path
  - estimated token size
  - payload hash

### `hooks/generate-overview-batch.sh`

- reuse the same overview packet builder as the live path
- target deletion in favor of the same Python entrypoint as live mode, unless batch submission mechanics force a temporary wrapper

## Compatibility Boundaries

Default target: zero duplicated packet builders remain in active paths.

Possible temporary live boundary:

- `review/scripts/build_plan_close_context.py` remains as a stable script path while its internals migrate to shared code.

This is acceptable because the live external contract is the script path, not the private packet logic.

Removal condition for any remaining private packet helper:

- all active callers are using the shared packet engine
- tests cover the migrated path

## Risks

### 1. Fake abstraction

If the packet engine tries to own task semantics, it will turn into a bloated universal document schema.

Mitigation:

- keep selection logic builder-specific
- keep block types small and mechanical

### 1.5. Format overreach

If overview rendering is forced into the markdown packet path, the migration will silently change model-facing prompts while pretending only mechanics changed.

Mitigation:

- keep renderer choice explicit
- gate overview migration on prompt equivalence tests

### 2. Over-shelling

If shell scripts keep owning most of the packet logic, the new core becomes decorative.

Mitigation:

- move assembly into Python for overview paths
- leave shell only for orchestration/process control

### 3. Drift between packet engine and dispatch budgets

If packet truncation is unaware of practical model limits, callers will still hand overly large packets to dispatch.

Mitigation:

- support profile-aware token budgets for model-facing builders
- replace shell `bytes/4` heuristics with a Python-owned estimator tied to dispatch profiles
- emit metric and estimate method in the manifest
- require dispatch profiles to publish the input-budget data those estimators depend on

### 3.5. Silent migration drift

If old and new builders are not compared against golden outputs, packet migrations may change prompts or review packets without anybody noticing.

Mitigation:

- golden fixture tests for plan-close packets
- exact payload-hash equivalence tests for overview live vs batch on identical inputs

### 3.75. Non-text source mishandling

If binary files, symlinks, or submodules get rendered as if they were normal text inputs, packets will silently lie about source content.

Mitigation:

- explicit non-text policy in `shared/file_specs.py`
- fixture coverage for binary, symlink, and submodule inputs

### 4. Hidden migration claims

If a builder still owns private assembly code after “migration complete,” the repo will drift again.

Mitigation:

- name remaining boundaries explicitly in the plan and closeout

## Success Criteria

1. One shared packet engine exists and is used by:
   - plan-close builder
   - model-review context assembly
   - overview builder

2. No duplicated active-path helpers remain for:
   - file-range parsing
   - constitutional preamble assembly
   - packet rendering
   - truncation markers

3. Live and batch overview generation share one packet-construction path.

4. Packet manifests make context provenance inspectable.

5. New skills can adopt packet creation without inventing another custom assembler.

6. Overview migration preserves prompt shape or proves the deliberate change with explicit tests.

7. Golden fixtures catch packet drift during migration.

8. Live and batch overview modes produce the same payload hash for identical repo inputs.

9. Active entrypoints import shared packet helpers instead of re-implementing parsing/rendering locally.

10. `shared/llm_dispatch.py` no longer owns a separate context-assembly path or parallel context hash contract.

## Recommended First Implementation Slice

Do not start by trying to generalize everything.

Start here:

1. align `shared/llm_dispatch.py` with packet-artifact handoff
2. build `shared/context_packet.py`
3. migrate `build_plan_close_context.py`
4. reuse the same file/range parsing in `model-review.py`

That is the 1/10-code proof.

If that does not materially reduce duplication and drift, stop there.
```

### review/scripts/build_plan_close_context.py

```text
#!/usr/bin/env python3
"""Build a single markdown review packet for plan-close / post-implementation review.

The packet is intentionally single-file because llmx multi-file transport has
recurring loss/truncation failures in critical review flows.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.context_packet import BudgetPolicy, CommandBlock, ContextPacket, DiffBlock, FileBlock, ListBlock, PacketSection, TextBlock
from shared.context_renderers import render_markdown, write_packet_artifact
from shared.file_specs import parse_file_spec, read_file_excerpt
from shared.git_context import collect_diff, collect_diff_stat, current_status, diff_ref, resolve_touched_files


BUILDER_VERSION = "2026-04-10-v1"


def log_progress(message: str) -> None:
    print(f"[build-plan-close-context] {message}", file=sys.stderr)


def build_scope(scope_text: str | None, scope_file: Path | None) -> str:
    if scope_file is not None:
        return scope_file.read_text().strip()
    if scope_text:
        return scope_text.strip()
    return (
        "- Target users: FILL ME\n"
        "- Scale: FILL ME\n"
        "- Rate of change: FILL ME"
    )


def build_packet_model(
    repo: Path,
    *,
    base: str | None,
    head: str | None,
    files: list[str] | None,
    tracked_only: bool,
    scope_text: str | None,
    scope_file: Path | None,
    max_diff_chars: int,
    max_file_chars: int,
    max_files: int,
) -> ContextPacket:
    log_progress("resolving touched files")
    touched = resolve_touched_files(repo, base=base, head=head, files=files, tracked_only=tracked_only)
    ref = diff_ref(base, head)

    log_progress("collecting git status")
    status_text = current_status(repo, tracked_only=tracked_only) or "(clean)"
    log_progress(f"collecting diffs for {len(touched)} touched files")
    diff_stat = collect_diff_stat(repo, ref=ref, files=touched) if touched else "(no touched files)"
    diff_text, diff_truncated = collect_diff(repo, ref=ref, files=touched, max_chars=max_diff_chars) if touched else ("(no touched files)", False)

    touched_section = PacketSection(
        "Touched Files",
        [ListBlock("Touched Files", [f"- `{path}`" for path in touched] if touched else ["- (none)"])],
    )
    git_section = PacketSection(
        "Git Status",
        [
            CommandBlock("git status --short", status_text),
            CommandBlock("git diff --stat", diff_stat),
            DiffBlock(
                "Unified Diff",
                diff_text,
                truncated=diff_truncated,
                truncation_reason="diff_char_limit" if diff_truncated else None,
            ),
        ],
    )

    display_files = touched[:max_files]
    log_progress(f"reading excerpts for {len(display_files)} files")
    file_sections_blocks = []
    for rel_path in display_files:
        spec_path = repo / rel_path
        spec = parse_file_spec(str(spec_path))
        text, truncated, omission_reason = read_file_excerpt(spec, max_chars=max_file_chars)
        metadata: dict[str, object] = {}
        if omission_reason:
            metadata["omission_reason"] = omission_reason
        block = FileBlock(
            rel_path,
            text,
            range_spec=spec.range_spec,
            truncated=truncated,
            truncation_reason="file_excerpt_limit" if truncated else None,
            original_chars=None if not truncated else len(spec_path.read_text(errors="replace")),
            metadata=metadata,
        )
        file_sections_blocks.append(block)
    omitted = len(touched) - len(display_files)
    if omitted > 0:
        file_sections_blocks.append(TextBlock("Omitted Files", f"(Omitted {omitted} additional touched files from excerpts.)"))
    files_section = PacketSection("Current File Excerpts", file_sections_blocks or [TextBlock("Current File Excerpts", "(none)")])

    return ContextPacket(
        title="Plan-Close Review Packet",
        sections=[touched_section, git_section, files_section],
        scope=build_scope(scope_text, scope_file),
        metadata={
            "Repo": str(repo),
            "Mode": "commit-range" if ref else "worktree",
            "Ref": ref or "HEAD vs current worktree",
        },
        budget_policy=BudgetPolicy(metric="chars", limit=max_diff_chars, estimate_method="heuristic:chars_div_4"),
    )


def build_packet(
    repo: Path,
    *,
    base: str | None,
    head: str | None,
    files: list[str] | None,
    tracked_only: bool,
    scope_text: str | None,
    scope_file: Path | None,
    max_diff_chars: int,
    max_file_chars: int,
    max_files: int,
) -> str:
    packet = build_packet_model(
        repo,
        base=base,
        head=head,
        files=files,
        tracked_only=tracked_only,
        scope_text=scope_text,
        scope_file=scope_file,
        max_diff_chars=max_diff_chars,
        max_file_chars=max_file_chars,
        max_files=max_files,
    )
    return render_markdown(packet)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Git repo to inspect")
    parser.add_argument("--output", type=Path, required=True, help="Markdown packet path")
    parser.add_argument("--base", help="Base git ref for commit-range review")
    parser.add_argument("--head", help="Head git ref for commit-range review")
    parser.add_argument("--file", action="append", dest="files", help="Specific file to include; may repeat")
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help=(
            "In worktree mode, limit touched files and git status to tracked changes only. "
            "Use this on dirty repos with large .scratch/ or other untracked trees."
        ),
    )
    parser.add_argument("--scope-text", help="Inline scope block for the packet")
    parser.add_argument("--scope-file", type=Path, help="File containing the scope block")
    parser.add_argument("--max-diff-chars", type=int, default=40_000)
    parser.add_argument("--max-file-chars", type=int, default=8_000)
    parser.add_argument("--max-files", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        print(f"not a git repo: {repo}", file=sys.stderr)
        return 2

    packet = build_packet_model(
        repo,
        base=args.base,
        head=args.head,
        files=args.files,
        tracked_only=args.tracked_only,
        scope_text=args.scope_text,
        scope_file=args.scope_file,
        max_diff_chars=args.max_diff_chars,
        max_file_chars=args.max_file_chars,
        max_files=args.max_files,
    )

    log_progress(f"writing packet to {args.output}")
    manifest_path = args.output.with_suffix(".manifest.json")
    write_packet_artifact(
        packet,
        renderer="markdown",
        output_path=args.output,
        manifest_path=manifest_path,
        builder_name="plan_close_context",
        builder_version=BUILDER_VERSION,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### review/scripts/test_build_plan_close_context.py

```text
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = SCRIPT_DIR / "build_plan_close_context.py"
SPEC = importlib.util.spec_from_file_location("build_plan_close_context_script", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
plan_close_context = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan_close_context)


def run(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class BuildPlanCloseContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        run(self.repo, "init")
        run(self.repo, "config", "user.name", "Test User")
        run(self.repo, "config", "user.email", "test@example.com")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolve_touched_files_uses_worktree_status(self) -> None:
        tracked = self.repo / "tracked.py"
        tracked.write_text("print('one')\n")
        run(self.repo, "add", "tracked.py")
        run(self.repo, "commit", "-m", "init")

        tracked.write_text("print('two')\n")
        untracked = self.repo / "new_file.py"
        untracked.write_text("print('new')\n")

        touched = plan_close_context.resolve_touched_files(
            self.repo,
            base=None,
            head=None,
            files=None,
            tracked_only=False,
        )

        self.assertEqual(set(touched), {"new_file.py", "tracked.py"})

    def test_resolve_touched_files_tracked_only_excludes_untracked(self) -> None:
        tracked = self.repo / "tracked.py"
        tracked.write_text("print('one')\n")
        run(self.repo, "add", "tracked.py")
        run(self.repo, "commit", "-m", "init")

        tracked.write_text("print('two')\n")
        untracked = self.repo / "new_file.py"
        untracked.write_text("print('new')\n")

        touched = plan_close_context.resolve_touched_files(
            self.repo,
            base=None,
            head=None,
            files=None,
            tracked_only=True,
        )

        self.assertEqual(touched, ["tracked.py"])

    def test_build_packet_includes_diff_and_current_excerpt(self) -> None:
        target = self.repo / "module.py"
        target.write_text("value = 1\n")
        run(self.repo, "add", "module.py")
        run(self.repo, "commit", "-m", "initial")
        base = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        target.write_text("value = 2\nprint(value)\n")
        run(self.repo, "add", "module.py")
        run(self.repo, "commit", "-m", "update")
        head = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        packet = plan_close_context.build_packet(
            self.repo,
            base=base,
            head=head,
            files=None,
            tracked_only=False,
            scope_text="- Target users: internal\n- Scale: small\n- Rate of change: high\n",
            scope_file=None,
            max_diff_chars=10_000,
            max_file_chars=10_000,
            max_files=10,
        )

        self.assertIn("# Plan-Close Review Packet", packet)
        self.assertIn("## Scope", packet)
        self.assertIn("- `module.py`", packet)
        self.assertIn("value = 1", packet)
        self.assertIn("value = 2", packet)
        self.assertIn("print(value)", packet)


if __name__ == "__main__":
    unittest.main()
```

### review/scripts/model-review.py

```text
#!/usr/bin/env python3
"""Model-review dispatch — context assembly + parallel llmx dispatch + output collection.

Replaces the 10-tool-call manual ceremony in the model-review skill with one script call.
Agent provides context + topic + question; script handles plumbing; agent reads outputs.

Usage:
    # Standard review (2 queries: arch + formal)
    model-review.py --context plan.md --topic "hook architecture" "Review for gaps"

    # Simple review (1 query: combined)
    model-review.py --context plan.md --topic "config tweak" --axes simple "Review this change"

    # Deep review (4 queries: arch + formal + domain + mechanical)
    model-review.py --context plan.md --topic "classification logic" --axes arch,formal,domain,mechanical "Review this"

    # With project dir for constitution discovery
    model-review.py --context plan.md --topic "data wiring" --project ~/Projects/intel "Review this plan"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import shared.llm_dispatch as dispatch_core
from shared.context_packet import BudgetPolicy, ContextPacket, FileBlock, PacketSection, TextBlock
from shared.context_preamble import build_review_preamble_blocks, find_constitution as shared_find_constitution
from shared.context_renderers import write_packet_artifact
from shared.file_specs import parse_file_spec, read_file_excerpt

# --- Structured output schema (both models return this) ---

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["bug", "logic", "architecture", "missing", "performance", "security", "style", "constitutional"],
                    },
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "title": {"type": "string", "description": "One-line summary"},
                    "description": {"type": "string", "description": "Detailed explanation with evidence"},
                    "file": {"type": "string", "description": "File path if cited, empty if architectural"},
                    "line": {"type": "integer", "description": "Line number if cited, 0 if N/A"},
                    "fix": {"type": "string", "description": "Proposed fix, empty if unclear"},
                    "confidence": {"type": "number", "description": "0.0-1.0 confidence in this finding"},
                },
                "required": ["category", "severity", "title", "description", "file", "line", "fix", "confidence"],
            },
        },
    },
    "required": ["findings"],
}

# --- Axis definitions: model + prompt + api kwargs ---

AXES = {
    "arch": {
        "label": "Gemini (architecture/patterns)",
        "profile": "deep_review",
        "prompt": """\
<system>
You are reviewing a codebase. Be concrete. No platitudes. Reference specific code, configs, and findings. It is {date}.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Assessment of Strengths and Weaknesses
What holds up and what doesn't. Reference actual code/config. Be specific about errors AND what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
{constitution_instruction}

## 6. Blind Spots In My Own Analysis
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?""",
    },
    "formal": {
        "label": "GPT-5.4 (quantitative/formal)",
        "profile": "formal_review",
        "prompt": """\
<system>
You are performing QUANTITATIVE and FORMAL analysis. Other reviewers handle qualitative pattern review. Focus on what they can't do well. Be precise. Show your reasoning. No hand-waving.
Budget: ~2000 words. Tables over prose. Source-grade claims.
</system>

{question}

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: expected impact, maintenance burden, composability, risk. Rank by value adjusted for ongoing cost. Creation effort is irrelevant (agents build everything). Only ongoing drag matters: maintenance, supervision, complexity budget.

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Constitutional Alignment (Quantified)
{constitution_instruction}

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.4) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.""",
    },
    "domain": {
        "label": "Gemini Pro (domain correctness)",
        "profile": "deep_review",
        "prompt": """\
<system>
You are verifying DOMAIN-SPECIFIC CLAIMS in this plan. Other reviewers handle architecture and formal logic.
Focus exclusively on: are the domain facts correc

... [truncated for review packet] ...

LLUCINATED")
    unverifiable = sum(1 for v in verified if v["verdict"] == "UNVERIFIABLE")

    # Write verified disposition
    out_path = review_dir / "verified-disposition.md"
    lines_out = [
        f"# Verified Disposition — {date.today().isoformat()}\n",
        f"**Claims:** {len(verified)} total — "
        f"{confirmed} CONFIRMED, {hallucinated} HALLUCINATED, {unverifiable} UNVERIFIABLE\n",
    ]
    if hallucinated > 0:
        rate = round(hallucinated / len(verified) * 100)
        lines_out.append(f"**Hallucination rate:** {rate}%\n")
    lines_out.append("")
    lines_out.append("| # | Verdict | Claim | Notes |")
    lines_out.append("|---|---------|-------|-------|")
    for v in verified:
        claim_short = v["text"][:80] + ("..." if len(v["text"]) > 80 else "")
        lines_out.append(f"| {v['num']} | {v['verdict']} | {claim_short} | {v.get('notes', '')} |")
    lines_out.append("")

    out_path.write_text("\n".join(lines_out) + "\n")
    print(
        f"Verification: {confirmed} confirmed, {hallucinated} hallucinated, "
        f"{unverifiable} unverifiable ({len(verified)} total)",
        file=sys.stderr,
    )
    return str(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Model-review dispatch: context assembly + parallel llmx + output collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Presets: {', '.join(PRESETS.keys())}. Axes: {', '.join(AXES.keys())}.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--context", type=Path, help="Context file for narrow review")
    group.add_argument(
        "--context-files", nargs="+", metavar="FILE_SPEC",
        help="Auto-assemble context from file:range specs (e.g., plan.md scripts/ir.py:86-110)",
    )
    parser.add_argument("--topic", required=True, help="Short topic label (used in output dir name)")
    parser.add_argument("--project", type=Path, help="Project dir for constitution discovery (default: cwd)")
    parser.add_argument(
        "--axes", default="standard",
        help="Comma-separated axes or preset name (simple, standard, deep, full). Default: standard",
    )
    parser.add_argument(
        "--extract", action="store_true",
        help="After dispatch, auto-extract claims from each output into disposition.md",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="After extraction, verify cited files/symbols exist. Implies --extract.",
    )
    parser.add_argument(
        "--questions", type=Path,
        help="JSON file mapping axis names to custom questions (overrides positional question per-axis)",
    )
    parser.add_argument(
        "question", nargs="?",
        default="Review this for logical gaps, missed edge cases, and constitutional alignment.",
        help="Review question for all models",
    )

    args = parser.parse_args()

    project_dir = args.project or Path.cwd()
    if not project_dir.is_dir():
        print(f"error: project dir {project_dir} not found", file=sys.stderr)
        return 1

    if args.context and not args.context.exists():
        print(f"error: context file {args.context} not found", file=sys.stderr)
        return 1

    # Resolve axes
    if args.axes in PRESETS:
        axis_names = PRESETS[args.axes]
    else:
        axis_names = [a.strip() for a in args.axes.split(",")]
        for a in axis_names:
            if a not in AXES:
                print(f"error: unknown axis '{a}'. Available: {', '.join(AXES.keys())}", file=sys.stderr)
                return 1

    print(f"Dispatching {len(axis_names)} queries: {', '.join(axis_names)}", file=sys.stderr)

    # Create output directory
    slug = slugify(args.topic)
    hex_id = os.urandom(3).hex()
    review_dir = Path(f".model-review/{date.today().isoformat()}-{slug}-{hex_id}")
    review_dir.mkdir(parents=True, exist_ok=True)

    # Assemble context
    ctx_files = build_context(
        review_dir, project_dir, args.context, axis_names,
        context_file_specs=args.context_files,
    )

    constitution, _ = find_constitution(project_dir)

    # Load per-axis question overrides
    question_overrides = None
    if args.questions:
        if not args.questions.exists():
            print(f"error: questions file {args.questions} not found", file=sys.stderr)
            return 1
        question_overrides = json.loads(args.questions.read_text())

    # Dispatch and wait
    result = dispatch(review_dir, ctx_files, axis_names, args.question, bool(constitution), question_overrides)
    failures = collect_dispatch_failures(result, ctx_files)
    if failures:
        failure_path = review_dir / "dispatch-failures.json"
        failure_path.write_text(json.dumps({"failures": failures}, indent=2) + "\n")
        result["dispatch_failures"] = str(failure_path)
        result["failed_axes"] = [failure["axis"] for failure in failures]
        print(
            f"error: model-review dispatch produced unusable outputs for "
            f"{', '.join(result['failed_axes'])}; see {failure_path}",
            file=sys.stderr,
        )
        print(json.dumps(result, indent=2))
        return 2

    # --verify implies --extract
    do_extract = args.extract or args.verify

    # Optional extraction phase
    if do_extract:
        disposition_path = extract_claims(review_dir, result)
        if disposition_path:
            result["disposition"] = disposition_path
            print(f"Disposition written to {disposition_path}", file=sys.stderr)

            # Optional verification phase
            if args.verify:
                verified_path = verify_claims(review_dir, disposition_path, project_dir)
                result["verified_disposition"] = verified_path
                print(f"Verified disposition written to {verified_path}", file=sys.stderr)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### review/scripts/test_model_review.py

```text
from __future__ import annotations

import importlib.util
import contextlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_REVIEW_PATH = SCRIPT_DIR / "model-review.py"
SPEC = importlib.util.spec_from_file_location("model_review_script", MODEL_REVIEW_PATH)
assert SPEC is not None and SPEC.loader is not None
model_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model_review)


@contextlib.contextmanager
def patched_llmx_chat(mock_chat):
    with patch.object(model_review.dispatch_core, "_LLMX_CHAT", mock_chat), patch.object(
        model_review.dispatch_core, "_LLMX_VERSION", "test"
    ):
        yield


class ModelReviewDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.review_dir = Path(self.temp_dir.name)
        self.ctx_files = {}
        for axis in ("arch", "formal", "domain"):
            ctx = self.review_dir / f"{axis}-context.md"
            ctx.write_text("context")
            self.ctx_files[axis] = ctx

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_dispatch_calls_both_models_and_writes_output(self) -> None:
        call_log: list[dict] = []

        def mock_chat(**kwargs):
            call_log.append(kwargs)
            resp = MagicMock()
            resp.content = f"output for {kwargs.get('model', '?')}"
            resp.latency = 1.0
            return resp

        with patched_llmx_chat(mock_chat):
            result = model_review.dispatch(
                self.review_dir,
                self.ctx_files,
                ["arch", "formal"],
                "Review this",
                has_constitution=False,
            )

        self.assertEqual(result["arch"]["exit_code"], 0)
        self.assertGreater(result["arch"]["size"], 0)
        self.assertEqual(result["formal"]["exit_code"], 0)
        self.assertGreater(result["formal"]["size"], 0)
        # Both models called
        models_called = {c["model"] for c in call_log}
        self.assertIn("gemini-3.1-pro-preview", models_called)
        self.assertIn("gpt-5.4", models_called)

    def test_dispatch_falls_back_after_gemini_rate_limit(self) -> None:
        call_count = {"arch": 0}

        def mock_chat(**kwargs):
            model = kwargs.get("model", "")
            if model == model_review.GEMINI_PRO_MODEL and call_count["arch"] == 0:
                call_count["arch"] += 1
                raise Exception("503 resource_exhausted")
            if model == model_review.GEMINI_FLASH_MODEL:
                resp = MagicMock()
                resp.content = "flash fallback"
                resp.latency = 0.5
                return resp
            resp = MagicMock()
            resp.content = "ok"
            resp.latency = 1.0
            return resp

        with patched_llmx_chat(mock_chat):
            result = model_review.dispatch(
                self.review_dir,
                self.ctx_files,
                ["arch", "formal"],
                "Review this",
                has_constitution=False,
            )

        # arch should have fallen back to Flash
        self.assertEqual(result["arch"]["model"], model_review.GEMINI_FLASH_MODEL)
        self.assertEqual(result["arch"]["fallback_reason"], "gemini_rate_limit")
        self.assertGreater(result["arch"]["size"], 0)
        # formal should succeed normally
        self.assertEqual(result["formal"]["exit_code"], 0)

    def test_collect_dispatch_failures_flags_zero_byte_outputs(self) -> None:
        dispatch_result = {
            "review_dir": str(self.review_dir),
            "axes": ["formal"],
            "queries": 1,
            "elapsed_seconds": 1.0,
            "formal": {
                "label": "Formal",
                "model": "gpt-5.4",
                "requested_model": "gpt-5.4",
                "exit_code": 0,
                "size": 0,
                "output": str(self.review_dir / "formal-output.md"),
                "stderr": "[llmx:WARN] 0-byte output",
            },
        }
        failures = model_review.collect_dispatch_failures(dispatch_result, self.ctx_files)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["axis"], "formal")
        self.assertEqual(failures[0]["failure_reason"], "empty_output")

    def test_fingerprint_merge_detects_similar_findings(self) -> None:
        """The Jaccard keyword merge should detect findings about the same issue."""
        f1 = {"title": "Missing null check in parse_config", "file": "config.py",
               "description": "parse_config does not handle None input", "confidence": 0.8,
               "category": "bug", "severity": "high", "fix": "add guard", "line": 0}
        f2 = {"title": "parse_config crashes on null input", "file": "config.py",
               "description": "Null input causes AttributeError in parse_config", "confidence": 0.7,
               "category": "bug", "severity": "high", "fix": "validate input", "line": 0}
        # Simulate what extract_claims merge does
        import re
        def _fp(f):
            text = f"{f.get('title', '')} {f.get('file', '')} {f.get('description', '')[:200]}"
            words = set(re.findall(r"[a-z_]{4,}", text.lower()))
            words -= {"this", "that", "with", "from", "should", "could", "would", "does", "have", "will", "also", "been"}
            return words

        fp1, fp2 = _fp(f1), _fp(f2)
        jaccard = len(fp1 & fp2) / len(fp1 | fp2)
        self.assertGreater(jaccard, 0.3, f"Expected Jaccard > 0.3, got {jaccard:.2f}")


class SchemaTransformTest(unittest.TestCase):
    def test_add_additional_properties_to_nested_objects(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "object", "prope

... [truncated for review packet] ...

       }
        result = model_review._add_additional_properties(schema)
        self.assertFalse(result["additionalProperties"])
        self.assertFalse(result["properties"]["items"]["items"]["additionalProperties"])
        # Original not mutated
        self.assertNotIn("additionalProperties", schema)

    def test_strip_additional_properties_from_nested_objects(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": False, "properties": {}},
                }
            },
        }
        result = model_review._strip_additional_properties(schema)
        self.assertNotIn("additionalProperties", result)
        self.assertNotIn("additionalProperties", result["properties"]["items"]["items"])
        # Original not mutated
        self.assertIn("additionalProperties", schema)

    def test_finding_schema_roundtrips_both_providers(self) -> None:
        """The canonical FINDING_SCHEMA should be valid after both transforms."""
        oai = model_review._add_additional_properties(model_review.FINDING_SCHEMA)
        self.assertFalse(oai["additionalProperties"])
        self.assertFalse(oai["properties"]["findings"]["items"]["additionalProperties"])

        google = model_review._strip_additional_properties(model_review.FINDING_SCHEMA)
        self.assertNotIn("additionalProperties", google)


class CallLlmxTest(unittest.TestCase):
    def test_call_llmx_returns_error_dict_on_exception(self) -> None:
        def exploding_chat(**kwargs):
            raise ConnectionError("network down")

        with tempfile.TemporaryDirectory() as td:
            ctx = Path(td) / "ctx.md"
            ctx.write_text("context")
            out = Path(td) / "out.md"
            with patched_llmx_chat(exploding_chat):
                result = model_review._call_llmx(
                    provider="google", model="gemini-3.1-pro-preview",
                    context_path=ctx, prompt="test", output_path=out,
                    timeout=10,
                )
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["size"], 0)
        self.assertIn("network down", result["error"])

    def test_call_llmx_passes_schema_for_openai(self) -> None:
        captured = {}
        def capture_chat(**kwargs):
            captured.update(kwargs)
            resp = MagicMock()
            resp.content = "ok"
            resp.latency = 0.1
            return resp

        with tempfile.TemporaryDirectory() as td:
            ctx = Path(td) / "ctx.md"
            ctx.write_text("context")
            out = Path(td) / "out.md"
            with patched_llmx_chat(capture_chat):
                model_review._call_llmx(
                    provider="openai", model="gpt-5.4",
                    context_path=ctx, prompt="test", output_path=out,
                    schema=model_review.FINDING_SCHEMA, timeout=10,
                )
        # Should have additionalProperties added for OpenAI
        fmt = captured.get("response_format", {})
        self.assertIn("additionalProperties", str(fmt))

    def test_call_llmx_strips_schema_for_google(self) -> None:
        captured = {}
        def capture_chat(**kwargs):
            captured.update(kwargs)
            resp = MagicMock()
            resp.content = "ok"
            resp.latency = 0.1
            return resp

        with tempfile.TemporaryDirectory() as td:
            ctx = Path(td) / "ctx.md"
            ctx.write_text("context")
            out = Path(td) / "out.md"
            with patched_llmx_chat(capture_chat):
                model_review._call_llmx(
                    provider="google", model="gemini-3.1-pro-preview",
                    context_path=ctx, prompt="test", output_path=out,
                    schema={"type": "object", "additionalProperties": False, "properties": {}},
                    timeout=10,
                )
        fmt = captured.get("response_format", {})
        self.assertNotIn("additionalProperties", str(fmt))


class ModelReviewMainTest(unittest.TestCase):
    def test_main_returns_nonzero_when_axis_output_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")

            dispatch_result = {
                "review_dir": str(project_dir / ".model-review" / "test"),
                "axes": ["formal"],
                "queries": 1,
                "elapsed_seconds": 1.0,
                "formal": {
                    "label": "Formal",
                    "model": "gpt-5.4",
                    "requested_model": "gpt-5.4",
                    "exit_code": 0,
                    "size": 0,
                    "output": str(project_dir / "formal-output.md"),
                    "stderr": "0-byte output",
                },
            }

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review, "build_context", return_value={"formal": project_dir / "ctx.md"}), \
                     patch.object(model_review, "dispatch", return_value=dispatch_result), \
                     patch.object(model_review, "find_constitution", return_value=("", None)), \
                     patch.object(model_review.os, "urandom", return_value=b"\xab\xcd\x12"), \
                     patch.object(model_review.sys, "argv", [
                         "model-review.py", "--context", str(context_path),
                         "--topic", "empty-axis", "--project", str(project_dir),
                     ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
```

### scripts/generate_overview.py

```text
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.context_packet import BudgetPolicy, ContextPacket, PacketSection, TextBlock, atomic_write_text
from shared.context_renderers import write_packet_artifact
from shared.git_context import run_git
from shared.llm_dispatch import DispatchProfile, dispatch, map_model_to_profile, profile_input_budget, PROFILES
from shared.overview_config import OverviewConfig, read_overview_config
from shared.repomix_source import build_include_pattern, capture_repomix_to_file


BUILDER_VERSION = "2026-04-10-v1"
DEFAULT_PROJECTS = ("meta", "intel", "selve", "genomics")


@dataclass(frozen=True)
class OverviewPayload:
    overview_type: str
    profile_name: str
    profile: DispatchProfile
    project_root: Path
    output_file: Path
    payload_path: Path
    manifest_path: Path
    token_estimate: int | None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_project_root(project_root: str | None) -> Path:
    if project_root:
        return Path(project_root).expanduser().resolve()
    try:
        return Path(run_git(Path.cwd(), ["rev-parse", "--show-toplevel"]).strip())
    except Exception:
        return Path.cwd().resolve()


def current_commit_hash(project_root: Path) -> str:
    try:
        return run_git(project_root, ["rev-parse", "HEAD"]).strip()
    except Exception:
        return "unknown"


def resolve_dispatch_profile(config: OverviewConfig) -> str:
    return map_model_to_profile(config.model)


def build_overview_packet(
    project_root: Path,
    config: OverviewConfig,
    overview_type: str,
    *,
    profile_name: str,
    output_dir: Path,
) -> OverviewPayload:
    prompt_file = config.prompt_file(overview_type)
    if not prompt_file.exists():
        raise FileNotFoundError(f"prompt template not found: {prompt_file}")

    dirs = config.dirs_by_type.get(overview_type) or []
    if not dirs:
        raise ValueError(f"no directories configured for type '{overview_type}'")

    output_dir.mkdir(parents=True, exist_ok=True)
    include_pattern = build_include_pattern(dirs)
    repomix_output = output_dir / f".overview-{overview_type}-codebase.txt"
    capture_repomix_to_file(
        project_root=project_root,
        include_pattern=include_pattern,
        exclude=config.exclude,
        no_gitignore=config.no_gitignore,
        output_path=repomix_output,
    )

    budget = profile_input_budget(profile_name)
    packet = ContextPacket(
        title=f"{overview_type} overview payload",
        sections=[
            PacketSection(
                "Instructions",
                [TextBlock("instructions", prompt_file.read_text())],
                tag="instructions",
            ),
            PacketSection(
                "Codebase",
                [TextBlock("codebase", repomix_output.read_text())],
                tag="codebase",
            ),
        ],
        metadata={
            "project_root": str(project_root),
            "overview_type": overview_type,
            "trailing_text": "Write the requested codebase overview in markdown.",
        },
        budget_policy=BudgetPolicy(
            metric="tokens",
            limit=budget["input_token_limit"] or 120000,
            estimate_method=budget["input_token_estimator"],
        ),
    )
    payload_path = output_dir / f".overview-{overview_type}-payload.txt"
    manifest_path = output_dir / f".overview-{overview_type}-payload.manifest.json"
    artifact = write_packet_artifact(
        packet,
        renderer="tagged",
        output_path=payload_path,
        manifest_path=manifest_path,
        builder_name="overview_payload",
        builder_version=BUILDER_VERSION,
    )
    profile = PROFILES[profile_name]
    return OverviewPayload(
        overview_type=overview_type,
        profile_name=profile_name,
        profile=profile,
        project_root=project_root,
        output_file=config.output_file(overview_type),
        payload_path=payload_path,
        manifest_path=manifest_path,
        token_estimate=artifact.token_estimate,
    )


def metadata_line(*, commit_hash: str, profile_name: str, model: str) -> str:
    return (
        f"<!-- Generated: {utc_now()} | git: {commit_hash[:7]} | "
        f"profile: {profile_name} | model: {model} -->"
    )


def write_overview_output(
    *,
    output_file: Path,
    markdown_body: str,
    commit_hash: str,
    profile_name: str,
    model: str,
) -> None:
    rendered = metadata_line(commit_hash=commit_hash, profile_name=profile_name, model=model) + "\n\n" + markdown_body.rstrip() + "\n"
    atomic_write_text(output_file, rendered)


def write_marker(project_root: Path, overview_type: str, commit_hash: str) -> None:
    marker = project_root / ".claude" / f"overview-marker-{overview_type}"
    marker.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(marker, commit_hash + "\n")


def generate_one(
    *,
    project_root: Path,
    config: OverviewConfig,
    overview_type: str,
    commit_hash: str,
    dry_run: bool,
) -> int:
    profile_name = resolve_dispatch_profile(config)
    prompt_file = config.prompt_file(overview_type)
    dirs = config.dirs_by_type.get(overview_type) or []
    output_file = config.output_file(overview_type)

    if dry_run:
        print(f"[dry-run] {overview_type}")
        print(f"  output: {output_file}")
        print(f"  profile: {profile_name}")
        print(f"  model: {PROFILES[profile_name].model}")
        print(f"  prompt: {prompt_file}")
        print(f"  dirs: {', '.join(dirs)}")
        return 0

    payload = build_overview_packet(

... [truncated for review packet] ...

utput_dir=work_dir / project,
                )
                key = f"{project}-{overview_type}"
                json.dump({"key": key, "prompt": payload.payload_path.read_text()}, jsonl_handle)
                jsonl_handle.write("\n")
                manifest_entries.append(
                    {
                        "key": key,
                        "project": project,
                        "project_root": str(project_root),
                        "type": overview_type,
                        "output": str(payload.output_file),
                        "profile": payload.profile_name,
                        "model": payload.profile.model,
                        "commit_hash": commit_hash,
                    }
                )
                count += 1

    manifest_path.write_text(json.dumps(manifest_entries, indent=2) + "\n")
    return count, jsonl_file, manifest_path


def distribute_results(results_file: Path, manifest_path: Path) -> int:
    manifest = {entry["key"]: entry for entry in json.loads(manifest_path.read_text())}
    distributed = 0
    for line in results_file.read_text().splitlines():
        if not line.strip():
            continue
        result = json.loads(line)
        key = result.get("key")
        if key not in manifest:
            print(f"WARN: no manifest entry for {key}", file=sys.stderr)
            continue
        entry = manifest[key]
        content = result.get("content") or ""
        if not content:
            print(f"ERROR: empty batch result for {key}", file=sys.stderr)
            continue
        output_file = Path(entry["output"])
        write_overview_output(
            output_file=output_file,
            markdown_body=content,
            commit_hash=str(entry["commit_hash"]),
            profile_name=str(entry["profile"]),
            model=str(result.get("model") or entry["model"]),
        )
        write_marker(Path(entry["project_root"]), str(entry["type"]), str(entry["commit_hash"]))
        distributed += 1
    return distributed


def batch_mode(args: argparse.Namespace) -> int:
    projects = list(DEFAULT_PROJECTS)
    with TemporaryDirectory(prefix="overview-batch-") as temp_dir:
        work_dir = Path(temp_dir)
        if args.mode == "get":
            manifest_path = Path(f"/tmp/overview-batch-manifest-{args.job_name.replace('/', '-')}.json")
            if not manifest_path.exists():
                print(f"Error: manifest not found at {manifest_path}", file=sys.stderr)
                return 1
            results_file = work_dir / "results.jsonl"
            llmx_root = Path.home() / "Projects" / "llmx"
            proc = subprocess.run(
                batch_get_command(args.job_name, output_file=results_file),
                cwd=llmx_root,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                print(proc.stderr, file=sys.stderr)
                return 1
            distributed = distribute_results(results_file, manifest_path)
            print(f"Distributed {distributed} overviews", file=sys.stderr)
            return 0

        count, jsonl_file, manifest_path = build_batch_requests(work_dir, projects)
        if count == 0:
            print("No overviews to generate", file=sys.stderr)
            return 0
        if args.mode == "dry-run":
            print(f"Would submit {count} overview requests from {jsonl_file}")
            return 0

        llmx_root = Path.home() / "Projects" / "llmx"
        results_file = work_dir / "results.jsonl"
        proc = subprocess.run(
            batch_submit_command(jsonl_file, wait=args.mode == "submit-wait", output_file=results_file if args.mode == "submit-wait" else None),
            cwd=llmx_root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            return 1

        submitted_job = None
        for line in proc.stdout.splitlines() + proc.stderr.splitlines():
            if line.startswith("Submitted:"):
                submitted_job = line.split(":", 1)[1].strip()
                break

        if submitted_job:
            saved_manifest = Path(f"/tmp/overview-batch-manifest-{submitted_job.replace('/', '-')}.json")
            shutil.copy2(manifest_path, saved_manifest)
            print(f"Manifest: {saved_manifest}")
            print(f"Job: {submitted_job}")

        if args.mode == "submit-only":
            return 0

        if not results_file.exists():
            print("Batch job completed without results file", file=sys.stderr)
            return 1
        distributed = distribute_results(results_file, manifest_path)
        print(f"Distributed {distributed} overviews", file=sys.stderr)
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Overview generation entrypoint")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    live = subparsers.add_parser("live")
    live.add_argument("--type")
    live.add_argument("--auto", action="store_true")
    live.add_argument("--dry-run", action="store_true")
    live.add_argument("--project-root")
    live.add_argument("--commit-hash")

    batch = subparsers.add_parser("batch")
    mode_group = batch.add_mutually_exclusive_group()
    mode_group.add_argument("--submit-only", action="store_true")
    mode_group.add_argument("--get", dest="job_name")
    mode_group.add_argument("--dry-run", action="store_true")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.subcommand == "live":
        return live_mode(args)
    args.mode = "submit-wait"
    if args.submit_only:
        args.mode = "submit-only"
    elif args.job_name:
        args.mode = "get"
    elif args.dry_run:
        args.mode = "dry-run"
    return batch_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

### scripts/test_generate_overview.py

```text
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.generate_overview as generate_overview


class GenerateOverviewTest(unittest.TestCase):
    def test_build_overview_packet_creates_payload_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / ".claude" / "overview.conf").write_text(
                "\n".join(
                    [
                        "OVERVIEW_TYPES=source",
                        "OVERVIEW_PROMPT_DIR=.claude/prompts",
                        "OVERVIEW_OUTPUT_DIR=.claude/overviews",
                        "OVERVIEW_SOURCE_DIRS=src/",
                    ]
                )
            )
            (root / ".claude" / "prompts").mkdir(parents=True)
            (root / ".claude" / "prompts" / "source.md").write_text("Summarize the source.")
            (root / "src").mkdir()
            config = generate_overview.read_overview_config(root)

            def fake_repomix(**kwargs):
                kwargs["output_path"].write_text("CODEBASE")

            with patch.object(generate_overview, "capture_repomix_to_file", fake_repomix):
                payload = generate_overview.build_overview_packet(
                    root,
                    config,
                    "source",
                    profile_name="fast_extract",
                    output_dir=root / ".claude" / "overviews",
                )

            self.assertTrue(payload.payload_path.exists())
            self.assertTrue(payload.manifest_path.exists())
            text = payload.payload_path.read_text()
            self.assertIn("<instructions>", text)
            self.assertIn("<codebase>", text)
            self.assertIn("Write the requested codebase overview in markdown.", text)


if __name__ == "__main__":
    unittest.main()
```

### shared/context_packet.py

```text
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal


NORMALIZATION_VERSION = "v1"
DEFAULT_TOKEN_ESTIMATOR = "heuristic:chars_div_4"


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_text(text: str) -> str:
    normalized = normalize_newlines(text)
    return normalized if normalized.endswith("\n") else normalized + "\n"


def normalize_path(value: str | Path) -> str:
    return Path(value).as_posix()


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def estimate_tokens(text: str, method: str = DEFAULT_TOKEN_ESTIMATOR) -> int:
    normalized = normalize_text(text)
    if method == "heuristic:chars_div_4":
        return max(1, len(normalized) // 4)
    raise ValueError(f"unsupported token estimate method '{method}'")


@dataclass(frozen=True)
class TruncationEvent:
    block_label: str
    reason: str
    original_chars: int
    rendered_chars: int


@dataclass(frozen=True)
class BudgetPolicy:
    metric: Literal["chars", "tokens"]
    limit: int
    estimate_method: str = DEFAULT_TOKEN_ESTIMATOR


@dataclass(frozen=True)
class PacketBlock:
    title: str
    text: str
    block_type: str
    truncatable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    truncated: bool = False
    truncation_reason: str | None = None
    original_chars: int | None = None

    def rendered_chars(self) -> int:
        return len(normalize_text(self.text))

    def block_hash(self) -> str:
        return sha256_text(self.text)

    def source_path(self) -> str | None:
        path_value = self.metadata.get("path")
        if path_value is None:
            return None
        return normalize_path(path_value)

    def truncation_event(self) -> TruncationEvent | None:
        if not self.truncated:
            return None
        return TruncationEvent(
            block_label=self.title,
            reason=self.truncation_reason or "truncated",
            original_chars=self.original_chars or self.rendered_chars(),
            rendered_chars=self.rendered_chars(),
        )


def TextBlock(title: str, text: str, **kwargs: Any) -> PacketBlock:
    return PacketBlock(title=title, text=text, block_type="text", **kwargs)


def PreambleBlock(title: str, text: str, **kwargs: Any) -> PacketBlock:
    return PacketBlock(title=title, text=text, block_type="preamble", truncatable=False, **kwargs)


def FileBlock(path: str | Path, text: str, *, range_spec: str | None = None, **kwargs: Any) -> PacketBlock:
    metadata = dict(kwargs.pop("metadata", {}))
    metadata["path"] = normalize_path(path)
    if range_spec:
        metadata["range_spec"] = range_spec
    return PacketBlock(title=metadata["path"], text=text, block_type="file", metadata=metadata, **kwargs)


def DiffBlock(label: str, diff_text: str, **kwargs: Any) -> PacketBlock:
    return PacketBlock(title=label, text=diff_text, block_type="diff", **kwargs)


def CommandBlock(command: str, output_text: str, **kwargs: Any) -> PacketBlock:
    metadata = dict(kwargs.pop("metadata", {}))
    metadata["command"] = command
    return PacketBlock(title=command, text=output_text, block_type="command", metadata=metadata, **kwargs)


def ListBlock(title: str, items: list[str], **kwargs: Any) -> PacketBlock:
    return PacketBlock(title=title, text="\n".join(items), block_type="list", **kwargs)


@dataclass(frozen=True)
class PacketSection:
    title: str
    blocks: list[PacketBlock]
    tag: str | None = None


@dataclass(frozen=True)
class ContextPacket:
    title: str
    sections: list[PacketSection]
    scope: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    budget_policy: BudgetPolicy | None = None


@dataclass(frozen=True)
class BuildArtifact:
    content_path: Path
    manifest_path: Path
    content_hash: str
    payload_hash: str
    rendered_bytes: int
    token_estimate: int | None
    estimate_method: str
    budget_metric: str
    truncated: bool


def build_manifest(
    packet: ContextPacket,
    *,
    rendered_content: str,
    builder_name: str,
    builder_version: str,
    created_at: str,
    estimate_method: str,
    budget_metric: str,
) -> dict[str, Any]:
    truncation_events = [
        asdict(event)
        for section in packet.sections
        for block in section.blocks
        for event in [block.truncation_event()]
        if event is not None
    ]
    source_blocks: list[dict[str, Any]] = []
    source_paths: list[str] = []
    for section_index, section in enumerate(packet.sections):
        for block_index, block in enumerate(section.blocks):
            source_path = block.source_path()
            if source_path and source_path not in source_paths:
                source_paths.append(source_path)
            source_blocks.append(
                {
                    "section_index": section_index,
                    "section_title": section.title,
                    "block_index": block_index,
                    "block_title": block.title,
                    "block_type": block.block_type,
                    "block_hash": block.block_hash(),
                    "source_path": source_path,
                    "metadata": block.metadata,
                    "truncated": block.truncated,
                }
            )

    normalized_content = normalize_text(rendered_content)
    token_estimate = estimate_tokens(normalized_content, estimate_method)
    budget_limit = packet.budget_policy.limit if packet.budget_policy else None

    return {
        "packet_title": packet.title,
        "builder_name": builder_name,
        "builder_version": builder_version,
        "created_at": created_at,
        "normalization_version": NORMALIZATION_VERSION,
        "source_blocks": source_blocks,
        "source_paths": source_paths,
        "rendered_content_hash": sha256_text(normalized_content),
        "payload_hash": sha256_text(normalized_content),
        "rendered_bytes": len(normalized_content.encode("utf-8")),
        "token_estimate": token_estimate,
        "estimate_method": estimate_method,
        "budget_metric": budget_metric,
        "budget_limit": budget_limit,
        "truncation_events": truncation_events,
        "packet_metadata": packet.metadata,
    }
```

### shared/context_renderers.py

```text
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from shared.context_packet import (
    BuildArtifact,
    ContextPacket,
    PacketBlock,
    PacketSection,
    atomic_write_json,
    atomic_write_text,
    build_manifest,
    estimate_tokens,
    normalize_text,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _render_block_markdown(block: PacketBlock) -> list[str]:
    lines: list[str] = []
    if block.block_type == "preamble":
        lines.extend([f"## {block.title}", "", block.text.strip(), ""])
        return lines
    if block.block_type == "list":
        lines.extend([f"### {block.title}", ""])
        lines.extend(block.text.splitlines() or [""])
        lines.append("")
        return lines

    fence = "text"
    if block.block_type == "diff":
        fence = "diff"
    lines.extend([f"### {block.title}", "", f"```{fence}", block.text.rstrip(), "```", ""])
    return lines


def render_markdown(packet: ContextPacket) -> str:
    lines = [f"# {packet.title}", ""]
    if packet.metadata:
        for key, value in packet.metadata.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    if packet.scope:
        lines.extend(["## Scope", "", packet.scope.strip(), ""])
    for section in packet.sections:
        lines.extend([f"## {section.title}", ""])
        for block in section.blocks:
            lines.extend(_render_block_markdown(block))
    return normalize_text("\n".join(lines).rstrip("\n"))


def render_tagged_prompt(packet: ContextPacket) -> str:
    rendered_sections: list[str] = []
    for section in packet.sections:
        tag = section.tag or section.title.lower().replace(" ", "_")
        body_parts = []
        for block in section.blocks:
            body_parts.append(block.text.rstrip())
        body_text = "\n\n".join(part for part in body_parts if part)
        rendered_sections.append(f"<{tag}>\n{body_text}\n</{tag}>")
    trailer = str(packet.metadata.get("trailing_text", "")).strip()
    body = "\n\n".join(rendered_sections)
    if trailer:
        body = f"{body}\n\n{trailer}"
    return normalize_text(body)


def write_packet_artifact(
    packet: ContextPacket,
    *,
    renderer: str,
    output_path: Path,
    manifest_path: Path,
    builder_name: str,
    builder_version: str,
) -> BuildArtifact:
    if renderer == "markdown":
        rendered_content = render_markdown(packet)
    elif renderer == "tagged":
        rendered_content = render_tagged_prompt(packet)
    else:
        raise ValueError(f"unsupported renderer '{renderer}'")

    estimate_method = packet.budget_policy.estimate_method if packet.budget_policy else "heuristic:chars_div_4"
    budget_metric = packet.budget_policy.metric if packet.budget_policy else "tokens"
    manifest = build_manifest(
        packet,
        rendered_content=rendered_content,
        builder_name=builder_name,
        builder_version=builder_version,
        created_at=_utc_now(),
        estimate_method=estimate_method,
        budget_metric=budget_metric,
    )
    atomic_write_text(output_path, rendered_content)
    atomic_write_json(manifest_path, manifest)
    return BuildArtifact(
        content_path=output_path,
        manifest_path=manifest_path,
        content_hash=manifest["rendered_content_hash"],
        payload_hash=manifest["payload_hash"],
        rendered_bytes=manifest["rendered_bytes"],
        token_estimate=manifest["token_estimate"],
        estimate_method=manifest["estimate_method"],
        budget_metric=manifest["budget_metric"],
        truncated=bool(manifest["truncation_events"]),
    )


def write_text_artifact(
    *,
    content: str,
    output_path: Path,
    manifest_path: Path,
    builder_name: str,
    builder_version: str,
    metadata: dict[str, object] | None = None,
) -> BuildArtifact:
    packet = ContextPacket(
        title="raw-payload",
        sections=[],
        metadata=metadata or {},
    )
    estimate_method = "heuristic:chars_div_4"
    normalized_content = normalize_text(content)
    manifest = build_manifest(
        packet,
        rendered_content=normalized_content,
        builder_name=builder_name,
        builder_version=builder_version,
        created_at=_utc_now(),
        estimate_method=estimate_method,
        budget_metric="tokens",
    )
    atomic_write_text(output_path, normalized_content)
    atomic_write_json(manifest_path, manifest)
    return BuildArtifact(
        content_path=output_path,
        manifest_path=manifest_path,
        content_hash=manifest["rendered_content_hash"],
        payload_hash=manifest["payload_hash"],
        rendered_bytes=manifest["rendered_bytes"],
        token_estimate=manifest["token_estimate"],
        estimate_method=manifest["estimate_method"],
        budget_metric=manifest["budget_metric"],
        truncated=False,
    )
```

### shared/file_specs.py

```text
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.context_packet import FileBlock


TRUNCATION_MARKER = "\n\n... [truncated for review packet] ...\n\n"


@dataclass(frozen=True)
class FileSpec:
    path: Path
    range_spec: str | None = None
    start_line: int | None = None
    end_line: int | None = None

    @property
    def display_path(self) -> str:
        return str(self.path)


def parse_file_spec(spec: str) -> FileSpec:
    trimmed = spec.strip()
    if ":" not in trimmed:
        return FileSpec(path=Path(trimmed).expanduser())

    file_part, maybe_range = trimmed.rsplit(":", 1)
    if not maybe_range or not maybe_range.replace("-", "").isdigit():
        return FileSpec(path=Path(trimmed).expanduser())

    path = Path(file_part).expanduser()
    if "-" in maybe_range:
        start_text, end_text = maybe_range.split("-", 1)
        return FileSpec(
            path=path,
            range_spec=maybe_range,
            start_line=int(start_text),
            end_line=int(end_text),
        )
    line_number = int(maybe_range)
    return FileSpec(
        path=path,
        range_spec=maybe_range,
        start_line=line_number,
        end_line=line_number,
    )


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data


def read_file_excerpt(spec: FileSpec, *, max_chars: int | None = None) -> tuple[str, bool, str | None]:
    if not spec.path.exists():
        return "[read failed: file not found]", False, "missing"
    if spec.path.is_symlink():
        return f"[symlink target: {spec.path.resolve()}]", False, "symlink"
    if spec.path.is_dir():
        return "[directory omitted from context packet]", False, "directory"

    raw = spec.path.read_bytes()
    if _is_binary(raw[:4096]):
        return "[binary file omitted from context packet]", False, "binary"

    text = raw.decode("utf-8", errors="replace")
    if spec.start_line is not None and spec.end_line is not None:
        lines = text.splitlines()
        start_index = max(spec.start_line - 1, 0)
        end_index = min(spec.end_line, len(lines))
        text = "\n".join(lines[start_index:end_index])

    truncated = False
    if max_chars is not None and len(text) > max_chars:
        head = max_chars // 2
        tail = max_chars - head
        text = text[:head] + TRUNCATION_MARKER + text[-tail:]
        truncated = True
    return text, truncated, None


def build_file_block(spec: FileSpec, *, max_chars: int | None = None):
    text, truncated, omission = read_file_excerpt(spec, max_chars=max_chars)
    metadata: dict[str, object] = {}
    if omission:
        metadata["omission_reason"] = omission
    return FileBlock(
        spec.display_path,
        text,
        range_spec=spec.range_spec,
        truncated=truncated,
        truncation_reason="file_excerpt_limit" if truncated else None,
        original_chars=None if not truncated else len(spec.path.read_text(errors="replace")),
        metadata=metadata,
    )
```

### shared/git_context.py

```text
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


DIFF_TRUNCATION_MARKER = "... [diff truncated] ..."


@dataclass(frozen=True)
class GitStatusEntry:
    code: str
    path: str
    old_path: str | None = None


def run_git(repo: Path, args: list[str], *, check: bool = True, text: bool = True):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=text,
    )
    if check and proc.returncode != 0:
        stderr = proc.stderr if text else proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def diff_ref(base: str | None, head: str | None) -> str | None:
    if base and head:
        return f"{base}..{head}"
    if base:
        return f"{base}..HEAD"
    if head:
        return f"HEAD..{head}"
    return None


def parse_status_porcelain(raw: bytes) -> list[GitStatusEntry]:
    entries: list[GitStatusEntry] = []
    fields = raw.split(b"\x00")
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 4:
            continue
        code = field[:2].decode("utf-8", errors="replace")
        path = field[3:].decode("utf-8", errors="replace")
        old_path = None
        if code.startswith(("R", "C")) and index < len(fields):
            old_path = path
            path = fields[index].decode("utf-8", errors="replace")
            index += 1
        entries.append(GitStatusEntry(code=code, path=path, old_path=old_path))
    return entries


def unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def resolve_touched_files(
    repo: Path,
    *,
    base: str | None,
    head: str | None,
    files: list[str] | None,
    tracked_only: bool,
) -> list[str]:
    if files:
        return unique_paths(files)

    ref = diff_ref(base, head)
    if ref:
        output = run_git(repo, ["diff", "--name-only", "-z", ref, "--"], text=False)
        names = [item.decode("utf-8", errors="replace") for item in output.split(b"\x00") if item]
        return unique_paths(names)

    if tracked_only:
        tracked = run_git(repo, ["diff", "--name-only", "-z", "HEAD", "--"], check=False, text=False)
        staged = run_git(repo, ["diff", "--cached", "--name-only", "-z", "HEAD", "--"], check=False, text=False)
        names = [item.decode("utf-8", errors="replace") for item in tracked.split(b"\x00") if item]
        names.extend(item.decode("utf-8", errors="replace") for item in staged.split(b"\x00") if item)
        return unique_paths(names)

    raw = run_git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"], text=False)
    return unique_paths([entry.path for entry in parse_status_porcelain(raw)])


def current_status(repo: Path, *, tracked_only: bool) -> str:
    args = ["status", "--short"]
    args.append("--untracked-files=no" if tracked_only else "--untracked-files=all")
    return str(run_git(repo, args, check=False)).strip()


def untracked_paths(repo: Path) -> set[str]:
    raw = run_git(repo, ["ls-files", "--others", "--exclude-standard", "-z"], check=False, text=False)
    return {item.decode("utf-8", errors="replace") for item in raw.split(b"\x00") if item}


def tracked_paths(repo: Path, files: list[str]) -> list[str]:
    untracked = untracked_paths(repo)
    return [path for path in files if path not in untracked]


def collect_diff_stat(repo: Path, *, ref: str | None, files: list[str]) -> str:
    tracked = tracked_paths(repo, files)
    if not tracked:
        return "(no tracked diff stat available)"
    args = ["diff", "--stat"]
    args.append(ref or "HEAD")
    args.append("--")
    args.extend(tracked)
    return str(run_git(repo, args, check=False)).strip() or "(empty diff stat)"


def _split_diff_chunks(diff_text: str) -> list[str]:
    lines = diff_text.splitlines()
    if not lines:
        return []
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("diff --git ") and current:
            chunks.append(current)
            current = [line]
            continue
        current.append(line)
    if current:
        chunks.append(current)
    return ["\n".join(chunk) for chunk in chunks]


def truncate_diff_text(diff_text: str, max_chars: int) -> tuple[str, bool]:
    if len(diff_text) <= max_chars:
        return diff_text, False

    chunks = _split_diff_chunks(diff_text)
    if not chunks:
        return diff_text[:max_chars].rstrip() + "\n" + DIFF_TRUNCATION_MARKER, True

    selected: list[str] = []
    total = 0
    for chunk in chunks:
        chunk_len = len(chunk) + (2 if selected else 0)
        if total + chunk_len <= max_chars:
            selected.append(chunk)
            total += chunk_len
            continue
        if not selected:
            lines = chunk.splitlines()
            partial: list[str] = []
            current_len = 0
            for line in lines:
                next_len = current_len + len(line) + 1
                if next_len >= max_chars:
                    break
                partial.append(line)
                current_len = next_len
            selected.append("\n".join(partial))
        break

    rendered = "\n\n".join(part.rstrip() for part in selected if part.strip()).rstrip()
    return rendered + "\n" + DIFF_TRUNCATION_MARKER, True


def collect_diff(repo: Path, *, ref: str | None, files: list[str], max_chars: int | None = None) -> tuple[str, bool]:
    tracked = tracked_paths(repo, files)
    if not tracked:
        return "(no tracked unified diff available)", False
    args = ["diff", "--unified=3"]
    args.append(ref or "HEAD")
    args.append("--")
    args.extend(tracked)
    diff_text = str(run_git(repo, args, check=False)).strip() or "(empty diff)"
    if max_chars is None:
        return diff_text, False
    return truncate_diff_text(diff_text, max_chars)
```

### shared/llm_dispatch.py

```text
from __future__ import annotations

import glob
import hashlib
import importlib.metadata
import json
import os
import re
import sys
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable


HELPER_VERSION = "2026-04-10-v1"

STATUS_EXIT_CODES = {
    "ok": 0,
    "timeout": 10,
    "rate_limit": 11,
    "quota": 12,
    "model_error": 13,
    "schema_error": 14,
    "parse_error": 15,
    "empty_output": 16,
    "config_error": 17,
    "dependency_error": 18,
    "dispatch_error": 19,
}

RETRYABLE_STATUSES = {
    "ok": False,
    "timeout": True,
    "rate_limit": True,
    "quota": False,
    "model_error": False,
    "schema_error": False,
    "parse_error": False,
    "empty_output": True,
    "config_error": False,
    "dependency_error": False,
    "dispatch_error": False,
}

_LLMX_CHAT: Callable[..., Any] | None = None
_LLMX_VERSION: str | None = None


@dataclass(frozen=True)
class DispatchProfile:
    name: str
    intent: str
    provider: str
    model: str
    timeout: int
    reasoning_effort: str | None = None
    max_tokens: int | None = None
    input_token_limit: int | None = None
    input_token_estimator: str = "heuristic:chars_div_4"
    search: bool = False
    api_only: bool = True
    allowed_overrides: tuple[str, ...] = ("timeout", "reasoning_effort", "max_tokens", "search")
    version: str = "v1"

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


PROFILES: dict[str, DispatchProfile] = {
    "fast_extract": DispatchProfile(
        name="fast_extract",
        intent="Low-cost extraction, triage, and short synthesis",
        provider="google",
        model="gemini-3-flash-preview",
        timeout=180,
        input_token_limit=900000,
    ),
    "deep_review": DispatchProfile(
        name="deep_review",
        intent="Long-context structural critique and review",
        provider="google",
        model="gemini-3.1-pro-preview",
        timeout=300,
        reasoning_effort="high",
        input_token_limit=900000,
    ),
    "formal_review": DispatchProfile(
        name="formal_review",
        intent="Formal or quantitative GPT-backed review",
        provider="openai",
        model="gpt-5.4",
        timeout=600,
        reasoning_effort="high",
        max_tokens=32768,
        input_token_limit=120000,
    ),
    "gpt_general": DispatchProfile(
        name="gpt_general",
        intent="General-purpose GPT-backed dispatch",
        provider="openai",
        model="gpt-5.4",
        timeout=600,
        reasoning_effort="medium",
        max_tokens=16384,
        input_token_limit=120000,
    ),
    "search_grounded": DispatchProfile(
        name="search_grounded",
        intent="Search-backed answer synthesis",
        provider="google",
        model="gemini-3.1-pro-preview",
        timeout=300,
        search=True,
        input_token_limit=900000,
    ),
    "cheap_tick": DispatchProfile(
        name="cheap_tick",
        intent="Low-cost maintenance or cycle tick synthesis",
        provider="google",
        model="gemini-3-flash-preview",
        timeout=120,
        input_token_limit=900000,
    ),
}

MODEL_TO_PROFILE = {
    "gemini-3-flash-preview": "fast_extract",
    "gemini-3.1-pro-preview": "deep_review",
    "gpt-5.4": "gpt_general",
}


@dataclass
class DispatchOverrides:
    timeout: int | None = None
    reasoning_effort: str | None = None
    max_tokens: int | None = None
    search: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value is not None
        }


@dataclass
class DispatchResult:
    status: str
    retryable: bool
    requested_profile: str
    profile_version: str
    profile_fingerprint: str
    provider: str
    model: str
    output_path: str
    meta_path: str
    error_path: str | None
    parsed_path: str | None
    latency: float
    llmx_version: str
    helper_version: str
    error_type: str | None = None
    error_message: str | None = None

    @property
    def exit_code(self) -> int:
        return STATUS_EXIT_CODES[self.status]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _temperature_for_model(model: str) -> float:
    return 1.0 if any(token in model for token in ("gpt-5", "gemini-3", "kimi-k2")) else 0.7


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*\n?", "", stripped)
        stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _remove_if_exists(path: Path | None) -> None:
    if path and path.exists():
        path.unlink()


def _bootstrap_llmx() -> tuple[Callable[..., Any], str]:
    global _LLMX_CHAT, _LLMX_VERSION
    if _LLMX_CHAT is not None:
        return _LLMX_CHAT, _LLMX_VERSION or "unknown"

    try:
        from llmx.api import chat as llmx_chat  # type: ignore
        _LLMX_CHAT = llmx_chat
    except ImportError:
        tool_sites = glob.glob(str(Path.home() / ".local/share/uv/tools/llmx/lib/python*/site-packages"))
        

... [truncated for review packet] ...

response.content or "")
        latency = float(getattr(response, "latency", 0.0) or 0.0)
        if not content.strip():
            raise ValueError("empty model output")

        _atomic_write_text(output_path, content)
        _remove_if_exists(error_path)

        parsed_error: dict[str, Any] | None = None
        if schema and parsed_path:
            try:
                parsed = json.loads(_strip_markdown_fences(content))
                _atomic_write_json(parsed_path, parsed)
            except Exception as exc:
                parsed_error = {
                    "error_type": "parse_error",
                    "error_message": str(exc),
                }
                _remove_if_exists(parsed_path)

        status = "ok" if parsed_error is None else "parse_error"
        if parsed_error:
            _atomic_write_json(error_path, parsed_error)

        meta = {
            "requested_profile": profile_def.name,
            "profile_version": profile_def.version,
            "profile_fingerprint": profile_def.fingerprint(),
            "resolved_provider": profile_def.provider,
            "resolved_model": profile_def.model,
            "resolved_kwargs": resolved,
            "api_only": call_kwargs["api_only"],
            "schema_used": bool(schema),
            "status": status,
            "retryable": RETRYABLE_STATUSES[status],
            "error_type": parsed_error["error_type"] if parsed_error else None,
            "error_message": parsed_error["error_message"] if parsed_error else None,
            "latency": latency,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "context_sha256": context_sha256,
            "context_payload_hash": context_payload_hash,
            "context_manifest_path": str(context_manifest_path) if context_manifest_path else None,
            "context_token_estimate": (context_manifest or {}).get("token_estimate"),
            "context_budget_metric": (context_manifest or {}).get("budget_metric"),
            "context_estimate_method": (context_manifest or {}).get("estimate_method"),
            "prompt_sha256": prompt_sha256,
            "llmx_version": llmx_version,
            "helper_version": HELPER_VERSION,
            "output_path": str(output_path),
            "parsed_path": str(parsed_path) if parsed_path else None,
            "error_path": str(error_path) if parsed_error else None,
        }
        _atomic_write_json(meta_path, meta)
        return DispatchResult(
            status=status,
            retryable=RETRYABLE_STATUSES[status],
            requested_profile=profile_def.name,
            profile_version=profile_def.version,
            profile_fingerprint=profile_def.fingerprint(),
            provider=profile_def.provider,
            model=profile_def.model,
            output_path=str(output_path),
            meta_path=str(meta_path),
            error_path=str(error_path) if parsed_error else None,
            parsed_path=str(parsed_path) if parsed_path else None,
            latency=latency,
            llmx_version=llmx_version,
            helper_version=HELPER_VERSION,
            error_type=parsed_error["error_type"] if parsed_error else None,
            error_message=parsed_error["error_message"] if parsed_error else None,
        )

    except Exception as exc:
        status, message = classify_error(exc)
        if status == "model_error" and "empty model output" in message.lower():
            status = "empty_output"
        _remove_if_exists(output_path)
        _remove_if_exists(parsed_path)
        error_payload = {
            "error_type": status,
            "error_message": message,
            "traceback": traceback.format_exc(limit=5),
        }
        _atomic_write_json(error_path, error_payload)
        meta = {
            "requested_profile": profile_def.name,
            "profile_version": profile_def.version,
            "profile_fingerprint": profile_def.fingerprint(),
            "resolved_provider": profile_def.provider,
            "resolved_model": profile_def.model,
            "resolved_kwargs": resolved,
            "api_only": call_kwargs["api_only"],
            "schema_used": bool(schema),
            "status": status,
            "retryable": RETRYABLE_STATUSES[status],
            "error_type": status,
            "error_message": message,
            "latency": 0.0,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "context_sha256": context_sha256,
            "context_payload_hash": context_payload_hash,
            "context_manifest_path": str(context_manifest_path) if context_manifest_path else None,
            "context_token_estimate": (context_manifest or {}).get("token_estimate"),
            "context_budget_metric": (context_manifest or {}).get("budget_metric"),
            "context_estimate_method": (context_manifest or {}).get("estimate_method"),
            "prompt_sha256": prompt_sha256,
            "llmx_version": llmx_version,
            "helper_version": HELPER_VERSION,
            "output_path": str(output_path),
            "parsed_path": str(parsed_path) if parsed_path else None,
            "error_path": str(error_path),
        }
        _atomic_write_json(meta_path, meta)
        return DispatchResult(
            status=status,
            retryable=RETRYABLE_STATUSES[status],
            requested_profile=profile_def.name,
            profile_version=profile_def.version,
            profile_fingerprint=profile_def.fingerprint(),
            provider=profile_def.provider,
            model=profile_def.model,
            output_path=str(output_path),
            meta_path=str(meta_path),
            error_path=str(error_path),
            parsed_path=str(parsed_path) if parsed_path else None,
            latency=0.0,
            llmx_version=llmx_version,
            helper_version=HELPER_VERSION,
            error_type=status,
            error_message=message,
        )
```

### shared/overview_config.py

```text
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class OverviewConfig:
    project_root: Path
    types: list[str]
    model: str
    output_dir: str
    prompt_dir: str
    exclude: str
    no_gitignore: bool
    loc_threshold: int
    dirs_by_type: dict[str, list[str]]

    def prompt_file(self, overview_type: str) -> Path:
        if self.prompt_dir.startswith("/"):
            return Path(self.prompt_dir) / f"{overview_type}.md"
        return self.project_root / self.prompt_dir / f"{overview_type}.md"

    def output_file(self, overview_type: str) -> Path:
        if self.output_dir.startswith("/"):
            return Path(self.output_dir) / f"{overview_type}-overview.md"
        return self.project_root / self.output_dir / f"{overview_type}-overview.md"


def read_overview_config(project_root: Path) -> OverviewConfig:
    conf_file = project_root / ".claude" / "overview.conf"
    config: dict[str, str] = {
        "OVERVIEW_TYPES": "source",
        "OVERVIEW_MODEL": "gemini-3-flash-preview",
        "OVERVIEW_OUTPUT_DIR": ".claude/overviews",
        "OVERVIEW_PROMPT_DIR": str((Path.home() / "Projects" / "skills" / "hooks" / "overview-prompts")),
        "OVERVIEW_EXCLUDE": "",
        "OVERVIEW_NO_GITIGNORE": "",
        "OVERVIEW_LOC_THRESHOLD": "200",
    }
    if conf_file.exists():
        for line in conf_file.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            config[key.strip()] = value.strip().strip('"')

    for key in (
        "OVERVIEW_TYPES",
        "OVERVIEW_MODEL",
        "OVERVIEW_OUTPUT_DIR",
        "OVERVIEW_PROMPT_DIR",
        "OVERVIEW_EXCLUDE",
        "OVERVIEW_NO_GITIGNORE",
        "OVERVIEW_LOC_THRESHOLD",
    ):
        env_value = os.environ.get(key)
        if env_value:
            config[key] = env_value

    overview_types = [item.strip() for item in config["OVERVIEW_TYPES"].split(",") if item.strip()]
    dirs_by_type: dict[str, list[str]] = {}
    for overview_type in overview_types:
        config_key = f"OVERVIEW_{overview_type.upper()}_DIRS"
        dirs_by_type[overview_type] = [item.strip() for item in config.get(config_key, "").split(",") if item.strip()]

    return OverviewConfig(
        project_root=project_root,
        types=overview_types,
        model=config["OVERVIEW_MODEL"],
        output_dir=config["OVERVIEW_OUTPUT_DIR"],
        prompt_dir=config["OVERVIEW_PROMPT_DIR"],
        exclude=config["OVERVIEW_EXCLUDE"],
        no_gitignore=config["OVERVIEW_NO_GITIGNORE"].lower() == "true",
        loc_threshold=int(config["OVERVIEW_LOC_THRESHOLD"]),
        dirs_by_type=dirs_by_type,
    )
```

### shared/repomix_source.py

```text
from __future__ import annotations

import subprocess
from pathlib import Path


def build_include_pattern(entries: list[str]) -> str:
    patterns: list[str] = []
    for entry in entries:
        trimmed = entry.strip()
        if not trimmed:
            continue
        if any(char in trimmed for char in "*?[]"):
            patterns.append(trimmed)
        elif trimmed.endswith("/"):
            patterns.append(f"{trimmed}**")
        else:
            patterns.append(trimmed)
    return ",".join(patterns)


def repomix_args(*, include_pattern: str, exclude: str | None, no_gitignore: bool) -> list[str]:
    args = ["--stdout", "--include", include_pattern]
    if no_gitignore:
        args.append("--no-gitignore")
    if exclude:
        args.extend(["--ignore", exclude])
    return args


def capture_repomix_to_file(
    *,
    project_root: Path,
    include_pattern: str,
    exclude: str | None,
    no_gitignore: bool,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    args = ["repomix", *repomix_args(include_pattern=include_pattern, exclude=exclude, no_gitignore=no_gitignore)]
    with output_path.open("w") as handle:
        proc = subprocess.run(
            args,
            cwd=project_root,
            stdout=handle,
            stderr=subprocess.PIPE,
            text=True,
        )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "repomix failed")
```

### shared/test_context_packet.py

```text
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from shared.context_packet import BudgetPolicy, ContextPacket, PacketSection, TextBlock
from shared.context_renderers import write_packet_artifact
from shared.file_specs import parse_file_spec
from shared.git_context import parse_status_porcelain


class ContextPacketTest(unittest.TestCase):
    def test_write_packet_artifact_emits_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            packet = ContextPacket(
                title="Packet",
                sections=[PacketSection("Section", [TextBlock("Block", "hello world")])],
                budget_policy=BudgetPolicy(metric="tokens", limit=100),
            )
            output_path = root / "packet.md"
            manifest_path = root / "packet.manifest.json"
            artifact = write_packet_artifact(
                packet,
                renderer="markdown",
                output_path=output_path,
                manifest_path=manifest_path,
                builder_name="test",
                builder_version="v1",
            )
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(artifact.content_hash, manifest["rendered_content_hash"])
            self.assertEqual(artifact.payload_hash, manifest["payload_hash"])
            self.assertEqual(manifest["budget_metric"], "tokens")
            self.assertEqual(manifest["normalization_version"], "v1")

    def test_parse_file_spec_handles_ranges(self) -> None:
        spec = parse_file_spec("foo.py:10-20")
        self.assertEqual(spec.path, Path("foo.py"))
        self.assertEqual(spec.start_line, 10)
        self.assertEqual(spec.end_line, 20)
        self.assertEqual(spec.range_spec, "10-20")

    def test_parse_status_porcelain_handles_rename_and_spaces(self) -> None:
        raw = b"R  old name.py\x00new name.py\x00?? extra file.py\x00"
        entries = parse_status_porcelain(raw)
        self.assertEqual(entries[0].old_path, "old name.py")
        self.assertEqual(entries[0].path, "new name.py")
        self.assertEqual(entries[1].path, "extra file.py")


if __name__ == "__main__":
    unittest.main()
```
```
