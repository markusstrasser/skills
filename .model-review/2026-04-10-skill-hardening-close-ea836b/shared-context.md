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

### /Users/alien/Projects/skills/.model-review/2026-04-10-skill-hardening-close-context.md

```text
# Plan-Close Review Packet

- Repo: `/Users/alien/Projects/skills`
- Mode: `worktree`
- Ref: `HEAD vs current worktree`
- Profile: `formal_review`
- diff_char_cap: `40000`
- file_char_cap: `8000`
- max_file_count: `12`

## Scope

Scope: close review for manifest-first skill migration, review/observe/brainstorm/modal/upgrade contract hardening, and caller migration. Focus on correctness regressions, contract drift, and obvious missing validation. Ignore unrelated dirty files outside the listed paths.

## Touched Files

### Touched Files

- `shared/skill_manifest.py`
- `scripts/lint_skill_manifests.py`
- `scripts/test_skill_manifest.py`
- `review/scripts/model-review.py`
- `review/scripts/test_model_review.py`
- `observe/scripts/observe_artifacts.py`
- `observe/scripts/session-shape.py`
- `observe/scripts/session_shape.py`
- `observe/scripts/validate_session_ids.py`
- `brainstorm/tests/test_brainstorm_contract.py`
- `scripts/test_modal_attribution_contract.py`
- `research-ops/SKILL.md`

## Git Status

### git status --short

```text
M .claude/telemetry/llm-dispatch.jsonl
 M _archive/code-review/code-review
 M brainstorm/SKILL.md
 M brainstorm/references/domain-pools.md
 M brainstorm/references/llmx-dispatch.md
 M brainstorm/references/synthesis-templates.md
 M hooks/stop-plan-gate.sh
 M modal/SKILL.md
 M modal/references/resources.md
 M observe/SKILL.md
 M observe/references/corrections-mode.md
 M observe/references/existing-infra-checks.md
 M observe/references/findings-staging.md
 M observe/references/gemini-dispatch-prompt.md
 M observe/references/gemini-prompt.md
 M observe/references/loop-mode.md
 M observe/references/output-template.md
 M observe/references/transcript-extraction.md
 M observe/scripts/session-shape.py
 M observe/scripts/validate_session_ids.py
 M references/data-acquisition/data-acquisition
 M references/source-grading/source-grading
 M research-ops/SKILL.md
 M review/SKILL.md
 M review/lenses/adversarial-review.md
 M review/lenses/plan-close-review.md
 M review/references/biases-and-antipatterns.md
 M review/references/dispatch.md
 M review/references/extraction.md
 M review/references/prompts.md
 M review/scripts/model-review.py
 M review/scripts/test_model_review.py
 M upgrade/SKILL.md
 M upgrade/references/cross-validation.md
 M upgrade/references/json-parsing.md
 M upgrade/references/model-prompts-harness.md
 M upgrade/references/model-prompts-standard.md
 M upgrade/references/operational-discipline.md
 M upgrade/references/phase-3-research.md
 M upgrade/references/phase-5-review.md
?? brainstorm/skill.json
?? brainstorm/tests/test_brainstorm_contract.py
?? hooks/pretool-genomics-mcp-routing.sh
?? modal/references/attribution.md
?? modal/references/status-reconciliation.md
?? modal/skill.json
?? observe/references/artifact-contract.md
?? observe/scripts/observe_artifacts.py
?? observe/scripts/session_shape.py
?? observe/skill.json
?? observe/tests/test_observe_artifacts.py
?? review/skill.json
?? scripts/lint_skill_manifests.py
?? scripts/test_modal_attribution_contract.py
?? scripts/test_skill_manifest.py
?? shared/skill_manifest.py
?? upgrade/skill.json
```

### git diff --stat

```text
observe/scripts/session-shape.py        |  90 ++++++++++-
 observe/scripts/validate_session_ids.py |  28 ++--
 research-ops/SKILL.md                   |   6 +-
 review/scripts/model-review.py          | 238 +++++++++++++++++++++++++----
 review/scripts/test_model_review.py     | 258 ++++++++++++++++++++++++++++++++
 5 files changed, 574 insertions(+), 46 deletions(-)
```

### Unified Diff

```diff
observe/scripts/session-shape.py --- 1/5 --- Python
  1 #!/usr/bin/env python3                 1 #!/usr/bin/env python3
  2 """Session shape detector — zero-LL    2 """Session shape detector — zero-LL
  . M-cost structural anomaly detection    . M-cost structural anomaly detection
  . .                                      . .
  3                                        3 
  4 Analyzes session topology (tool pat    4 Analyzes session topology (tool pat
  . terns, message ratios, structural s    . terns, message ratios, structural s
  . ignals)                                . ignals)
  5 to flag anomalous sessions worth de    5 to flag anomalous sessions worth de
  . ep analysis. Pre-filter for session    . ep analysis. The deterministic outp
  . -analyst:                              . ut can
  6 most sessions are fine — don't wast    6 also be written as observe signal/c
  . e Gemini on them.                      . andidate JSONL records for backlog 
  .                                        . staging.
  7                                        7 
  8 Usage:                                 8 Usage:
  9     session-shape.py [--days N] [--    9     session-shape.py [--days N] [--
  . project P] [--threshold T] [--json]    . project P] [--threshold T] [--json]
  .                                       10         [--signals-out PATH] [--can
  .                                       .. didates-out PATH]
 10 """                                   11 """
 11                                       12 
 12 import argparse                       13 import argparse
 13 import json                           14 import json
 14 import sqlite3                        15 import sqlite3
 15 import sys                            16 import sys
 16 from collections import Counter       .. 
 17 from dataclasses import dataclass,    17 from dataclasses import dataclass, 
 .. field                                 .. field
 18 from datetime import datetime, time   18 from datetime import datetime, time
 .. delta, timezone                       .. delta, timezone
 19 from pathlib import Path              19 from pathlib import Path
 20 from statistics import mean, stdev    20 from statistics import mean, stdev
 21                                       21 
 22 import os                             22 import os
 ..                                       23 
 ..                                       24 from observe_artifacts import (
 ..                                       25     append_jsonl,
 ..                                       26     artifact_path,
 ..                                       27     stable_id,
 ..                                       28 )
 23                                       29 
 24 # Inlined from meta/scripts/common/   30 # Inlined from meta/scripts/common/
 .. paths.py and meta/scripts/config.py   .. paths.py and meta/scripts/config.py
 25 _CLAUDE_DIR = Path(os.environ.get("   31 _CLAUDE_DIR = Path(os.environ.get("
 .. CLAUDE_DIR", str(Path.home() / ".cl   .. CLAUDE_DIR", str(Path.home() / ".cl
 .. aude")))                              .. aude")))

observe/scripts/session-shape.py --- 2/5 --- Python
138 144     return shapes
... 145 
... 146 
... 147 def build_signal_record(shape: SessionShape, *, threshold: float) -> dict:
... 148     """Build a deterministic signal record for backlog staging."""
... 149     return {
... 150         "schema": "observe.signal.v1",
... 151         "kind": "session_shape",
... 152         "session_id": shape.uuid,
... 153         "signal_id": stable_id(
... 154             "signal",
... 155             "session_shape",
... 156             shape.uuid,
... 157             shape.project,
... 158         ),
... 159         "project": shape.project,
... 160         "start_ts": shape.start_ts,
... 161         "threshold": threshold,
... 162         "anomaly_score": round(shape.anomaly_score, 3),
... 163         "reasons": list(shape.anomaly_reasons),
... 164         "features": {k: round(v, 6) for k, v in shape.features.items()},
... 165         "first_message": shape.first_message,
... 166         "source": "scripts/session-shape.py",
... 167         "status": "signal",
... 168     }
... 169 
... 170 
... 171 def build_candidate_record(shape: SessionShape, *, threshold: float) -> dict:
... 172     """Build a candidate backlog record derived from a signal."""
... 173     signal_id = stable_id("signal", "session_shape", shape.uuid, shape.project)
... 174     candidate_summary = (
... 175         f"Session shape anomaly for {shape.project} {shape.uuid[:8]} "
... 176         f"(score {shape.anomaly_score:.1f}, threshold {threshold:.1f})"
... 177     )
... 178     return {
... 179         "schema": "observe.candidate.v1",
... 180         "kind": "session_shape_anomaly",
... 181         "candidate_id": stable_id(
... 182             "candidate",
... 183             "session_shape_anomaly",
... 184             shape.uuid,
... 185             shape.project,
... 186         ),
... 187         "session_id": shape.uuid,
... 188         "project": shape.project,
... 189         "source_signal_ids": [signal_id],
... 190         "recurrence": 1,
... 191         "promoted": False,
... 192         "state": "candidate",
... 193         "checkable": True,
... 194         "summary": candidate_summary,
... 195         "evidence": {
... 196             "score": round(shape.anomaly_score, 3),
... 197             "threshold": threshold,
... 198             "reasons": list(shape.anomaly_reasons),
... 199             "first_message": shape.first_message,
... 200             "duration_min": round(shape.duration_min, 2),
... 201             "cost_usd": round(shape.cost_usd, 2),
... 202         },
... 203         "source": "scripts/session-shape.py",
... 204     }
139 205 
140 206 
141 207 def main():

observe/scripts/session-shape.py --- 3/5 --- Python
147 213     )
148 214     parser.add_argument("--json", action="store_true", help="JSON output")
149 215     parser.add_argument("--all", action="store_true", help="Show all sessions, not just anomalies")
... 216     parser.add_argument(
... 217         "--signals-out",
... 218         type=Path,
... 219         help="Append deterministic signal records as JSONL",
... 220     )
... 221     parser.add_argument(
... 222         "--candidates-out",
... 223         type=Path,
... 224         help="Append candidate backlog records as JSONL",
... 225     )
150 226     args = parser.parse_args()
151 227 
152 228     if not DB_PATH.exists():

observe/scripts/session-shape.py --- 4/5 --- Python
194 270 
195 271     # Compute anomalies
196 272     shapes = compute_anomalies(shapes, threshold=args.threshold)
... 273     signal_shapes = list(shapes)
197 274 
198 275     # Filter to anomalies unless --all
199 276     anomalous = len([s for s in shapes if s.anomaly_score > 0])

observe/scripts/session-shape.py --- 5/5 --- Python
236 313             print(f"  {s.first_message}")
237 314             print()
... 315 
... 316     signals_out = args.signals_out or artifact_path("signals.jsonl")
... 317     candidates_out = args.candidates_out or artifact_path("candidates.jsonl")
... 318     for shape in signal_shapes:
... 319         append_jsonl(signals_out, build_signal_record(shape, threshold=args.threshold))
... 320         if shape.anomaly_score > 0:
... 321             append_jsonl(candidates_out, build_candidate_record(shape, threshold=args.threshold))
238 322 
239 323     # Log metric
240 324     log_metric("session_shape",

observe/scripts/validate_session_ids.py --- 1/3 --- Python
  1 #!/usr/bin/env python3                 1 #!/usr/bin/env python3
  2 """Validate session IDs in Gemini o    2 """Validate session IDs in Gemini o
  . utput against the extraction manife    . utput against the extraction manife
  . st.                                    . st.
  3                                        3 
  4 Reads input.md for the VALID SESSIO    4 Reads input.md for the VALID SESSIO
  . N IDS table, then checks gemini-out    . N IDS table, then checks gemini-out
  . put.md                                 . put.md
  5 for any 8-char hex patterns that ar    5 for any 8-char hex patterns that ar
  . en't in the allowlist. Reports fabr    . en't in the allowlist. Reports fabr
  . icated                                 . icated
  6 IDs and optionally strips them from    6 IDs and optionally strips them from
  .  findings.                             .  findings.
  7                                        7 
  8 Usage:                                 8 Usage:
  9     python validate_session_ids.py     9     python validate_session_ids.py 
  . [--input FILE] [--output FILE] [--s    . [--input FILE] [--output FILE] [--s
  . trip]                                  . trip]
 10                                       10 
 11 Defaults to session-analyst artifac   11 Defaults to the canonical observe a
 .. t paths.                              .. rtifact root.
 12 """                                   12 """
 13                                       13 
 14 import argparse                       14 import argparse
 15 import re                             15 import re
 16 import sys                            16 import sys
 17 from pathlib import Path              17 from pathlib import Path
 18                                       18 
 19 ARTIFACT_DIR = Path.home() / "Proje   19 from observe_artifacts import artif
 .. cts/agent-infra/artifacts/session-a   .. act_root
 .. nalyst"                               .. 
 ..                                       20 
 20 HEX8_PATTERN = re.compile(r"\b([0-9   21 HEX8_PATTERN = re.compile(r"\b([0-9
 .. a-f]{8})\b")                          .. a-f]{8})\b")
 21 MANIFEST_ROW = re.compile(r"\|\s*([   22 MANIFEST_ROW = re.compile(r"\|\s*([
 .. 0-9a-f]{8})\s*\|")                    .. 0-9a-f]{8})\s*\|")

observe/scripts/validate_session_ids.py --- 2/3 --- Python
 72                                       73 
 73 def main():                           74 def main():
 74     parser = argparse.ArgumentParse   75     parser = argparse.ArgumentParse
 .. r(description="Validate session IDs   .. r(description="Validate session IDs
 ..  in Gemini output")                   ..  in Gemini output")
 ..                                       76     parser.add_argument("--artifact
 ..                                       .. -root", type=Path, help="Override t
 ..                                       .. he observe artifact root")
 75     parser.add_argument("--input",    77     parser.add_argument("--input", 
 .. "-i", type=Path, default=ARTIFACT_D   .. "-i", type=Path, help="Input transc
 .. IR / "input.md")                      .. ript markdown")
 76     parser.add_argument("--gemini",   78     parser.add_argument("--gemini",
 ..  "-g", type=Path, default=ARTIFACT_   ..  "-g", type=Path, help="Gemini outp
 .. DIR / "gemini-output.md")             .. ut markdown")
 77     parser.add_argument("--strip",    79     parser.add_argument("--strip", 
 .. action="store_true", help="Replace    .. action="store_true", help="Replace 
 .. fabricated IDs in output")            .. fabricated IDs in output")
 78     parser.add_argument("--output",   80     parser.add_argument("--output",
 ..  "-o", type=Path, help="Write strip   ..  "-o", type=Path, help="Write strip
 .. ped output to file")                  .. ped output to file")
 79     args = parser.parse_args()        81     args = parser.parse_args()
 ..                                       82 
 ..                                       83     root = args.artifact_root or ar
 ..                                       .. tifact_root()
 ..                                       84     input_path = args.input or (roo
 ..                                       .. t / "input.md")
 ..                                       85     gemini_path = args.gemini or (r
 ..                                       .. oot / "gemini-output.md")
 80                                       86 
 81     if not args.input.exists():       87     if not input_path.exists():
 82         print(f"✗ Input not found:    88         print(f"✗ Input not found: 
 .. {args.input}", file=sys.stderr)       .. {input_path}", file=sys.stderr)
 83         sys.exit(1)                   89         sys.exit(1)
 84     if not args.gemini.exists():      90     if not gemini_path.exists():
 85         print(f"✗ Gemini output not   91         print(f"✗ Gemini output not
 ..  found: {args.gemini}", file=sys.st   ..  found: {gemini_path}", file=sys.st
 .. derr)                                 .. derr)
 86         sys.exit(1)                   92         sys.exit(1)
 87                                       93 
 88     report = validate(args.input, a   94     report = validate(input_path, g
 .. rgs.gemini)                           .. emini_path)
 89                                       95 
 90     print(f"  Manifest IDs: {len(re   96     print(f"  Manifest IDs: {len(re
 .. port['valid_ids'])} {report['valid_   .. port['valid_ids'])} {report['valid_
 .. ids']}")                              .. ids']}")
 91     print(f"  Referenced:   {len(re   97     print(f"  Referenced:   {len(re
 .. port['referenced_ids'])} {report['r   .. port['referenced_ids'])} {report['r
 .. eferenced_ids']}")                    .. eferenced_ids']}")

observe/scripts/validate_session_ids.py --- 3/3 --- Python
 99         print(f"  ! Unreferenced se  105         print(f"  ! Unreferenced se
 .. ssions: {report['unreferenced']}")   ... ssions: {report['unreferenced']}")
100                                      106 
101     if args.strip and report["fabri  107     if args.strip and report["fabri
... cated"]:                             ... cated"]:
102         gemini_text = args.gemini.r  108         gemini_text = gemini_path.r
... ead_text()                           ... ead_text()
103         cleaned = strip_fabricated(  109         cleaned = strip_fabricated(
... gemini_text, set(report["fabricated  ... gemini_text, set(report["fabricated
... "]))                                 ... "]))
104         out_path = args.output or a  110         out_path = args.output or g
... rgs.gemini                           ... emini_path
105         out_path.write_text(cleaned  111         out_path.write_text(cleaned
... )                                    ... )
106         print(f"  ✓ Stripped {len(r  112         print(f"  ✓ Stripped {len(r
... eport['fabricated'])} fabricated ID  ... eport['fabricated'])} fabricated ID
... s → {out_path}")                     ... s → {out_path}")
107                                      113 

research-ops/SKILL.md --- Text
114 2. **Probe external claims inline:*  114 2. **Probe external claims inline:*
... * If the plan references any URL, A  ... * If the plan references any URL, A
... PI endpoint, or version number, HTT  ... PI endpoint, or version number, HTT
... P-probe it directly. This catches 4  ... P-probe it directly. This catches 4
... 04s and HTML-instead-of-API before   ... 04s and HTML-instead-of-API before 
... wasting a review cycle (caught 2 bu  ... wasting a review cycle (caught 2 bu
... gs in 6 cycles).                     ... gs in 6 cycles).
115 3. **Cross-model review via script:  115 3. **Cross-model review via script:
... ** Write the plan to a temp file, t  ... ** Write the plan to a temp file, t
... hen dispatch:                        ... hen dispatch:
116 ```bash                              116 ```bash
117 uv run python3 ~/Projects/skills/mo  117 uv run python3 ~/Projects/skills/re
... del-review/scripts/model-review.py   ... view/scripts/model-review.py \
... \                                    ... 
118   --context /tmp/cycle-plan.md \     118   --context /tmp/cycle-plan.md \
119   --topic "research-cycle-G{N}" \    119   --topic "research-cycle-G{N}" \
120   --axes simple \                    120   --axes standard \
121   --project "$(pwd)" \               121   --project "$(pwd)" \
122   "Review this plan for wrong assum  122   "Review this plan for wrong assum
... ptions, missing steps, and anything  ... ptions, missing steps, and anything
...  that could break existing function  ...  that could break existing function
... ality"                               ... ality"
123 ```                                  123 ```
124 Route `--axes` by stakes: `simple`   124 Route `--axes` by stakes: `standard
... for autonomous/low-risk, `standard`  ... ` for autonomous/low-risk, `deep` f
...  for needs-approval, `deep` for str  ... or needs-approval, `full` for struc
... uctural changes. Skip cross-model e  ... tural changes. Skip cross-model ent
... ntirely for trivial changes (docstr  ... irely for trivial changes (docstrin
... ing fixes, config tweaks).           ... g fixes, config tweaks).
125 Read the output files, apply verifi  125 Read the output files, apply verifi
... ed findings to plan. If critical is  ... ed findings to plan. If critical is
... sues, move plan back to gaps. **On   ... sues, move plan back to gaps. **On 
... model-review failure:** check exit   ... model-review failure:** check exit 
... code + stderr before retrying. Clas  ... code + stderr before retrying. Clas
... sify: auth (retry), rate-limit (fal  ... sify: auth (retry), rate-limit (fal
... l back to other model), timeout (re  ... l back to other model), timeout (re
... duce context), schema error (fix in  ... duce context), schema error (fix in
... put). Do NOT blindly retry the same  ... put). Do NOT blindly retry the same
...  model (FM24). Commit.               ...  model (FM24). Commit.
126                                      126 
127 **Execute:** Read reviewed plan. Im  127 **Execute:** Read reviewed plan. Im
... plement it — the queue is the appro  ... plement it — the queue is the appro
... val, no `[x]` gate. **Before execut  ... val, no `[x]` gate. **Before execut
... ing:** note current HEAD SHA. After  ... ing:** note current HEAD SHA. After
...  implementation, commit. **Reflect   ...  implementation, commit. **Reflect 
... inline** (1-3 lines under the done   ... inline** (1-3 lines under the done 
... entry): what was easier/harder than  ... entry): what was easier/harder than
...  planned, did plan assumptions hold  ...  planned, did plan assumptions hold
... , anything to carry forward. Move i  ... , anything to carry forward. Move i
... tem from Active Plan to `## Autonom  ... tem from Active Plan to `## Autonom
... ous (done)` with date + reflection.  ... ous (done)` with date + reflection.
...  Mark corresponding gap entry with   ...  Mark corresponding gap entry with 
... `~~done~~` prefix.                   ... `~~done~~` prefix.

review/scripts/model-review.py --- 1/12 --- Python
   1 #!/usr/bin/env python3                 1 #!/usr/bin/env python3
   2 """Model-review dispatch — context     2 """Model-review dispatch — context
   .  assembly + parallel llmx dispatch     .  assembly + parallel llmx dispatch
   .  + output collection.                  .  + output collection.
   3                                        3 
   4 Replaces the 10-tool-call manual c     4 Replaces the 10-tool-call manual c
   . eremony in the model-review skill      . eremony in the model-review skill 
   . with one script call.                  . with one script call.
   5 Agent provides context + topic + q     5 Agent provides context + topic + q
   . uestion; script handles plumbing;      . uestion; script handles plumbing; 
   . agent reads outputs.                   . agent reads outputs.
   6                                        6 
   7 Usage:                                 7 Usage:
   8     # Standard review (2 queries:      8     # Standard review (2 queries: 
   . arch + formal)                         . arch + formal)
   9     model-review.py --context plan     9     model-review.py --context plan
   . .md --topic "hook architecture" "R     . .md --topic "hook architecture" "R
   . eview for gaps"                        . eview for gaps"
  10                                       10 
  11     # Simple review (1 query: comb    11     # Deep review (4 queries: arch
  .. ined)                                 ..  + formal + domain + mechanical)
  12     model-review.py --context plan    .. 
  .. .md --topic "config tweak" --axes     .. 
  .. simple "Review this change"           .. 
  13                                       .. 
  14     # Deep review (4 queries: arch    12     model-review.py --context plan
  ..  + formal + domain + mechanical)      .. .md --topic "classification logic"
  ..                                       ..  --axes arch,formal,domain,mechani
  ..                                       .. cal "Review this"
  15     model-review.py --context plan    13 
  .. .md --topic "classification logic"    .. 
  ..  --axes arch,formal,domain,mechani    .. 
  .. cal "Review this"                     .. 
  16                                       14     # With project dir for constit
  ..                                       .. ution discovery
  17     # With project dir for constit    15     model-review.py --context plan
  .. ution discovery                       .. .md --topic "data wiring" --projec
  ..                                       .. t ~/Projects/intel "Review this pl
  ..                                       .. an"
  18     model-review.py --context plan    16 """
  .. .md --topic "data wiring" --projec    .. 
  .. t ~/Projects/intel "Review this pl    .. 
  .. an"                                   .. 
  19 """                                   .. 
  20                                       17 
  21 from __future__ import annotations    18 from __future__ import annotations
  22                                       19 

review/scripts/model-review.py --- 2/12 --- Python
 193                                      190 
 194 Do NOT critique the existing plan    191 Do NOT critique the existing plan 
 ... — generate alternatives. Different   ... — generate alternatives. Different
 ...  mechanisms, not tweaks.""",         ...  mechanisms, not tweaks.""",
 195     },                               192     },
 196     "simple": {                      ... 
 197         "label": "Gemini Pro (comb   ... 
 ... ined review)",                       ... 
 198         "profile": "deep_review",    ... 
 199         "prompt": """\               ... 
 200 <system>                             ... 
 201 Quick combined review. Be concrete   ... 
 ... . It is {date}. Budget: ~1000 word   ... 
 ... s.                                   ... 
 202 </system>                            ... 
 203                                      ... 
 204 {question}                           ... 
 205                                      ... 
 206 Check for: (1) anything that break   ... 
 ... s existing functionality, (2) wron   ... 
 ... g assumptions, (3) missing edge ca   ... 
 ... ses.                                 ... 
 207 If everything looks correct, say s   ... 
 ... o concisely.""",                     ... 
 208     },                               ... 
 209 }                                    193 }
 210                                      194 
 211 # Presets map a single name to a l   195 # Presets map a single name to a l
 ... ist of axes                          ... ist of axes
 212 PRESETS = {                          196 PRESETS = {
 213     "simple": ["simple"],            ... 
 214     "standard": ["arch", "formal"]   197     "standard": ["arch", "formal"]
 ... ,                                    ... ,
 215     "deep": ["arch", "formal", "do   198     "deep": ["arch", "formal", "do
 ... main", "mechanical"],                ... main", "mechanical"],
 216     "full": ["arch", "formal", "do   199     "full": ["arch", "formal", "do
 ... main", "mechanical", "alternatives   ... main", "mechanical", "alternatives
 ... "],                                  ... "],
 217 }                                    200 }
 218                                      201 
 219 GEMINI_PRO_MODEL = dispatch_core.P   202 GEMINI_PRO_MODEL = dispatch_core.P
 ... ROFILES["deep_review"].model         ... ROFILES["deep_review"].model
 220 GEMINI_FLASH_MODEL = dispatch_core   203 GEMINI_FLASH_MODEL = dispatch_core
 ... .PROFILES["fast_extract"].model      ... .PROFILES["fast_extract"].model
 ...                                      204 COVERAGE_SCHEMA_VERSION = "review-
 ...                                      ... coverage.v1"
 221 GEMINI_RATE_LIMIT_MARKERS = (        205 GEMINI_RATE_LIMIT_MARKERS = (
 222     "503",                           206     "503",
 223     "rate limit",                    207     "rate limit",

review/scripts/model-review.py --- 3/12 --- Python
 241  225     return value.manifest_path if isinstance(value, ContextArtifact) else None
 ...  226 
 ...  227 
 ...  228 def axis_uses_gpt(axis_name: str) -> bool:
 ...  229     model_name = dispatch_core.PROFILES[str(AXES[axis_name]["profile"])].model.lower()
 ...  230     return "gpt" in model_name
 ...  231 
 ...  232 
 ...  233 def resolve_axes(raw_axes: str, *, allow_non_gpt: bool = False) -> list[str]:
 ...  234     axes_text = raw_axes.strip()
 ...  235     if axes_text == "simple":
 ...  236         raise ValueError("the `simple` preset was removed; use `standard` for the GPT-inclusive default")
 ...  237 
 ...  238     if axes_text in PRESETS:
 ...  239         axis_names = PRESETS[axes_text]
 ...  240     else:
 ...  241         axis_names = [axis.strip() for axis in axes_text.split(",") if axis.strip()]
 ...  242         if not axis_names:
 ...  243             raise ValueError("no review axes provided")
 ...  244         unknown_axes = [axis for axis in axis_names if axis not in AXES]
 ...  245         if unknown_axes:
 ...  246             raise ValueError(
 ...  247                 f"unknown axis '{unknown_axes[0]}'. Available: {', '.join(sorted(AXES.keys()))}"
 ...  248             )
 ...  249 
 ...  250     if not allow_non_gpt and not any(axis_uses_gpt(axis_name) for axis_name in axis_names):
 ...  251         raise ValueError(
 ...  252             "review requires at least one GPT-backed axis; add `formal` or use `standard`, `deep`, or `full`"
 ...  253         )
 ...  254     return axis_names
 242  255 
 243  256 
 244  257 def slugify(text: str, max_len: int = 40) -> str:

review/scripts/model-review.py --- 4/12 --- Python
 591  604     return results
 ...  605 
 ...  606 
 ...  607 def _load_json(path: Path) -> dict:
 ...  608     try:
 ...  609         return json.loads(path.read_text())
 ...  610     except (FileNotFoundError, json.JSONDecodeError):
 ...  611         return {}
 ...  612 
 ...  613 
 ...  614 def _review_artifact_path(review_dir: Path, filename: str) -> str | None:
 ...  615     path = review_dir / filename
 ...  616     return str(path) if path.exists() else None
 ...  617 
 ...  618 
 ...  619 def _context_packet_summary(review_dir: Path) -> dict[str, object]:
 ...  620     manifest_path = review_dir / "shared-context.manifest.json"
 ...  621     manifest = _load_json(manifest_path)
 ...  622     packet_metadata = manifest.get("packet_metadata") or {}
 ...  623     budget_enforcement = packet_metadata.get("budget_enforcement") or {}
 ...  624     return {
 ...  625         "path": str(manifest_path) if manifest_path.exists() else None,
 ...  626         "builder_name": manifest.get("builder_name"),
 ...  627         "builder_version": manifest.get("builder_version"),
 ...  628         "payload_hash": manifest.get("payload_hash"),
 ...  629         "rendered_content_hash": manifest.get("rendered_content_hash"),
 ...  630         "rendered_bytes": manifest.get("rendered_bytes"),
 ...  631         "token_estimate": manifest.get("token_estimate"),
 ...  632         "estimate_method": manifest.get("estimate_method"),
 ...  633         "budget_metric": manifest.get("budget_metric"),
 ...  634         "budget_limit": manifest.get("budget_limit"),
 ...  635         "source_paths_count": len(manifest.get("source_paths") or []),
 ...  636         "truncation_event_count": len(manifest.get("truncation_events") or []),
 ...  637         "dropped_blocks": budget_enforcement.get("dropped_blocks") or [],
 ...  638     }
 ...  639 
 ...  640 
 ...  641 def write_coverage_artifact(
 ...  642     review_dir: Path,
 ...  643     dispatch_result: dict | None = None,
 ...  644     *,
 ...  645     extraction_tasks: list[tuple[str, Path, str]] | None = None,
 ...  646     axis_findings: dict[str, list[dict]] | None = None,
 ...  647     merged_findings: list[dict] | None = None,
 ...  648     disposition_path: str | None = None,
 ...  649     verification_summary: dict[str, object] | None = None,
 ...  650     verified_disposition_path: str | None = None,
 ...  651 ) -> Path:
 ...  652     coverage_path = review_dir / "coverage.json"
 ...  653     existing_payload = _load_json(coverage_path)
 ...  654     requested_axes: list[str] = []
 ...  655     dispatch_axes: list[dict[str, object]] = []
 ...  656 
 ...  657     if dispatch_result is not None:
 ...  658         requested_axes = [
 ...  659             axis
 ...  660             for axis, info in dispatch_result.items()
 ...  661             if axis
 ...  662             not in {"review_dir", "axes", "queries", "elapsed_seconds", "dispatch_failures", "failed_axes"}
 ...  663             and isinstance(info, dict)
 ...  664         ]
 ...  665         dispatch_axes = [
 ...  666             {
 ...  667                 "axis": axis,
 ...  668                 "label": info.get("label"),
 ...  669                 "requested_model": info.get("requested_model"),
 ...  670                 "model": info.get("model"),
 ...  671                 "exit_code": info.get("exit_code"),
 ...  672                 "output_path": info.get("output"),
 ...  673                 "output_bytes": info.get("size"),
 ...  674                 "latency_seconds": info.get("latency"),
 ...  675                 "fallback_from": info.get("fallback_from"),
 ...  676                 "fallback_reason": info.get("fallback_reason"),
 ...  677             }
 ...  678             for axis, info in ((axis, dispatch_result[axis]) for axis in requested_axes)
 ...  679         ]
 ...  680 
 ...  681     payload = {
 ...  682         "schema_version": COVERAGE_SCHEMA_VERSION,
 ...  683         "review_dir": str(review_dir),
 ...  684         "artifacts": existing_payload.get("artifacts", {}),
 ...  685         "context_packet": _context_packet_summary(review_dir),
 ...  686         "dispatch": existing_payload.get("dispatch", {}),
 ...  687         "extraction": existing_payload.get("extraction", {"enabled": False}),
 ...  688         "verification": existing_payload.get("verification", {"enabled": False}),
 ...  689     }
 ...  690 
 ...  691     payload["artifacts"].update(
 ...  692         {
 ...  693             "shared_context": _review_artifact_path(review_dir, "shared-context.md"),
 ...  694             "shared_context_manifest": _review_artifact_path(review_dir, "shared-context.manifest.json"),
 ...  695             "findings": _review_artifact_path(review_dir, "findings.json"),
 ...  696             "disposition": disposition_path or payload["artifacts"].get("disposition"),
 ...  697             "verified_disposition": verified_disposition_path or payload["artifacts"].get("verified_disposition"),
 ...  698         }
 ...  699     )
 ...  700 
 ...  701     if dispatch_result is not None:
 ...  702         payload["dispatch"] = {
 ...  703             "requested_axes": requested_axes,
 ...  704             "requested_axis_count": len(requested_axes),
 ...  705             "axes": dispatch_axes,
 ...  706             "elapsed_seconds": dispatch_result.get("elapsed_seconds"),
 ...  707         }
 ...  708 
 ...  709     if extraction_tasks is not None or axis_findings is not None or merged_findings is not None:
 ...  710         usable_axes = [axis for axis, _, _ in (extraction_tasks or [])]
 ...  711         usable_axis_count = len(usable_axes)
 ...  712         findings_before_dedup = sum(len(findings) for findings in (axis_findings or {}).values())
 ...  713         payload["extraction"] = {
 ...  714             "enabled": True,
 ...  715             "usable_axes": usable_axes,
 ...  716             "usable_axis_count": usable_axis_count,
 ...  717             "axes_with_findings": list((axis_findings or {}).keys()),
 ...  718             "axes_with_findings_count": len(axis_findings or {}),
 ...  719             "findings_before_dedup": findings_before_dedup,
 ...  720             "findings_after_dedup": len(merged_findings or []),
 ...  721             "cross_model_agreements": sum(
 ...  722                 1 for finding in (merged_findings or []) if finding.get("cross_model")
 ...  723             ),
 ...  724             "findings_by_axis": {
 ...  725                 axis: len(findings) for axis, findings in (axis_findings or {}).items()
 ...  726             },
 ...  727             "coverage_ratio": round(len(axis_findings or {}) / usable_axis_count, 3) if usable_axis_count else 0.0,
 ...  728         }
 ...  729 
 ...  730     if verification_summary is not None:
 ...  731         payload["verification"] = {"enabled": True, **verification_summary}
 ...  732 
 ...  733     coverage_path.write_text(json.dumps(payload, indent=2) + "\n")
 ...  734     return coverage_path
 592  735 
 593  736 
 594  737 EXTRACTION_PROMPT = (

review/scripts/model-review.py --- 5/12 --- Python
 641     review_dir: Path,                784     review_dir: Path,
 642     dispatch_result: dict,           785     dispatch_result: dict,
 643 ) -> str | None:                     786 ) -> str | None:
 644     """Cross-family extraction: Fl   787     """Cross-family extraction: Fl
 ... ash extracts GPT outputs, GPT-Inst   ... ash extracts GPT outputs, GPT-Inst
 ... ant extracts Gemini outputs.         ... ant extracts Gemini outputs.
 645                                      788 
 646     Returns path to disposition.md   789     Returns path to disposition.md
 ... , or None if no outputs to extract   ... , or None if no outputs to extract
 ... .                                    ... .
 647     """                              790     Writes coverage.json whenever 
 ...                                      ... extraction tasks were attempted.
 ...                                      791     """
 648     extraction_tasks: list[tuple[s   792     extraction_tasks: list[tuple[s
 ... tr, Path, str]] = []  # (axis, out   ... tr, Path, str]] = []  # (axis, out
 ... put_path, profile)                   ... put_path, profile)
 649     skip_keys = {"review_dir", "ax   793     skip_keys = {"review_dir", "ax
 ... es", "queries", "elapsed_seconds"}   ... es", "queries", "elapsed_seconds"}
 650                                      794 

review/scripts/model-review.py --- 6/12 --- Python
 714  858                 axis_findings[axis] = findings
 715  859 
 716  860     if not axis_findings:
 ...  861         write_coverage_artifact(
 ...  862             review_dir,
 ...  863             dispatch_result,
 ...  864             extraction_tasks=extraction_tasks,
 ...  865             axis_findings={},
 ...  866             merged_findings=[],
 ...  867         )
 717  868         return None
 718  869 
 719  870     # Merge findings across axes — keyword overlap for cross-model dedup

review/scripts/model-review.py --- 7/12 --- Python
 804  955         f"Structured data: `findings.json`\n\n"
 805  956     )
 806  957     disposition.write_text(header + merged + response_template)
 ...  958     write_coverage_artifact(
 ...  959         review_dir,
 ...  960         dispatch_result,
 ...  961         extraction_tasks=extraction_tasks,
 ...  962         axis_findings=axis_findings,
 ...  963         merged_findings=merged_findings,
 ...  964         disposition_path=str(disposition),
 ...  965     )
 807  966     return str(disposition)
 808  967 
 809  968 

review/scripts/model-review.py --- 8/12 --- Python
 891 1050     confirmed = sum(1 for v in verified if v["verdict"] == "CONFIRMED")
 892 1051     hallucinated = sum(1 for v in verified if v["verdict"] == "HALLUCINATED")
 893 1052     unverifiable = sum(1 for v in verified if v["verdict"] == "UNVERIFIABLE")
 ... 1053     verification_summary = {
 ... 1054         "claim_count": len(verified),
 ... 1055         "confirmed_count": confirmed,
 ... 1056         "hallucinated_count": hallucinated,
 ... 1057         "unverifiable_count": unverifiable,
 ... 1058         "hallucination_rate": round(hallucinated / len(verified), 3) if verified else 0.0,
 ... 1059     }
 894 1060 
 895 1061     # Write verified disposition
 896 1062     out_path = review_dir / "verified-disposition.md"

review/scripts/model-review.py --- 9/12 --- Python
 916 1082         f"{unverifiable} unverifiable ({len(verified)} total)",
 917 1083         file=sys.stderr,
 918 1084     )
 ... 1085     write_coverage_artifact(
 ... 1086         review_dir,
 ... 1087         verification_summary=verification_summary,
 ... 1088         verified_disposition_path=str(out_path),
 ... 1089     )
 919 1090     return str(out_path)
 920 1091 
 921 1092 

review/scripts/model-review.py --- 10/12 --- Python
 935     parser.add_argument("--project  1106     parser.add_argument("--project
 ... ", type=Path, help="Project dir fo  .... ", type=Path, help="Project dir fo
 ... r constitution discovery (default:  .... r constitution discovery (default:
 ...  cwd)")                             ....  cwd)")
 936     parser.add_argument(            1107     parser.add_argument(
 937         "--axes", default="standar  1108         "--axes", default="standar
 ... d",                                 .... d",
 938         help="Comma-separated axes  1109         help="Comma-separated axes
 ...  or preset name (simple, standard,  ....  or preset name (standard, deep, f
 ...  deep, full). Default: standard",   .... ull). Default: standard",
 939     )                               1110     )
 ...                                     1111     parser.add_argument("--allow-n
 ...                                     .... on-gpt", action="store_true", help
 ...                                     .... =argparse.SUPPRESS)
 940     parser.add_argument(            1112     parser.add_argument(
 941         "--extract", action="store  1113         "--extract", action="store
 ... _true",                             .... _true",
 942         help="After dispatch, auto  1114         help="Explicitly enable ex
 ... -extract claims from each output i  .... traction. Extraction is the defaul
 ... nto disposition.md",                .... t user-facing path and emits dispo
 ...                                     .... sition.md plus coverage.json.",
 943     )                               1115     )
 ...                                     1116     parser.add_argument(
 ...                                     1117         "--no-extract", action="st
 ...                                     .... ore_true",
 ...                                     1118         help="Disable extraction f
 ...                                     .... or internal or debugging-only runs
 ...                                     .... .",
 ...                                     1119     )
 944     parser.add_argument(            1120     parser.add_argument(
 945         "--verify", action="store_  1121         "--verify", action="store_
 ... true",                              .... true",
 946         help="After extraction, ve  1122         help="After extraction, ve
 ... rify cited files/symbols exist. Im  .... rify cited files/symbols exist. Im
 ... plies --extract.",                  .... plies --extract.",

review/scripts/model-review.py --- 11/12 --- Python
 967         return 1                    1143         return 1
 968                                     1144 
 969     # Resolve axes                  1145     # Resolve axes
 970     if args.axes in PRESETS:        1146     try:
```

## Current File Excerpts

### shared/skill_manifest.py

```text
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.llm_dispatch import PROFILES

KNOWN_KINDS = {"worker", "orchestrator", "operator", "reference"}
KNOWN_INTENT_CLASSES = {
    "divergent",
    "convergent",
    "observational",
    "operator",
    "reference",
    "verification",
}
KNOWN_ENTRYPOINT_TYPES = {"script", "skill_doc", "manual"}
KNOWN_PACKET_BUILDERS = {
    "shared_context_packet",
    "plan_close_packet",
    "observe_transcript_packet",
    "brainstorm_context_packet",
    "overview_packet",
    "status_reconciliation_packet",
}
ARTIFACT_SCHEMAS: dict[str, dict[str, Any]] = {
    "review_coverage_v1": {
        "required_fields": [
            "schema",
            "topic",
            "mode",
            "axes",
            "claims",
            "verification",
            "packet",
        ]
    },
    "observe_signal_v1": {
        "required_fields": ["schema", "kind", "signal_id", "project", "source", "status"]
    },
    "observe_candidate_v1": {
        "required_fields": [
            "schema",
            "kind",
            "candidate_id",
            "project",
            "source_signal_ids",
            "state",
            "promoted",
            "checkable",
            "summary",
        ]
    },
    "brainstorm_matrix_v1": {
        "required_fields": [
            "idea_id",
            "source_artifact",
            "axis",
            "dominant_paradigm_escaped",
            "disposition",
        ]
    },
    "brainstorm_coverage_v1": {
        "required_fields": [
            "requested_axes",
            "executed_axes",
            "idea_count_by_axis",
            "uncovered_cells",
        ]
    },
    "status_reconciliation_v1": {
        "required_fields": [
            "stage",
            "mismatch_class",
            "live_state",
            "control_plane_state",
            "local_state",
        ]
    },
}


@dataclass(frozen=True)
class ManifestIssue:
    manifest_path: Path
    message: str


def iter_manifest_paths(root: Path) -> list[Path]:
    return sorted(root.glob("*/skill.json"))


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text())


def _expect_dict(value: Any, label: str, issues: list[ManifestIssue], manifest_path: Path) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    issues.append(ManifestIssue(manifest_path, f"{label} must be an object"))
    return {}


def _expect_list(value: Any, label: str, issues: list[ManifestIssue], manifest_path: Path) -> list[Any]:
    if isinstance(value, list):
        return value
    issues.append(ManifestIssue(manifest_path, f"{label} must be an array"))
    return []


def validate_manifest(manifest_path: Path, repo_root: Path) -> list[ManifestIssue]:
    issues: list[ManifestIssue] = []
    try:
        manifest = load_manifest(manifest_path)
    except json.JSONDecodeError as exc:
        return [ManifestIssue(manifest_path, f"invalid JSON: {exc}")]

    if not isinstance(manifest, dict):
        return [ManifestIssue(manifest_path, "manifest root must be an object")]

    skill_dir = manifest_path.parent.name
    name = manifest.get("name")
    if not isinstance(name, str) or not name:
        issues.append(ManifestIssue(manifest_path, "name must be a non-empty string"))
    elif name != skill_dir:
        issues.append(ManifestIssue(manifest_path, f"name must match skill dir '{skill_dir}'"))

    kind = manifest.get("kind")
    if kind not in KNOWN_KINDS:
        issues.append(
            ManifestIssue(
                manifest_path,
                f"kind must be one of {sorted(KNOWN_KINDS)}",
            )
        )

    intent_class = manifest.get("intent_class")
    if intent_class not in KNOWN_INTENT_CLASSES:
        issues.append(
            ManifestIssue(
                manifest_path,
                f"intent_class must be one o

... [truncated for review packet] ...

e(entrypoint_path, str) or not entrypoint_path:
        issues.append(ManifestIssue(manifest_path, "entrypoint.path must be a non-empty string"))
    else:
        resolved = repo_root / entrypoint_path
        if not resolved.exists():
            issues.append(
                ManifestIssue(manifest_path, f"entrypoint.path does not exist: {entrypoint_path}")
            )

    modes = _expect_dict(manifest.get("modes"), "modes", issues, manifest_path)
    if not modes:
        issues.append(ManifestIssue(manifest_path, "modes must declare at least one mode"))
    for mode_name, raw_mode in sorted(modes.items()):
        mode = _expect_dict(raw_mode, f"modes.{mode_name}", issues, manifest_path)
        mode_intent = mode.get("intent_class")
        if mode_intent not in KNOWN_INTENT_CLASSES:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"modes.{mode_name}.intent_class must be one of {sorted(KNOWN_INTENT_CLASSES)}",
                )
            )
        artifacts = _expect_list(mode.get("artifacts"), f"modes.{mode_name}.artifacts", issues, manifest_path)
        if not artifacts:
            issues.append(ManifestIssue(manifest_path, f"modes.{mode_name} must declare artifacts"))
        elif not all(isinstance(item, str) and item for item in artifacts):
            issues.append(
                ManifestIssue(manifest_path, f"modes.{mode_name}.artifacts must contain strings")
            )

    uses = _expect_dict(manifest.get("uses"), "uses", issues, manifest_path)
    dispatch_profiles = _expect_list(uses.get("dispatch_profiles", []), "uses.dispatch_profiles", issues, manifest_path)
    for profile_name in dispatch_profiles:
        if profile_name not in PROFILES:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown dispatch profile '{profile_name}'",
                )
            )

    packet_builders = _expect_list(uses.get("packet_builders", []), "uses.packet_builders", issues, manifest_path)
    for builder_name in packet_builders:
        if builder_name not in KNOWN_PACKET_BUILDERS:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown packet builder '{builder_name}'",
                )
            )

    artifact_schemas = _expect_list(uses.get("artifact_schemas", []), "uses.artifact_schemas", issues, manifest_path)
    for schema_name in artifact_schemas:
        if schema_name not in ARTIFACT_SCHEMAS:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown artifact schema '{schema_name}'",
                )
            )

    follow_on = _expect_list(manifest.get("follow_on", []), "follow_on", issues, manifest_path)
    if follow_on and not all(isinstance(item, str) and item for item in follow_on):
        issues.append(ManifestIssue(manifest_path, "follow_on must contain non-empty strings"))

    references = _expect_list(manifest.get("references", []), "references", issues, manifest_path)
    for reference_path in references:
        if not isinstance(reference_path, str) or not reference_path:
            issues.append(ManifestIssue(manifest_path, "references must contain non-empty strings"))
            continue
        resolved = repo_root / reference_path
        if not resolved.exists():
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"reference does not exist: {reference_path}",
                )
            )

    return issues


def validate_repo_manifests(repo_root: Path, manifest_paths: list[Path] | None = None) -> list[ManifestIssue]:
    paths = manifest_paths or iter_manifest_paths(repo_root)
    issues: list[ManifestIssue] = []
    for manifest_path in paths:
        issues.extend(validate_manifest(manifest_path, repo_root))
    return issues
```

### scripts/lint_skill_manifests.py

```text
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.skill_manifest import iter_manifest_paths, validate_repo_manifests


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill manifests")
    parser.add_argument(
        "--manifest",
        action="append",
        type=Path,
        help="Validate only the given manifest path(s)",
    )
    args = parser.parse_args()

    manifest_paths = args.manifest
    if manifest_paths is None:
        manifest_paths = iter_manifest_paths(ROOT)
    issues = validate_repo_manifests(ROOT, manifest_paths)
    if issues:
        for issue in issues:
            rel_path = issue.manifest_path.relative_to(ROOT)
            print(f"{rel_path}: {issue.message}", file=sys.stderr)
        return 1

    for manifest_path in manifest_paths:
        rel_path = manifest_path.relative_to(ROOT)
        print(f"OK {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### scripts/test_skill_manifest.py

```text
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from shared.skill_manifest import validate_manifest


class SkillManifestTest(unittest.TestCase):
    def test_validate_manifest_accepts_known_profile_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "foo").mkdir()
            (root / "foo" / "SKILL.md").write_text("# Foo\n")
            (root / "foo" / "run.py").write_text("print('ok')\n")
            (root / "foo" / "skill.json").write_text(
                """
                {
                  "name": "foo",
                  "kind": "worker",
                  "intent_class": "convergent",
                  "summary": "x",
                  "entrypoint": {"type": "script", "path": "foo/run.py"},
                  "modes": {
                    "main": {
                      "intent_class": "convergent",
                      "requires_packet": true,
                      "requires_gpt": true,
                      "artifacts": ["out.md"]
                    }
                  },
                  "uses": {
                    "dispatch_profiles": ["formal_review"],
                    "packet_builders": ["shared_context_packet"],
                    "artifact_schemas": ["review_coverage_v1"]
                  },
                  "follow_on": ["upgrade"],
                  "references": ["foo/SKILL.md"]
                }
                """.strip()
            )
            issues = validate_manifest(root / "foo" / "skill.json", root)
            self.assertEqual(issues, [])

    def test_validate_manifest_rejects_unknown_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "foo").mkdir()
            (root / "foo" / "SKILL.md").write_text("# Foo\n")
            (root / "foo" / "run.py").write_text("print('ok')\n")
            manifest_path = root / "foo" / "skill.json"
            manifest_path.write_text(
                """
                {
                  "name": "foo",
                  "kind": "worker",
                  "intent_class": "convergent",
                  "summary": "x",
                  "entrypoint": {"type": "script", "path": "foo/run.py"},
                  "modes": {"main": {"intent_class": "convergent", "artifacts": ["out.md"]}},
                  "uses": {"dispatch_profiles": ["not_real"], "packet_builders": [], "artifact_schemas": []},
                  "follow_on": [],
                  "references": ["foo/SKILL.md"]
                }
                """.strip()
            )
            issues = validate_manifest(manifest_path, root)
            self.assertTrue(any("unknown dispatch profile" in issue.message for issue in issues))


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
from shared.context_budget import enforce_budget
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
{con

... [truncated for review packet] ...

age.json.",
    )
    parser.add_argument(
        "--no-extract", action="store_true",
        help="Disable extraction for internal or debugging-only runs.",
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
    try:
        axis_names = resolve_axes(args.axes, allow_non_gpt=bool(args.allow_non_gpt))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.no_extract and args.verify:
        print("error: --verify cannot be combined with --no-extract", file=sys.stderr)
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

    do_extract = not args.no_extract or args.verify

    # Optional extraction phase
    if do_extract:
        disposition_path = extract_claims(review_dir, result)
        coverage_path = review_dir / "coverage.json"
        if coverage_path.exists():
            result["coverage"] = str(coverage_path)
            print(f"Coverage written to {coverage_path}", file=sys.stderr)
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
import json
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
           

... [truncated for review packet] ...

             "--topic", "empty-axis", "--project", str(project_dir),
                     ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 2)

    def test_main_rejects_verify_with_no_extract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")
            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review.sys, "argv", [
                    "model-review.py",
                    "--context", str(context_path),
                    "--topic", "invalid",
                    "--project", str(project_dir),
                    "--verify",
                    "--no-extract",
                ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 1)

    def test_main_rejects_non_gpt_axes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review.sys, "argv", [
                    "model-review.py",
                    "--context", str(context_path),
                    "--topic", "non-gpt",
                    "--project", str(project_dir),
                    "--axes", "arch,domain,mechanical",
                ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 1)


class ModelReviewContextBuildTest(unittest.TestCase):
    def test_build_context_drops_file_specs_when_budget_is_tiny(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            project_dir = root / "project"
            project_dir.mkdir()
            context_file = project_dir / "context.txt"
            context_file.write_text("A" * 4000)

            ctx_files = model_review.build_context(
                review_dir,
                project_dir,
                context_file=None,
                axis_names=["formal"],
                context_file_specs=[str(context_file)],
                budget_limit_override=120,
            )

            shared_ctx = ctx_files["formal"]
            manifest = json.loads(shared_ctx.manifest_path.read_text())
            dropped = manifest["packet_metadata"]["budget_enforcement"]["dropped_blocks"]
            self.assertTrue(dropped)
            self.assertEqual(dropped[0]["block_title"], str(context_file))

    def test_build_context_keeps_explicit_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            project_dir = root / "project"
            project_dir.mkdir()
            context_file = project_dir / "assembled.md"
            context_file.write_text("B" * 4000)

            ctx_files = model_review.build_context(
                review_dir,
                project_dir,
                context_file=context_file,
                axis_names=["formal"],
                budget_limit_override=120,
            )

            shared_ctx = ctx_files["formal"]
            manifest = json.loads(shared_ctx.manifest_path.read_text())
            dropped = manifest["packet_metadata"]["budget_enforcement"]["dropped_blocks"]
            self.assertEqual(dropped, [])
            self.assertIn(str(context_file), shared_ctx.content_path.read_text())


if __name__ == "__main__":
    unittest.main()
```

### observe/scripts/observe_artifacts.py

```text
#!/usr/bin/env python3
"""Shared paths and JSONL helpers for observe artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = Path.home() / "Projects" / "meta"
ARTIFACT_SUBDIR = Path("artifacts") / "observe"

MANIFEST_JSON = "manifest.json"
INPUT_MD = "input.md"
CODEX_MD = "codex.md"
COVERAGE_DIGEST_TXT = "coverage-digest.txt"
OPERATIONAL_CONTEXT_TXT = "operational-context.txt"
GEMINI_OUTPUT_MD = "gemini-output.md"
GEMINI_OUTPUT_META_JSON = "gemini-output.meta.json"
GEMINI_OUTPUT_ERROR_JSON = "gemini-output.error.json"
DISPATCH_META_JSON = "dispatch.meta.json"
SIGNALS_JSONL = "signals.jsonl"
CANDIDATES_JSONL = "candidates.jsonl"
PATTERNS_JSONL = "patterns.jsonl"
LAST_SYNTHESIS_MD = "last-synthesis.md"
DIGEST_MD = "digest.md"

OBSERVE_ARTIFACT_ROOT_ENV = "OBSERVE_ARTIFACT_ROOT"
OBSERVE_PROJECT_ROOT_ENV = "OBSERVE_PROJECT_ROOT"


def project_root() -> Path:
    """Resolve the canonical workspace root for observe outputs."""
    env_root = os.environ.get(OBSERVE_PROJECT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser()

    env_artifact_root = os.environ.get(OBSERVE_ARTIFACT_ROOT_ENV)
    if env_artifact_root:
        artifact_dir = Path(env_artifact_root).expanduser()
        if len(artifact_dir.parents) >= 2:
            return artifact_dir.parents[1]
        return artifact_dir.parent

    return DEFAULT_PROJECT_ROOT


def artifact_root() -> Path:
    """Resolve the canonical observe artifact directory."""
    env_root = os.environ.get(OBSERVE_ARTIFACT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser()
    return project_root() / ARTIFACT_SUBDIR


def artifact_path(*parts: str) -> Path:
    """Join a path under the canonical artifact root."""
    return artifact_root().joinpath(*parts)


def improvement_log_path() -> Path:
    """Canonical improvement log used by sessions and supervision modes."""
    return project_root() / "improvement-log.md"


def stable_id(prefix: str, *parts: str, length: int = 12) -> str:
    """Create a stable short identifier from a sequence of string parts."""
    digest_input = "\x1f".join(parts).encode("utf-8")
    digest = hashlib.sha1(digest_input).hexdigest()[:length]
    return f"{prefix}_{digest}"


def jsonl_line(record: dict[str, Any]) -> str:
    """Serialize one JSONL record with stable key ordering."""
    return json.dumps(record, sort_keys=True, ensure_ascii=True)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSONL record, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(jsonl_line(record))
        handle.write("\n")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write a full JSONL file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(jsonl_line(record))
            handle.write("\n")
```

### observe/scripts/session-shape.py

```text
#!/usr/bin/env python3
"""Session shape detector — zero-LLM-cost structural anomaly detection.

Analyzes session topology (tool patterns, message ratios, structural signals)
to flag anomalous sessions worth deep analysis. The deterministic output can
also be written as observe signal/candidate JSONL records for backlog staging.

Usage:
    session-shape.py [--days N] [--project P] [--threshold T] [--json]
        [--signals-out PATH] [--candidates-out PATH]
"""

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, stdev

import os

from observe_artifacts import (
    append_jsonl,
    artifact_path,
    stable_id,
)

# Inlined from meta/scripts/common/paths.py and meta/scripts/config.py
_CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", str(Path.home() / ".claude")))
DB_PATH = _CLAUDE_DIR / "runlogs.db"
_METRICS_FILE = _CLAUDE_DIR / "epistemic-metrics.jsonl"


def log_metric(metric_name: str, **fields) -> None:
    """Append a metric entry to epistemic-metrics.jsonl."""
    entry = {"ts": datetime.now().isoformat(), "metric": metric_name, **fields}
    with open(_METRICS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _open_db(path: Path, *, wal: bool = True) -> sqlite3.Connection:
    """Open SQLite DB with consistent policy defaults."""
    path = Path(path)
    db = sqlite3.connect(str(path), timeout=5.0, isolation_level="DEFERRED")
    db.row_factory = sqlite3.Row
    if wal:
        db.execute("PRAGMA journal_mode=WAL")
    return db

# Structural features extracted per session
FEATURE_NAMES = [
    "tool_diversity",       # unique tools / total tool calls
    "read_write_ratio",     # reads / (writes + edits + 1)
    "bash_fraction",        # bash calls / total tool calls
    "agent_fraction",       # agent calls / total tool calls
    "search_density",       # (grep + glob + web) / total
    "transcript_density",   # transcript lines / duration minutes
    "tool_intensity",       # total tool calls / duration minutes
    "mcp_fraction",         # mcp tool calls / total
    "commit_ratio",         # commits / edits
    "read_only_flag",       # 1 if zero writes/edits, else 0
]


@dataclass
class SessionShape:
    uuid: str
    project: str
    start_ts: str
    first_message: str
    duration_min: float
    cost_usd: float
    features: dict = field(default_factory=dict)
    anomaly_score: float = 0.0
    anomaly_reasons: list = field(default_factory=list)


def extract_features(row: sqlite3.Row) -> dict:
    """Extract structural features from a session row."""
    tools_raw = row["tools_used"]
    tools = json.loads(tools_raw) if tools_raw else []
    total_tools = len(tools)

    # Count tool categories
    reads = sum(1 for t in tools if t in ("Read", "Glob", "Grep"))
    writes = sum(1 for t in tools if t in ("Write", "Edit", "NotebookEdit"))
    bashes = sum(1 for t in tools if t == "Bash")
    agents = sum(1 for t in tools if t == "Agent")
    searches = sum(1 for t in tools if t in ("Grep", "Glob", "WebSearch", "WebFetch"))
    mcps = sum(1 for t in tools if t.startswith("mcp__"))

    unique_tools = len(set(tools))
    duration = max(row["duration_min"] or 1.0, 0.1)
    transcript_lines = row["transcript_lines"] or 0

    commits_raw = row["commits"]
    commits = json.loads(commits_raw) if commits_raw else []

    return {
        "tool_diversity": unique_tools / max(total_tools, 1),
        "read_write_ratio": reads / max(writes + 1, 1),
        "bash_fraction": bashes / max(total_tools, 1),
        "agent_fraction": agents / max(total_tools, 1),
        "search_density": searches / max(total_tools, 1),
        "transcript_density": transcript_lines / duration,
        "tool_intensity": total_tools / duration,
        "mcp_fraction": mcps / max(total_tools, 1),
        "commit_ratio": len(commits) / max(writes + 1, 1),
        "rea

... [truncated for review packet] ...

 JSONL",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("Runlogs DB not found. Run: uv run python3 scripts/runlog.py import && uv run python3 scripts/sessions.py index", file=sys.stderr)
        sys.exit(1)

    db = _open_db(DB_PATH)

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    query = """
        SELECT vendor_session_id AS uuid, project_slug AS project, started_at AS start_ts, first_message, duration_min, cost_usd,
               tools_used, commits, transcript_lines
        FROM sessions
        WHERE vendor = 'claude'
          AND client = 'claude-code'
          AND jsonl_path IS NOT NULL
          AND started_at >= ?
          AND duration_min IS NOT NULL
          AND duration_min > 0.5
    """
    params = [since]
    if args.project:
        query += " AND project = ?"
        params.append(args.project)
    query += " ORDER BY started_at DESC"

    rows = db.execute(query, params).fetchall()
    if not rows:
        print("No sessions found in the given period.", file=sys.stderr)
        sys.exit(0)

    # Extract features
    shapes = []
    for row in rows:
        shape = SessionShape(
            uuid=row["uuid"],
            project=row["project"] or "unknown",
            start_ts=row["start_ts"] or "",
            first_message=(row["first_message"] or "")[:80],
            duration_min=row["duration_min"] or 0,
            cost_usd=row["cost_usd"] or 0,
            features=extract_features(row),
        )
        shapes.append(shape)

    # Compute anomalies
    shapes = compute_anomalies(shapes, threshold=args.threshold)
    signal_shapes = list(shapes)

    # Filter to anomalies unless --all
    anomalous = len([s for s in shapes if s.anomaly_score > 0])
    if not args.all:
        shapes = [s for s in shapes if s.anomaly_score > 0]

    # Sort by anomaly score descending
    shapes.sort(key=lambda s: s.anomaly_score, reverse=True)

    if args.json:
        output = []
        for s in shapes:
            output.append({
                "uuid": s.uuid[:8],
                "project": s.project,
                "date": s.start_ts[:10],
                "anomaly_score": round(s.anomaly_score, 2),
                "reasons": s.anomaly_reasons,
                "first_message": s.first_message,
                "features": {k: round(v, 3) for k, v in s.features.items()},
            })
        print(json.dumps(output, indent=2))
    else:
        total = len(rows)
        anomalous = len([s for s in shapes if s.anomaly_score > 0]) if args.all else len(shapes)
        print(f"Sessions: {total} total, {anomalous} anomalous (threshold z>{args.threshold})")
        print()

        if not shapes:
            print("No anomalous sessions found.")
            return

        for s in shapes[:20]:
            score_bar = "█" * min(int(s.anomaly_score), 20)
            print(f"{s.uuid[:8]}  {s.start_ts[:10]}  {s.project:<12}  "
                  f"${s.cost_usd:>5.2f}  {s.duration_min:>5.1f}m  "
                  f"score={s.anomaly_score:>5.1f}  {score_bar}")
            for reason in s.anomaly_reasons[:3]:
                print(f"  ↳ {reason}")
            print(f"  {s.first_message}")
            print()

    signals_out = args.signals_out or artifact_path("signals.jsonl")
    candidates_out = args.candidates_out or artifact_path("candidates.jsonl")
    for shape in signal_shapes:
        append_jsonl(signals_out, build_signal_record(shape, threshold=args.threshold))
        if shape.anomaly_score > 0:
            append_jsonl(candidates_out, build_candidate_record(shape, threshold=args.threshold))

    # Log metric
    log_metric("session_shape",
               sessions_scanned=len(rows),
               anomalies_found=anomalous if not args.all else len([s for s in shapes if s.anomaly_score > 0]),
               threshold=args.threshold,
               days=args.days)

    db.close()


if __name__ == "__main__":
    main()
```

### observe/scripts/session_shape.py

```text
"""Importable wrapper around `session-shape.py`.

The CLI entrypoint stays hyphenated for compatibility with existing shell
invocations. This adapter gives tests and future code a stable module name.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_IMPL_PATH = Path(__file__).with_name("session-shape.py")
_SPEC = spec_from_file_location("observe_session_shape_impl", _IMPL_PATH)
assert _SPEC and _SPEC.loader
_IMPL = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_IMPL)

for _name in dir(_IMPL):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_IMPL, _name)
```

### observe/scripts/validate_session_ids.py

```text
#!/usr/bin/env python3
"""Validate session IDs in Gemini output against the extraction manifest.

Reads input.md for the VALID SESSION IDS table, then checks gemini-output.md
for any 8-char hex patterns that aren't in the allowlist. Reports fabricated
IDs and optionally strips them from findings.

Usage:
    python validate_session_ids.py [--input FILE] [--output FILE] [--strip]

Defaults to the canonical observe artifact root.
"""

import argparse
import re
import sys
from pathlib import Path

from observe_artifacts import artifact_root

HEX8_PATTERN = re.compile(r"\b([0-9a-f]{8})\b")
MANIFEST_ROW = re.compile(r"\|\s*([0-9a-f]{8})\s*\|")


def extract_manifest(input_text: str) -> set[str]:
    """Extract valid session ID prefixes from the VALID SESSION IDS table."""
    return set(MANIFEST_ROW.findall(input_text))


def extract_referenced_ids(gemini_text: str) -> set[str]:
    """Extract all 8-char hex strings from Gemini output."""
    return set(HEX8_PATTERN.findall(gemini_text))


def validate(input_path: Path, gemini_path: Path) -> dict:
    """Validate Gemini output IDs against manifest. Returns report dict."""
    input_text = input_path.read_text()
    gemini_text = gemini_path.read_text()

    valid_ids = extract_manifest(input_text)
    referenced_ids = extract_referenced_ids(gemini_text)

    # Only flag hex strings that appear near session-referencing context
    # (not random hex in code snippets, hashes, etc.)
    session_context = re.compile(
        r"(?:session|Session|SESSION|uuid|UUID)\s*[:=]?\s*\b([0-9a-f]{8})\b"
        r"|\*\*Session:\*\*\s*\b([0-9a-f]{8})\b"
    )
    contextual_ids = set()
    for m in session_context.finditer(gemini_text):
        contextual_ids.add(m.group(1) or m.group(2))

    fabricated = contextual_ids - valid_ids
    valid_refs = contextual_ids & valid_ids
    unreferenced = valid_ids - contextual_ids

    return {
        "valid_ids": sorted(valid_ids),
        "referenced_ids": sorted(contextual_ids),
        "fabricated": sorted(fabricated),
        "valid_refs": sorted(valid_refs),
        "unreferenced": sorted(unreferenced),
    }


def strip_fabricated(gemini_text: str, fabricated: set[str]) -> str:
    """Replace fabricated session IDs with [FABRICATED_ID]."""
    result = gemini_text
    for fid in fabricated:
        result = result.replace(fid, "[FABRICATED_ID]")
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate session IDs in Gemini output")
    parser.add_argument("--artifact-root", type=Path, help="Override the observe artifact root")
    parser.add_argument("--input", "-i", type=Path, help="Input transcript markdown")
    parser.add_argument("--gemini", "-g", type=Path, help="Gemini output markdown")
    parser.add_argument("--strip", action="store_true", help="Replace fabricated IDs in output")
    parser.add_argument("--output", "-o", type=Path, help="Write stripped output to file")
    args = parser.parse_args()

    root = args.artifact_root or artifact_root()
    input_path = args.input or (root / "input.md")
    gemini_path = args.gemini or (root / "gemini-output.md")

    if not input_path.exists():
        print(f"✗ Input not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    if not gemini_path.exists():
        print(f"✗ Gemini output not found: {gemini_path}", file=sys.stderr)
        sys.exit(1)

    report = validate(input_path, gemini_path)

    print(f"  Manifest IDs: {len(report['valid_ids'])} {report['valid_ids']}")
    print(f"  Referenced:   {len(report['referenced_ids'])} {report['referenced_ids']}")

    if report["fabricated"]:
        print(f"  ✗ Fabricated: {len(report['fabricated'])} {report['fabricated']}")
    else:
        print(f"  ✓ No fabricated session IDs")

    if report["unreferenced"]:
        print(f"  ! Unreferenced sessions: {report['unreferenced']}")

    if args.strip and report["fabricated"]:
        gemini_text = gemini_path.read_text()
        cleaned = strip_fabricated(gemini_text, set(report["fabricated"]))
        out_path = args.output or gemini_path
        out_path.write_text(cleaned)
        print(f"  ✓ Stripped {len(report['fabricated'])} fabricated IDs → {out_path}")

    sys.exit(1 if report["fabricated"] else 0)


if __name__ == "__main__":
    main()
```

### brainstorm/tests/test_brainstorm_contract.py

```text
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DOC = ROOT / "SKILL.md"
SKILL_MANIFEST = ROOT / "skill.json"
DISPATCH_REF = ROOT / "references" / "llmx-dispatch.md"
TEMPLATES_REF = ROOT / "references" / "synthesis-templates.md"
DOMAIN_POOLS_REF = ROOT / "references" / "domain-pools.md"


class BrainstormContractTest(unittest.TestCase):
    def test_docs_match_structured_artifact_contract(self) -> None:
        skill_text = SKILL_DOC.read_text()
        dispatch_text = DISPATCH_REF.read_text()
        templates_text = TEMPLATES_REF.read_text()
        manifest = json.loads(SKILL_MANIFEST.read_text())

        self.assertEqual(
            manifest["modes"]["default"]["artifacts"],
            ["synthesis.md", "matrix.json", "matrix.md", "coverage.json"],
        )
        self.assertIn("matrix.json", skill_text)
        self.assertIn("coverage.json", skill_text)
        self.assertIn("matrix.json", dispatch_text)
        self.assertIn("coverage.json", dispatch_text)
        self.assertIn("matrix.json", templates_text)
        self.assertIn("coverage.json", templates_text)

    def test_docs_do_not_teach_raw_llmx_chat_commands(self) -> None:
        combined = "\n".join(
            [
                SKILL_DOC.read_text(),
                DISPATCH_REF.read_text(),
                TEMPLATES_REF.read_text(),
            ]
        )

        self.assertNotIn("llmx chat", combined)
        self.assertNotIn("llmx chat -m", combined)

    def test_docs_preserve_divergent_boundary_and_domain_row_tracking(self) -> None:
        skill_text = SKILL_DOC.read_text()
        dispatch_text = DISPATCH_REF.read_text()
        domain_pools_text = DOMAIN_POOLS_REF.read_text()

        self.assertIn("/model-review", skill_text)
        self.assertIn("caller_evidence", dispatch_text)
        self.assertIn("speculative", dispatch_text)
        self.assertIn("domain_row", dispatch_text)
        self.assertIn("domain_row", domain_pools_text)


if __name__ == "__main__":
    unittest.main()
```

### scripts/test_modal_attribution_contract.py

```text
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODAL_SKILL = ROOT / "modal" / "SKILL.md"
MODAL_ATTRIBUTION = ROOT / "modal" / "references" / "attribution.md"
MODAL_RESOURCES = ROOT / "modal" / "references" / "resources.md"


class ModalAttributionContractTest(unittest.TestCase):
    def test_modal_docs_explain_question_source_status_spend(self) -> None:
        skill_text = MODAL_SKILL.read_text()
        attribution_text = MODAL_ATTRIBUTION.read_text()
        resources_text = MODAL_RESOURCES.read_text()

        self.assertIn("operational question", skill_text)
        self.assertIn("truth surface", skill_text)
        self.assertIn("billing question", skill_text)
        self.assertIn("synthetic status", skill_text)
        self.assertIn("Question -> Source -> Status -> Spend", attribution_text)
        self.assertIn("status and spend", resources_text)
        self.assertIn("question_id", attribution_text)
        self.assertIn("run_id", attribution_text)
        self.assertIn("stage", attribution_text)


if __name__ == "__main__":
    unittest.main()
```

### research-ops/SKILL.md

```text
---
name: research-ops
description: "Use when: 'run research cycle', 'compile memos into article', 'what's not in training data', 'dispatch parallel audit'. Autonomous research loops, knowledge compilation, training-data diff. For one-shot research questions use /research."
user-invocable: true
argument-hint: <mode> [topic]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent, WebSearch, WebFetch]
effort: high
---

# Research Ops

Operator-initiated research workflows. For one-shot research questions, use `/research`.

| Mode | Trigger | What it does |
|------|---------|--------------|
| `cycle` | `/research-ops cycle` | Autonomous discover/gap/plan/review/execute/verify loop via `/loop 15m` |
| `compile` | `/research-ops compile <concept>` | Synthesize memos into unified article |
| `diff` | `/research-ops diff <text or path>` | Extract what's NOT in training data |
| `dispatch` | `/research-ops dispatch [depth]` | Parallel audit sweep |

---

# Mode: cycle

You run on `/loop`. Each tick you read state, pick the next phase, and execute it — via subagent (preferred, fresh context) or inline (if memory-constrained). **Never ask for input.** The human steers by editing CYCLE.md between ticks.

## Live State

!`bash ${CLAUDE_SKILL_DIR}/scripts/gather-cycle-state.sh "$(pwd)" 2>&1 | head -80`

## Rate Limit Detection

Before each tick, check rate limit status:
```bash
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
```

**If rate-limited (CLAUDE_PROCS >= 6):** Route LLM-heavy phases (discover, gap-analyze, plan) through the shared dispatch helper instead of Claude subagents:
- Use `uv run python3 ~/Projects/skills/scripts/llm-dispatch.py --profile cheap_tick ...` for discover/gap-analyze (shared artifact contract, no raw CLI dispatch)
- Use `model-review.py` for review (already routes through llmx)
- Execute and verify phases use tools, not LLM reasoning — run inline regardless
- Write `[rate-limited: used shared dispatch]` tag in CYCLE.md log entries for tracking

**If not rate-limited:** Normal operation (Claude subagents preferred).

## Each Tick

If "NO STATE CHANGE" -> one-line noop, stop.

Otherwise, pick the highest-priority phase and run it. **Chain phases** if confident — don't wait for the next tick when the next phase has no blockers. Stop chaining when: rate-limited, context is heavy (>60% used), or the next phase needs external data you don't have yet.

### Phase Priority (first match wins)

1. **Recent execution without verification** -> run verify (always verify before executing more)
2. **Items in queue** (CYCLE.md `## Queue`) -> run execute. The queue IS the approval — items land there via human steering or gap-analyze. No `[x] APPROVE` gate needed.
3. **Active plan not yet reviewed** -> run review (probe claims + cross-model via `model-review.py`)
4. **Gaps exist without plan** -> run plan phase (write plan for top gap)
5. **Discoveries exist without gap analysis** -> run gap-analyze
6. **Verification done without improve** -> run improve (includes retro + archival)
7. **Nothing pending** -> run discover (includes brainstorm if discover returns empty)

### Running a Phase

**Route by task type, not line count:**
- Docstring, config, research_only field changes -> **inline** (fast, reliable)
- Logic changes, even 1-line -> **subagent** (fresh context for reasoning about consequences)
- If subagent returns empty (no edit), retry inline once

**Subagent dispatch (normal mode):**
```
Agent(
  prompt="[phase prompt with project context]",
  subagent_type="general-purpose",
  description="research-cycle: [phase]",
  mode="bypassPermissions"
)
```

**Shared dispatch (rate-limited mode):** For discover/gap-analyze/plan phases, write the phase prompt to a temp file and dispatch via the wrapper:
```bash
cat > /tmp/cycle-phase-prompt.md << 'EOF'
[phase prompt with project context]
EOF
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile cheap_tick \
  --context /tmp/c

... [truncated for review packet] ...

ns filling it in. Failed 3/4 sessions. Use `-o FILE` instead — captures final text message automatically.

**Memory pressure gate:** Before dispatching, count active processes (`pgrep -lf claude | wc -l`, NOT `pgrep -c` on macOS). If >= 4, reduce to sequential or audit directly.

**MCP contention:** Max 4 parallel Codex agents. Each starts 9 MCP servers. 5+ agents = 132+ simultaneous startups = system overwhelm.

**Output preservation:** Tell agents to write to `docs/audit/`, NOT `/tmp`. Immediately `git add` or `cp` after completion — sandbox cleanup can delete files. Do NOT use `--ephemeral` (deletes `-o` output).

**Verification is mandatory (Phase 3).** ~28% error rate concentrated in counts, severity, external knowledge. Code-grounded findings (file:line) are consistently reliable. See `references/verification-procedure.md` for checklist and hallucination patterns.

**S2 API outages:** Tell agents to fall back to `backend="openalex"` or exa if Semantic Scholar returns 403.

## Model selection

| Target | When | Tradeoff |
|--------|------|----------|
| `codex exec --model gpt-5.4` | Cross-referencing, counting, structured output | Free, parallel, output extraction fragile |
| Claude Code `Agent` subagents | Same + DuckDB/MCP access | Costs tokens, output inline (reliable) |
| `uv run python3 ~/Projects/skills/scripts/llm-dispatch.py --profile deep_review ...` | 1M context, huge file ingestion | Best for monolithic analysis |

**Use Codex for:** 5+ parallel audits, cross-file grep+read tracing, wiring/drift/completeness checks.
**Use Claude subagents for:** <3 file audits, tasks needing project-specific tooling (uv, DuckDB, MCP).

## Phase-by-phase execution

**Phase 1 -- Recon:** Read CLAUDE.md, `.claude/overviews/`, plans, `git log --oneline -30`, `docs/audit/` (skip completed). Build mental model, identify audit targets.

**Phase 2 -- Dispatch:** Craft self-contained prompts per `references/prompt-construction.md`. Execute per `references/codex-dispatch-mechanics.md`. Each prompt: "Read [files], check [properties], cross-reference [A vs B], cite file:line."

**Phase 3 -- Verify:** Every finding checked against actual code. Follow `references/verification-procedure.md`. Output: confirmed / rejected (with reason) / corrected findings.

**Phase 4 -- Plan:** Synthesize into phased execution plan per `references/plan-and-execute.md`. Fix ALL verified findings -- don't self-select "top N." Present to user; wait for approval.

**Phase 5 -- Execute:** Implement per `references/plan-and-execute.md`. Read before editing. One commit per logical change. If other agents active, commit after each fix (not batched) or use `isolation: worktree`.

## References (loaded on demand)

| File | Contents |
|------|----------|
| `references/prompt-construction.md` | Target selection categories, prompt structure, good/bad patterns |
| `references/codex-dispatch-mechanics.md` | Bash commands, flags, MCP config, `-o` caveats, fallback |
| `references/verification-procedure.md` | Verification checklist, hallucination pattern table, output format |
| `references/plan-and-execute.md` | Plan template, plan principles, execution principles, MAINTAIN.md integration |
| `references/paper-reading-dispatch.md` | DOI handling, S2 fallbacks, turn budget, GPT-5.4 strengths/weaknesses for papers |
| `references/agent-system-prompt.md` | Full system prompt for subagent dispatch |

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Commit contamination — when dispatch-research agents don't use worktree isolation, their uncommitted changes get swept into the parent session's next commit.**

---

$ARGUMENTS

<!-- knowledge-index
generated: 2026-04-08T21:42:46Z
hash: fce0e32de4a2

cross_refs: docs/compiled/{concept-slug}.md, docs/research/*.md, research/*.md, research/adversarial-case-library.md, research/compiled/{concept-slug}.md
sources: 1
  DATA: BASE: name
table_claims: 8

end-knowledge-index -->
```
```
