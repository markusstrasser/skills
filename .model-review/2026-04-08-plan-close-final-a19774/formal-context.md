# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler/hacky approaches because they're 'faster to implement'
- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort
- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters

# Plan Close: llmx Python API Migration + Kimi Removal

## Scope
Personal infrastructure, one operator, 6 projects. Agent-built, human-steered.

## What changed (this session)
review/scripts/model-review.py --- 1/13 --- Python
 24 import json                           24 import json
 25 import os                             25 import os
 26 import re                             26 import re
 27 import subprocess                     .. 
 28 import sys                            27 import sys
 29 import time                           28 import time
 ..                                       29 from concurrent.futures import Thre
 ..                                       .. adPoolExecutor, as_completed
 30 from datetime import date             30 from datetime import date
 31 from pathlib import Path              31 from pathlib import Path
 ..                                       32 
 ..                                       33 # llmx is editable-installed as a u
 ..                                       .. v tool; bootstrap from its venv if 
 ..                                       .. not importable
 ..                                       34 try:
 ..                                       35     from llmx.api import chat as ll
 ..                                       .. mx_chat
 ..                                       36 except ImportError:
 ..                                       37     import glob
 ..                                       38     _tool_site = glob.glob(str(Path
 ..                                       .. .home() / ".local/share/uv/tools/ll
 ..                                       .. mx/lib/python*/site-packages"))
 ..                                       39     if _tool_site:
 ..                                       40         sys.path.insert(0, _tool_si
 ..                                       .. te[0])
 ..                                       41     sys.path.insert(0, str(Path.hom
 ..                                       .. e() / "Projects" / "llmx"))
 ..                                       42     from llmx.api import chat as ll
 ..                                       .. mx_chat
 ..                                       43 
 ..                                       44 # --- Structured output schema (bot
 ..                                       .. h models return this) ---
 ..                                       45 
 ..                                       46 FINDING_SCHEMA = {
 ..                                       47     "type": "object",
 ..                                       48     "properties": {
 ..                                       49         "findings": {
 ..                                       50             "type": "array",
 ..                                       51             "items": {
 ..                                       52                 "type": "object",
 ..                                       53                 "properties": {
 ..                                       54                     "category": {
 ..                                       55                         "type": "st
 ..                                       .. ring",
 ..                                       56                         "enum": ["b
 ..                                       .. ug", "logic", "architecture", "miss
 ..                                       .. ing", "performance", "security", "s
 ..                                       .. tyle", "constitutional"],
 ..                                       57                     },
 ..                                       58                     "severity": {"t
 ..                                       .. ype": "string", "enum": ["critical"
 ..                                       .. , "high", "medium", "low"]},
 ..                                       59                     "title": {"type
 ..                                       .. ": "string", "description": "One-li
 ..                                       .. ne summary"},
 ..                                       60                     "description": 
 ..                                       .. {"type": "string", "description": "
 ..                                       .. Detailed explanation with evidence"
 ..                                       .. },
 ..                                       61                     "file": {"type"
 ..                                       .. : "string", "description": "File pa
 ..                                       .. th if cited, empty if architectural
 ..                                       .. "},
 ..                                       62                     "line": {"type"
 ..                                       .. : "integer", "description": "Line n
 ..                                       .. umber if cited, 0 if N/A"},
 ..                                       63                     "fix": {"type":
 ..                                       ..  "string", "description": "Proposed
 ..                                       ..  fix, empty if unclear"},
 ..                                       64                     "confidence": {
 ..                                       .. "type": "number", "description": "0
 ..                                       .. .0-1.0 confidence in this finding"}
 ..                                       .. ,
 ..                                       65                 },
 ..                                       66                 "required": ["categ
 ..                                       .. ory", "severity", "title", "descrip
 ..                                       .. tion", "file", "line", "fix", "conf
 ..                                       .. idence"],
 ..                                       67             },
 ..                                       68         },
 ..                                       69     },
 ..                                       70     "required": ["findings"],
 ..                                       71 }
 32                                       72 
 33 # --- Axis definitions: model + pro   73 # --- Axis definitions: model + pro
 .. mpt + llmx flags ---                  .. mpt + api kwargs ---
 34                                       74 
 35 AXES = {                              75 AXES = {
 36     "arch": {                         76     "arch": {
 37         "label": "Gemini (architect   77         "label": "Gemini (architect
 .. ure/patterns)",                       .. ure/patterns)",
 38         "model": "gemini-3.1-pro-pr   78         "model": "gemini-3.1-pro-pr
 .. eview",                               .. eview",
 ..                                       79         "provider": "google",
 39         "flags": ["--timeout", "300   80         "api_kwargs": {"timeout": 3
 .. "],                                   .. 00},
 40         "prompt": """\                81         "prompt": """\
 41 <system>                              82 <system>
 42 You are reviewing a codebase. Be co   83 You are reviewing a codebase. Be co
 .. ncrete. No platitudes. Reference sp   .. ncrete. No platitudes. Reference sp
 .. ecific code, configs, and findings.   .. ecific code, configs, and findings.
 ..  It is {date}.                        ..  It is {date}.

review/scripts/model-review.py --- 2/13 --- Python
 68     "formal": {                      109     "formal": {
 69         "label": "GPT-5.4 (quantita  110         "label": "GPT-5.4 (quantita
 .. tive/formal)",                       ... tive/formal)",
 70         "model": "gpt-5.4",          111         "model": "gpt-5.4",
 ..                                      112         "provider": "openai",
 71         "flags": ["--stream", "--re  113         "api_kwargs": {"timeout": 6
 .. asoning-effort", "high", "--timeout  ... 00, "reasoning_effort": "high", "ma
 .. ", "600", "--max-tokens", "32768"],  ... x_tokens": 32768},
 72         "prompt": """\               114         "prompt": """\
 73 <system>                             115 <system>
 74 You are performing QUANTITATIVE and  116 You are performing QUANTITATIVE and
 ..  FORMAL analysis. Other reviewers h  ...  FORMAL analysis. Other reviewers h
 .. andle qualitative pattern review. F  ... andle qualitative pattern review. F
 .. ocus on what they can't do well. Be  ... ocus on what they can't do well. Be
 ..  precise. Show your reasoning. No h  ...  precise. Show your reasoning. No h
 .. and-waving.                          ... and-waving.

review/scripts/model-review.py --- 3/13 --- Python
100     "domain": {                      142     "domain": {
101         "label": "Gemini Pro (domai  143         "label": "Gemini Pro (domai
... n correctness)",                     ... n correctness)",
102         "model": "gemini-3.1-pro-pr  144         "model": "gemini-3.1-pro-pr
... eview",                              ... eview",
...                                      145         "provider": "google",
103         "flags": ["--timeout", "300  146         "api_kwargs": {"timeout": 3
... "],                                  ... 00},
104         "prompt": """\               147         "prompt": """\
105 <system>                             148 <system>
106 You are verifying DOMAIN-SPECIFIC C  149 You are verifying DOMAIN-SPECIFIC C
... LAIMS in this plan. Other reviewers  ... LAIMS in this plan. Other reviewers
...  handle architecture and formal log  ...  handle architecture and formal log
... ic.                                  ... ic.

review/scripts/model-review.py --- 4/13 --- Python
122     "mechanical": {                  165     "mechanical": {
123         "label": "Gemini Flash (mec  166         "label": "Gemini Flash (mec
... hanical audit)",                     ... hanical audit)",
124         "model": "gemini-3-flash-pr  167         "model": "gemini-3-flash-pr
... eview",                              ... eview",
...                                      168         "provider": "google",
125         "flags": ["--timeout", "120  169         "api_kwargs": {"timeout": 1
... "],                                  ... 20},
126         "prompt": """\               170         "prompt": """\
127 <system>                             171 <system>
128 Mechanical audit only. No analysis,  172 Mechanical audit only. No analysis,
...  no recommendations. Fast and preci  ...  no recommendations. Fast and preci
... se.                                  ... se.

review/scripts/model-review.py --- 5/13 --- Python
137 Output as a flat numbered list. One  181 Output as a flat numbered list. One
...  issue per line.""",                 ...  issue per line.""",
138     },                               182     },
139     "alternatives": {                183     "alternatives": {
140         "label": "Kimi K2.5 (altern  184         "label": "Gemini Pro (alter
... ative approaches)",                  ... native approaches)",
141         "model": "kimi-k2.5",        185         "model": "gemini-3.1-pro-pr
...                                      ... eview",
...                                      186         "provider": "google",
142         "flags": ["--stream", "--ti  187         "api_kwargs": {"timeout": 3
... meout", "300"],                      ... 00},
143         "prompt": """\               188         "prompt": """\
144 <system>                             189 <system>
145 You are generating ALTERNATIVE APPR  190 You are generating ALTERNATIVE APPR
... OACHES to the proposed plan. Other   ... OACHES to the proposed plan. Other 
... reviewers check correctness.         ... reviewers check correctness.

review/scripts/model-review.py --- 6/13 --- Python
160     "simple": {                      205     "simple": {
161         "label": "Gemini Pro (combi  206         "label": "Gemini Pro (combi
... ned review)",                        ... ned review)",
162         "model": "gemini-3.1-pro-pr  207         "model": "gemini-3.1-pro-pr
... eview",                              ... eview",
...                                      208         "provider": "google",
163         "flags": ["--timeout", "300  209         "api_kwargs": {"timeout": 3
... "],                                  ... 00},
164         "prompt": """\               210         "prompt": """\
165 <system>                             211 <system>
166 Quick combined review. Be concrete.  212 Quick combined review. Be concrete.
...  It is {date}. Budget: ~1000 words.  ...  It is {date}. Budget: ~1000 words.

review/scripts/model-review.py --- 7/13 --- Python
200     return s[:max_len]               246     return s[:max_len]
...                                      247 
...                                      248 
...                                      249 def _add_additional_properties(sche
...                                      ... ma: dict) -> dict:
...                                      250     """Recursively add additionalPr
...                                      ... operties:false to all objects (Open
...                                      ... AI strict mode)."""
...                                      251     import copy
...                                      252     s = copy.deepcopy(schema)
...                                      253     def _walk(obj: dict) -> None:
...                                      254         if obj.get("type") == "obje
...                                      ... ct":
...                                      255             obj["additionalProperti
...                                      ... es"] = False
...                                      256         for v in obj.values():
...                                      257             if isinstance(v, dict):
...                                      258                 _walk(v)
...                                      259             elif isinstance(v, list
...                                      ... ):
...                                      260                 for item in v:
...                                      261                     if isinstance(i
...                                      ... tem, dict):
...                                      262                         _walk(item)
...                                      263     _walk(s)
...                                      264     return s
...                                      265 
...                                      266 
...                                      267 def _strip_additional_properties(sc
...                                      ... hema: dict) -> dict:
...                                      268     """Recursively remove additiona
...                                      ... lProperties from all objects (Googl
...                                      ... e API)."""
...                                      269     import copy
...                                      270     s = copy.deepcopy(schema)
...                                      271     def _walk(obj: dict) -> None:
...                                      272         obj.pop("additionalProperti
...                                      ... es", None)
...                                      273         for v in obj.values():
...                                      274             if isinstance(v, dict):
...                                      275                 _walk(v)
...                                      276             elif isinstance(v, list
...                                      ... ):
...                                      277                 for item in v:
...                                      278                     if isinstance(i
...                                      ... tem, dict):
...                                      279                         _walk(item)
...                                      280     _walk(s)
...                                      281     return s
201                                      282 
202                                      283 
203 def build_llmx_cmd(                  284 def _call_llmx(
204     model: str,                      285     provider: str,
205     flags: list[str],                286     model: str,
206     context_path: Path,              287     context_path: Path,
207     output_path: Path,               ... 
208     prompt: str,                     288     prompt: str,
209     *,                               289     output_path: Path,
210     provider: str | None = None,     290     schema: dict | None = None,
...                                      291     **kwargs,
211 ) -> list[str]:                      292 ) -> dict:
...                                      293     """Call llmx Python API, write 
...                                      ... output to file, return result dict.
...                                      ... """
...                                      294     context = context_path.read_tex
...                                      ... t()
...                                      295     full_prompt = context + "\n\n--
...                                      ... -\n\n" + prompt
...                                      296     # Reasoning models (GPT-5.x, Ge
...                                      ... mini 3.x) require temperature=1.0
212     cmd = [                          297     temperature = 1.0 if any(m in m
...                                      ... odel for m in ("gpt-5", "gemini-3")
...                                      ... ) else 0.7
213         "llmx", "chat",              298     api_kwargs: dict = {**kwargs}
214     ]                                ... 
215     if provider:                     299     if schema:
...                                      300         # OpenAI strict mode requir
...                                      ... es additionalProperties:false; Goog
...                                      ... le rejects it
...                                      301         if provider == "openai":
216         cmd.extend(["-p", provider]  302             api_kwargs["response_fo
... )                                    ... rmat"] = _add_additional_properties
...                                      ... (schema)
...                                      303         else:
...                                      304             api_kwargs["response_fo
...                                      ... rmat"] = _strip_additional_properti
...                                      ... es(schema)
...                                      305     try:
217     cmd.extend([                     306         response = llmx_chat(
...                                      307             prompt=full_prompt,
218         "-m", model,                 308             provider=provider,
...                                      309             model=model,
219         *flags,                      310             temperature=temperature
...                                      ... ,
...                                      311             **api_kwargs,
...                                      312         )
...                                      313         output_path.write_text(resp
...                                      ... onse.content)
...                                      314         return {
220         "-f", str(context_path),     315             "exit_code": 0,
...                                      316             "size": output_path.sta
...                                      ... t().st_size,
...                                      317             "latency": response.lat
...                                      ... ency,
221         "-o", str(output_path),      318             "error": None,
...                                      319         }
...                                      320     except Exception as e:
...                                      321         error_msg = str(e)[:500]
...                                      322         print(f"warning: llmx call 
...                                      ... failed ({model}): {error_msg}", fil
...                                      ... e=sys.stderr)
...                                      323         return {
222         prompt,                      324             "exit_code": 1,
223     ])                               325             "size": 0,
224     return cmd                       326             "latency": 0,
225                                      327             "error": error_msg,
226                                      328         }
227 def read_process_stderr(proc: subpr  ... 
... ocess.Popen) -> str:                 ... 
228     _, stderr = proc.communicate()   ... 
229     return stderr.decode(errors="re  ... 
... place").strip() if stderr else ""    ... 
230                                      329 
231                                      330 
232 def axis_output_failed(info: object  331 def axis_output_failed(info: object
... ) -> bool:                           ... ) -> bool:

review/scripts/model-review.py --- 8/13 --- Python
271     review_dir: Path,                370     review_dir: Path,
272     ctx_file: Path,                  371     ctx_file: Path,
273     prompt: str,                     372     prompt: str,
274     env: dict[str, str],             ... 
275 ) -> tuple[int, str, Path]:          373 ) -> dict:
...                                      374     """Retry a failed Gemini Pro ax
...                                      ... is with Gemini Flash."""
276     out_path = review_dir / f"{axis  375     out_path = review_dir / f"{axis
... }-output.md"                         ... }-output.md"
277     cmd = build_llmx_cmd(            ... 
278         GEMINI_FLASH_MODEL,          ... 
279         list(axis_def["flags"]),     ... 
280         ctx_file,                    ... 
281         out_path,                    ... 
282         prompt,                      ... 
283     )                                ... 
284     print(                           376     print(
285         f"warning: {axis} hit Gemin  377         f"warning: {axis} hit Gemin
... i Pro rate limits; retrying once wi  ... i Pro rate limits; retrying once wi
... th Gemini Flash",                    ... th Gemini Flash",
286         file=sys.stderr,             378         file=sys.stderr,
287     )                                379     )
288     proc = subprocess.Popen(cmd, en  380     api_kwargs = dict(axis_def.get(
... v=env, stdout=subprocess.PIPE, stde  ... "api_kwargs") or {})  # type: ignor
... rr=subprocess.PIPE)                  ... e[arg-type]
289     stderr = read_process_stderr(pr  ... 
... oc)                                  ... 
290     return proc.returncode, stderr,  381     return _call_llmx(
...  out_path                            ... 
...                                      382         provider="google",
...                                      383         model=GEMINI_FLASH_MODEL,
...                                      384         context_path=ctx_file,
...                                      385         prompt=prompt,
...                                      386         output_path=out_path,
...                                      387         **api_kwargs,
...                                      388     )
291                                      389 
292                                      390 
293 def find_constitution(project_dir:   391 def find_constitution(project_dir: 
... Path) -> tuple[str, str | None]:     ... Path) -> tuple[str, str | None]:

review/scripts/model-review.py --- 9/13 --- Python
439     has_constitution: bool,          537     has_constitution: bool,
440     question_overrides: dict[str, s  538     question_overrides: dict[str, s
... tr] | None = None,                   ... tr] | None = None,
441 ) -> dict:                           539 ) -> dict:
442     """Fire N llmx processes in par  540     """Fire N llmx API calls in par
... allel (one per axis), wait, return   ... allel (one per axis), wait, return 
... results."""                          ... results."""
443     env = {                          ... 
444         k: v                         ... 
445         for k, v in os.environ.item  ... 
... s()                                  ... 
446         if k not in ("CLAUDECODE",   ... 
... "CLAUDE_SESSION_ID")                 ... 
447     }                                ... 
448                                      ... 
449     today = date.today().isoformat(  541     today = date.today().isoformat(
... )                                    ... )
450                                      542 

review/scripts/model-review.py --- 10/13 --- Python
461         ),                           553         ),
462     }                                554     }
463                                      555 
464     procs = {}                       ... 
465     outputs = {}                     ... 
466     prompts = {}                     556     prompts: dict[str, str] = {}
467     t0 = time.time()                 557     t0 = time.time()
468                                      558 
469     for axis in axis_names:          559     for axis in axis_names:
470         axis_def = AXES[axis]        560         axis_def = AXES[axis]
471         out_path = review_dir / f"{  ... 
... axis}-output.md"                     ... 
472         outputs[axis] = out_path     ... 
473                                      ... 
474         axis_question = (question_o  561         axis_question = (question_o
... verrides or {}).get(axis, question)  ... verrides or {}).get(axis, question)
475         prompt = axis_def["prompt"]  562         prompts[axis] = axis_def["p
... .format(                             ... rompt"].format(
476             date=today,              563             date=today,
477             question=axis_question,  564             question=axis_question,
478             constitution_instructio  565             constitution_instructio
... n=const_instruction.get(axis, ""),   ... n=const_instruction.get(axis, ""),
479         )                            566         )
480         prompts[axis] = prompt       567 
481                                      ... 
482         # Auto-escalate Gemini Pro   ... 
... to API transport for large context.  ... 
483         # CLI transport (free) time  ... 
... s out on thinking models above ~15K  ... 
... B context                            ... 
484         # within the 300s window. -  ... 
... -stream forces API transport (paid   ... 
... but reliable).                       ... 
485         axis_flags = list(axis_def[  ... 
... "flags"])                            ... 
486         ctx_size = ctx_files[axis].  ... 
... stat().st_size if ctx_files[axis].e  ... 
... xists() else 0                       ... 
487         model_name = str(axis_def["  ... 
... model"])                             ... 
488         provider_name: str | None =  ... 
...  None                                ... 
489         if model_name == GEMINI_PRO  ... 
... _MODEL and ctx_size > 15_000 and "-  ... 
... -stream" not in axis_flags:          ... 
490             axis_flags.append("--st  ... 
... ream")                               ... 
491         if model_name.startswith("g  ... 
... pt-"):                               ... 
492             # model-review always w  ... 
... rites outputs with -o. In current l  ... 
... lmx, -o                              ... 
493             # auto-enables streamin  ... 
... g, which forces GPT onto API transp  ... 
... ort.                                 ... 
494             # Choose reliability-fi  ... 
... rst API transport explicitly instea  ... 
... d of                                 ... 
495             # pretending Codex CLI   ... 
... is preserved.                        ... 
496             provider_name = "openai  ... 
... "                                    ... 
497                                      ... 
498         cmd = build_llmx_cmd(        ... 
499             model_name,              ... 
500             axis_flags,              ... 
501             ctx_files[axis],         ... 
502             out_path,                ... 
503             prompt,                  ... 
504             provider=provider_name,  ... 
505         )                            ... 
506                                      ... 
507         procs[axis] = subprocess.Po  ... 
... pen(                                 ... 
508             cmd, env=env, stdout=su  ... 
... bprocess.PIPE, stderr=subprocess.PI  ... 
... PE                                   ... 
509         )                            ... 
510                                      ... 
511     # Wait for all                   ... 
512     results = {"review_dir": str(re  ... 
... view_dir), "axes": axis_names, "que  ... 
... ries": len(axis_names)}              ... 
513     gemini_rate_limited = False      ... 
514     for axis in axis_names:          568     def _run_axis(axis: str) -> tup
...                                      ... le[str, dict]:
515         proc = procs[axis]           ... 
516         stderr = read_process_stder  ... 
... r(proc)                              ... 
517         rc = proc.returncode         ... 
518         out_path = outputs[axis]     ... 
519         requested_model = str(AXES[  569         axis_def = AXES[axis]
... axis]["model"])                      ... 
520         output_size = out_path.stat  ... 
... ().st_size if out_path.exists() els  ... 
... e 0                                  ... 
521         transient_gemini_failure =   570         out_path = review_dir / f"{
... is_gemini_rate_limit_failure(        ... axis}-output.md"
522             requested_model,         ... 
523             rc,                      ... 
524             stderr,                  ... 
525             output_size,             ... 
526         )                            ... 
527         should_fallback = requested  571         result = _call_llmx(
... _model == GEMINI_PRO_MODEL and (     ... 
528             transient_gemini_failur  ... 
... e                                    ... 
529             or (gemini_rate_limited  572             provider=str(axis_def["
...  and (rc != 0 or output_size == 0))  ... provider"]),
...                                      573             model=str(axis_def["mod
...                                      ... el"]),
...                                      574             context_path=ctx_files[
...                                      ... axis],
...                                      575             prompt=prompts[axis],
...                                      576             output_path=out_path,
...                                      577             **dict(axis_def.get("ap
...                                      ... i_kwargs") or {}),  # type: ignore[
...                                      ... arg-type]
530         )                            578         )
531         if transient_gemini_failure  ... 
... :                                    ... 
532             gemini_rate_limited = T  ... 
... rue                                  ... 
533                                      ... 
534         entry = {                    579         entry = {
535             "label": AXES[axis]["la  580             "label": axis_def["labe
... bel"],                               ... l"],
536             "requested_model": requ  581             "requested_model": str(
... ested_model,                         ... axis_def["model"]),
537             "model": requested_mode  582             "model": str(axis_def["
... l,                                   ... model"]),
538             "exit_code": rc,         583             "exit_code": result["ex
...                                      ... it_code"],
539             "output": str(out_path)  584             "output": str(out_path)
... ,                                    ... ,
540             "size": output_size,     585             "size": result["size"],
541         }                            586         }
542         if should_fallback:          587         if result.get("latency"):
543             entry["fallback_from"]   588             entry["latency"] = resu
... = requested_model                    ... lt["latency"]
...                                      589         if result.get("error"):
...                                      590             entry["stderr"] = resul
...                                      ... t["error"]
...                                      591 
...                                      592         # Gemini Pro fallback to Fl
...                                      ... ash on rate limit
...                                      593         if (
...                                      594             str(axis_def["model"]) 
...                                      ... == GEMINI_PRO_MODEL
...                                      595             and result["exit_code"]
...                                      ...  != 0
...                                      596             and result.get("error")
544             entry["fallback_reason"  597             and any(m in result["er
... ] = (                                ... ror"].lower() for m in GEMINI_RATE_
...                                      ... LIMIT_MARKERS)
545                 "gemini_rate_limit"  598         ):
...  if transient_gemini_failure else "  ... 
... gemini_session_rate_limit"           ... 
546             )                        ... 
547             entry["initial_exit_cod  599             entry["fallback_from"] 
... e"] = rc                             ... = str(axis_def["model"])
548             entry["initial_size"] =  600             entry["fallback_reason"
...  output_size                         ... ] = "gemini_rate_limit"
549             if stderr:               ... 
550                 entry["initial_stde  601             entry["initial_exit_cod
... rr"] = stderr[-500:]                 ... e"] = result["exit_code"]
551                                      ... 
552             rc, stderr, out_path =   602             flash_result = rerun_ax
... rerun_axis_with_flash(               ... is_with_flash(
553                 axis,                603                 axis, axis_def, rev
...                                      ... iew_dir, ctx_files[axis], prompts[a
...                                      ... xis],
554                 AXES[axis],          ... 
555                 review_dir,          ... 
556                 ctx_files[axis],     ... 
557                 prompts[axis],       ... 
558                 env,                 ... 
559             )                        604             )
560             output_size = out_path.  ... 
... stat().st_size if out_path.exists()  ... 
...  else 0                              ... 
561             entry["model"] = GEMINI  605             entry["model"] = GEMINI
... _FLASH_MODEL                         ... _FLASH_MODEL
562             entry["exit_code"] = rc  606             entry["exit_code"] = fl
...                                      ... ash_result["exit_code"]
563             entry["size"] = output_  607             entry["size"] = flash_r
... size                                 ... esult["size"]
564         if stderr:                   608 
565             entry["stderr"] = stder  ... 
... r[-500:] if stderr else ""           ... 
566         if output_size == 0:         609         if entry["size"] == 0:
567             entry["failure_reason"]  610             entry["failure_reason"]
...  = "empty_output"                    ...  = "empty_output"
568                                      611 
569         results[axis] = entry        612         return axis, entry
...                                      613 
...                                      614     # Parallel dispatch via threads
...                                      ...  (720s timeout = max model timeout 
...                                      ... + 2min buffer)
...                                      615     results: dict = {"review_dir": 
...                                      ... str(review_dir), "axes": axis_names
...                                      ... , "queries": len(axis_names)}
...                                      616     with ThreadPoolExecutor(max_wor
...                                      ... kers=len(axis_names)) as pool:
...                                      617         futures = {pool.submit(_run
...                                      ... _axis, axis): axis for axis in axis
...                                      ... _names}
...                                      618         for future in as_completed(
...                                      ... futures, timeout=720):
...                                      619             try:
...                                      620                 axis, entry = futur
...                                      ... e.result(timeout=720)
...                                      621             except TimeoutError:
...                                      622                 axis = futures[futu
...                                      ... re]
...                                      623                 entry = {
...                                      624                     "label": AXES[a
...                                      ... xis]["label"],
...                                      625                     "requested_mode
...                                      ... l": str(AXES[axis]["model"]),
...                                      626                     "model": str(AX
...                                      ... ES[axis]["model"]),
...                                      627                     "exit_code": 1,
...                                      628                     "output": str(r
...                                      ... eview_dir / f"{axis}-output.md"),
...                                      629                     "size": 0,
...                                      630                     "failure_reason
...                                      ... ": "thread_timeout",
...                                      631                 }
...                                      632             results[axis] = entry
570                                      633 
571     results["elapsed_seconds"] = ro  634     results["elapsed_seconds"] = ro
... und(time.time() - t0, 1)             ... und(time.time() - t0, 1)
572     return results                   635     return results
573                                      636 
574                                      637 
575 EXTRACTION_PROMPT = (                638 EXTRACTION_PROMPT = (
576     "Extract every discrete recomme  639     "Extract every discrete recomme
... ndation, finding, or claimed bug as  ... ndation, finding, or claimed bug fr
...  a numbered list. "                  ... om the review. "
577     "One item per line. Include the  640     "Return JSON matching the schem
...  specific file/code/concept referen  ... a. For each finding: category, seve
... ced. "                               ... rity, a one-line title, "
...                                      641     "description with the reviewer'
...                                      ... s evidence, file path if cited, pro
...                                      ... posed fix, "
...                                      642     "and confidence 0.0-1.0 based o
...                                      ... n specificity of evidence. "
578     "SKIP confirmatory observations  643     "SKIP confirmatory observations
...  that merely describe existing corr  ...  that merely describe correct behav
... ect behavior "                       ... ior. "
579     "(e.g. 'X correctly groups Y',   ... 
... 'Z is well-designed'). "             ... 
580     "Only extract items that propos  644     "Only extract items that propos
... e a change, flag a problem, or clai  ... e a change, flag a problem, or clai
... m something is wrong/missing."       ... m something is wrong/missing."
581 )                                    645 )
582                                      646 

review/scripts/model-review.py --- 11/13 --- Python
625                                      689 
626     Returns path to disposition.md,  690     Returns path to disposition.md,
...  or None if no outputs to extract.   ...  or None if no outputs to extract.
627     """                              691     """
628     env = {                          ... 
629         k: v                         ... 
630         for k, v in os.environ.item  ... 
... s()                                  ... 
631         if k not in ("CLAUDECODE",   ... 
... "CLAUDE_SESSION_ID")                 ... 
632     }                                ... 
633                                      ... 
634     extraction_procs: dict[str, tup  692     extraction_tasks: list[tuple[st
... le[subprocess.Popen, Path]] = {}     ... r, Path, str, str]] = []  # (axis, 
...                                      ... output_path, model, provider)
635     skip_keys = {"review_dir", "axe  693     skip_keys = {"review_dir", "axe
... s", "queries", "elapsed_seconds"}    ... s", "queries", "elapsed_seconds"}
636                                      694 
637     for axis, info in dispatch_resu  695     for axis, info in dispatch_resu
... lt.items():                          ... lt.items():

review/scripts/model-review.py --- 12/13 --- Python
644         if not output_path.exists()  702         if not output_path.exists()
... :                                    ... :
645             continue                 703             continue
646                                      704 
647         extraction_path = review_di  ... 
... r / f"{axis}-extraction.md"          ... 
648         model = info.get("model", "  705         model = info.get("model", "
... ")                                   ... ")
649                                      706 
650         # Cross-family: Gemini outp  707         # Cross-family: Gemini outp
... uts → GPT extraction, GPT outputs →  ... uts → GPT extraction, GPT outputs →
...  Gemini Flash extraction             ...  Gemini Flash extraction
651         if "gemini" in model.lower(  708         if "gemini" in model.lower(
... ):                                   ... ):
652             extract_model = "gpt-5.  ... 
... 3-chat-latest"                       ... 
653             extract_flags = ["--str  ... 
... eam", "--timeout", "120"]            ... 
654         else:                        ... 
655             extract_model = "gemini  ... 
... -3-flash-preview"                    ... 
656             extract_flags = ["--tim  ... 
... eout", "120"]                        ... 
657                                      ... 
658         cmd = build_llmx_cmd(        709             extraction_tasks.append
...                                      ... ((axis, output_path, "gpt-5.3-chat-
...                                      ... latest", "openai"))
659             extract_model, extract_  710         else:
... flags, output_path, extraction_path  ... 
... , EXTRACTION_PROMPT,                 ... 
660         )                            ... 
661         proc = subprocess.Popen(cmd  711             extraction_tasks.append
... , env=env, stdout=subprocess.PIPE,   ... ((axis, output_path, "gemini-3-flas
... stderr=subprocess.PIPE)              ... h-preview", "google"))
662         extraction_procs[axis] = (p  ... 
... roc, extraction_path)                ... 
663                                      712 
664     if not extraction_procs:         713     if not extraction_tasks:
665         return None                  714         return None
666                                      715 
667     print(                           716     print(
668         f"Extracting claims from {l  717         f"Extracting claims from {l
... en(extraction_procs)} outputs...",   ... en(extraction_tasks)} outputs...",
669         file=sys.stderr,             718         file=sys.stderr,
670     )                                719     )
671                                      720 
672     # Wait for all extractions and   ... 
... merge                                ... 
673     extractions: list[str] = []      721     def _extract_one(task: tuple[st
...                                      ... r, Path, str, str]) -> tuple[str, l
...                                      ... ist[dict] | None]:
674     for axis, (proc, path) in extra  722         axis, output_path, model, p
... ction_procs.items():                 ... rovider = task
675         stderr = read_process_stder  723         extraction_path = review_di
... r(proc)                              ... r / f"{axis}-extraction.json"
676         label = dispatch_result[axi  724         result = _call_llmx(
... s].get("label", axis)                ... 
...                                      725             provider=provider,
...                                      726             model=model,
...                                      727             context_path=output_pat
...                                      ... h,
...                                      728             prompt=EXTRACTION_PROMP
...                                      ... T,
...                                      729             output_path=extraction_
...                                      ... path,
...                                      730             schema=FINDING_SCHEMA,
...                                      731             timeout=120,
...                                      732         )
677         if proc.returncode != 0:     733         if result["exit_code"] != 0
...                                      ... :
678             print(f"warning: extrac  734             print(f"warning: extrac
... tion for {axis} failed (exit {proc.  ... tion for {axis} failed: {result.get
... returncode})", file=sys.stderr)      ... ('error', 'unknown')}", file=sys.st
...                                      ... derr)
679             if stderr:               ... 
680                 print(f"  stderr: {  735             return axis, None
... stderr[:200]}", file=sys.stderr)     ... 
681             continue                 ... 
682         if path.exists() and path.s  736         if result["size"] > 0:
... tat().st_size > 0:                   ... 
683             extractions.append(f"##  737             try:
...  {label}\n\n{path.read_text().strip  ... 
... ()}")                                ... 
684         elif path.exists() and path  738                 data = json.loads(e
... .stat().st_size == 0:                ... xtraction_path.read_text())
...                                      739                 return axis, data.g
...                                      ... et("findings", [])
...                                      740             except (json.JSONDecode
...                                      ... Error, KeyError) as e:
685             print(f"warning: extrac  741                 print(f"warning: ex
... tion for {axis} produced 0-byte fil  ... traction for {axis} returned invali
... e (model errored before output)", f  ... d JSON: {e}", file=sys.stderr)
... ile=sys.stderr)                      ... 
...                                      742                 # Fall back to raw 
...                                      ... text
...                                      743                 return axis, None
...                                      744         print(f"warning: extraction
...                                      ...  for {axis} produced empty output",
...                                      ...  file=sys.stderr)
...                                      745         return axis, None
...                                      746 
...                                      747     # Parallel extraction
...                                      748     axis_findings: dict[str, list[d
...                                      ... ict]] = {}
...                                      749     with ThreadPoolExecutor(max_wor
...                                      ... kers=len(extraction_tasks)) as pool
...                                      ... :
...                                      750         for axis, findings in pool.
...                                      ... map(_extract_one, extraction_tasks)
...                                      ... :
...                                      751             if findings:
...                                      752                 axis_findings[axis]
...                                      ...  = findings
...                                      753 
...                                      754     if not axis_findings:
...                                      755         return None
...                                      756 
...                                      757     # Merge findings across axes — 
...                                      ... keyword overlap for cross-model ded
...                                      ... up
...                                      758     def _fingerprint(f: dict) -> se
...                                      ... t[str]:
...                                      759         """Extract significant keyw
...                                      ... ords for fuzzy matching."""
...                                      760         text = f"{f.get('title', ''
...                                      ... )} {f.get('file', '')} {f.get('desc
...                                      ... ription', '')[:200]}"
...                                      761         words = set(re.findall(r"[a
...                                      ... -z_]{4,}", text.lower()))
...                                      762         # Remove common stop-words 
...                                      ... that inflate false matches
...                                      763         words -= {"this", "that", "
...                                      ... with", "from", "should", "could", "
...                                      ... would", "does", "have", "will", "al
...                                      ... so", "been"}
...                                      764         return words
...                                      765 
...                                      766     merged_findings: list[dict] = [
...                                      ... ]
...                                      767     seen: list[tuple[set[str], dict
...                                      ... ]] = []  # (keywords, finding)
...                                      768     for axis, findings in axis_find
...                                      ... ings.items():
...                                      769         source_label = dispatch_res
...                                      ... ult[axis].get("label", axis)
...                                      770         source_model = dispatch_res
...                                      ... ult[axis].get("model", "unknown")
...                                      771         for f in findings:
...                                      772             f["source_axis"] = axis
...                                      773             f["source_model"] = sou
...                                      ... rce_model
...                                      774             f["source_label"] = sou
...                                      ... rce_label
...                                      775             fp = _fingerprint(f)
...                                      776             # Check for overlap wit
...                                      ... h existing findings (Jaccard > 0.3)
...                                      777             matched = False
...                                      778             for existing_fp, existi
...                                      ... ng in seen:
...                                      779                 if len(fp & existin
...                                      ... g_fp) > 0 and len(fp & existing_fp)
...                                      ...  / len(fp | existing_fp) > 0.3:
...                                      780                     existing.setdef
...                                      ... ault("also_found_by", []).append(so
...                                      ... urce_label)
...                                      781                     existing["cross
...                                      ... _model"] = True
...                                      782                     existing["confi
...                                      ... dence"] = min(1.0, existing.get("co
...                                      ... nfidence", 0.5) + 0.2)
...                                      783                     matched = True
...                                      784                     break
...                                      785             if not matched:
...                                      786                 seen.append((fp, f)
...                                      ... )
...                                      787                 merged_findings.app
...                                      ... end(f)
...                                      788 
...                                      789     # Sort: cross-model agreements 
...                                      ... first, then by severity, then confi
...                                      ... dence
...                                      790     severity_order = {"critical": 0
...                                      ... , "high": 1, "medium": 2, "low": 3}
...                                      791     merged_findings.sort(key=lambda
...                                      ...  f: (
...                                      792         0 if f.get("cross_model") e
...                                      ... lse 1,
...                                      793         severity_order.get(f.get("s
...                                      ... everity", "low"), 3),
...                                      794         -(f.get("confidence", 0)),
...                                      795     ))
...                                      796 
...                                      797     # Renumber
...                                      798     for i, f in enumerate(merged_fi
...                                      ... ndings, 1):
...                                      799         f["id"] = i
...                                      800 
...                                      801     # Write structured JSON
...                                      802     structured_path = review_dir / 
...                                      ... "findings.json"
...                                      803     structured_path.write_text(json
...                                      ... .dumps({"findings": merged_findings
...                                      ... }, indent=2) + "\n")
...                                      804 
...                                      805     # Write human-readable disposit
...                                      ... ion
...                                      806     extractions: list[str] = []
...                                      807     for f in merged_findings:
...                                      808         source = f.get("source_labe
...                                      ... l", "unknown")
...                                      809         also = f.get("also_found_by
...                                      ... ", [])
...                                      810         agreement = f" **[CROSS-MOD
...                                      ... EL: also {', '.join(also)}]**" if a
...                                      ... lso else ""
...                                      811         conf = f.get("confidence", 
...                                      ... 0)
...                                      812         extractions.append(
...                                      813             f"{f['id']}. **[{f.get(
...                                      ... 'severity', '?').upper()}]** {f.get
...                                      ... ('title', '?')}{agreement}\n"
...                                      814             f"   Category: {f.get('
...                                      ... category', '?')} | Confidence: {con
...                                      ... f:.1f} | Source: {source}\n"
...                                      815             f"   {f.get('descriptio
...                                      ... n', '')}\n"
...                                      816             f"   File: {f.get('file
...                                      ... ', 'N/A')}\n"
...                                      817             f"   Fix: {f.get('fix',
...                                      ...  'N/A')}"
...                                      818         )
686                                      819 
687     if not extractions:              820     if not extractions:
688         return None                  821         return None

review/scripts/model-review.py --- 13/13 --- Python
701         "### Context I had that the  834         "### Context I had that the
...  models didn't:\n"                   ...  models didn't:\n"
702         "<!-- If context file was c  835         "<!-- If context file was c
... omprehensive, say so. -->\n\n"       ... omprehensive, say so. -->\n\n"
703     )                                836     )
...                                      837     cross_model_count = sum(1 for f
...                                      ...  in merged_findings if f.get("cross
...                                      ... _model"))
...                                      838     header = (
...                                      839         f"# Review Findings — {date
...                                      ... .today().isoformat()}\n\n"
...                                      840         f"**{len(merged_findings)} 
...                                      ... findings** from {len(axis_findings)
...                                      ... } axes"
...                                      841         f" ({cross_model_count} cro
...                                      ... ss-model agreements)\n"
...                                      842         f"Structured data: `finding
...                                      ... s.json`\n\n"
...                                      843     )
704     disposition.write_text(          844     disposition.write_text(header +
...                                      ...  merged + response_template)
705         f"# Extracted Claims — {dat  ... 
... e.today().isoformat()}\n\n" + merge  ... 
... d + response_template                ... 
706     )                                ... 
707     return str(disposition)          845     return str(disposition)
708                                      846 



## Current model-review.py (full)

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

# llmx is editable-installed as a uv tool; bootstrap from its venv if not importable
try:
    from llmx.api import chat as llmx_chat
except ImportError:
    import glob
    _tool_site = glob.glob(str(Path.home() / ".local/share/uv/tools/llmx/lib/python*/site-packages"))
    if _tool_site:
        sys.path.insert(0, _tool_site[0])
    sys.path.insert(0, str(Path.home() / "Projects" / "llmx"))
    from llmx.api import chat as llmx_chat

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
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
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
        "model": "gpt-5.4",
        "provider": "openai",
        "api_kwargs": {"timeout": 600, "reasoning_effort": "high", "max_tokens": 32768},
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
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
        "prompt": """\
<system>
You are verifying DOMAIN-SPECIFIC CLAIMS in this plan. Other reviewers handle architecture and formal logic.
Focus exclusively on: are the domain facts correct? Are citations real? Are API endpoints, database schemas,
biological claims, financial numbers accurate? Check every specific claim against your knowledge.
Budget: ~1500 words. Flat list of claims with verdict (CORRECT / WRONG / UNVERIFIABLE).
</system>

{question}

For each domain-specific claim in the reviewed material:
1. State the claim
2. Verdict: CORRECT / WRONG / UNVERIFIABLE
3. If WRONG: what's actually true
4. If UNVERIFIABLE: what would you need to check

Flag any URLs, API endpoints, or version numbers that should be probed before implementation.""",
    },
    "mechanical": {
        "label": "Gemini Flash (mechanical audit)",
        "model": "gemini-3-flash-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 120},
        "prompt": """\
<system>
Mechanical audit only. No analysis, no recommendations. Fast and precise.
</system>

Find in the reviewed material:
- Stale references (wrong versions, deprecated APIs, broken links)
- Inconsistent naming (model names, paths, conventions that don't match)
- Missing cross-references between related documents
- Duplicated content
- Paths or file references that look wrong
Output as a flat numbered list. One issue per line.""",
    },
    "alternatives": {
        "label": "Gemini Pro (alternative approaches)",
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
        "prompt": """\
<system>
You are generating ALTERNATIVE APPROACHES to the proposed plan. Other reviewers check correctness.
Your job: what ELSE could be done? Different mechanisms, not variations.
Budget: ~1500 words.
</system>

{question}

Generate 3-5 genuinely different approaches to the same problem. For each:
1. Core mechanism (how it works differently)
2. What it's better at than the proposed approach
3. What it's worse at
4. Maintenance burden and complexity cost (not implementation effort — agents build everything)

Do NOT critique the existing plan — generate alternatives. Different mechanisms, not tweaks.""",
    },
    "simple": {
        "label": "Gemini Pro (combined review)",
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
        "prompt": """\
<system>
Quick combined review. Be concrete. It is {date}. Budget: ~1000 words.
</system>

{question}

Check for: (1) anything that breaks existing functionality, (2) wrong assumptions, (3) missing edge cases.
If everything looks correct, say so concisely.""",
    },
}

# Presets map a single name to a list of axes
PRESETS = {
    "simple": ["simple"],
    "standard": ["arch", "formal"],
    "deep": ["arch", "formal", "domain", "mechanical"],
    "full": ["arch", "formal", "domain", "mechanical", "alternatives"],
}

GEMINI_PRO_MODEL = "gemini-3.1-pro-preview"
GEMINI_FLASH_MODEL = "gemini-3-flash-preview"
GEMINI_RATE_LIMIT_MARKERS = (
    "503",
    "rate limit",
    "rate-limit",
    "resource_exhausted",
    "overloaded",
    "429",
)


def slugify(text: str, max_len: int = 40) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len]


def _add_additional_properties(schema: dict) -> dict:
    """Recursively add additionalProperties:false to all objects (OpenAI strict mode)."""
    import copy
    s = copy.deepcopy(schema)
    def _walk(obj: dict) -> None:
        if obj.get("type") == "object":
            obj["additionalProperties"] = False
        for v in obj.values():
            if isinstance(v, dict):
                _walk(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _walk(item)
    _walk(s)
    return s


def _strip_additional_properties(schema: dict) -> dict:
    """Recursively remove additionalProperties from all objects (Google API)."""
    import copy
    s = copy.deepcopy(schema)
    def _walk(obj: dict) -> None:
        obj.pop("additionalProperties", None)
        for v in obj.values():
            if isinstance(v, dict):
                _walk(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _walk(item)
    _walk(s)
    return s


def _call_llmx(
    provider: str,
    model: str,
    context_path: Path,
    prompt: str,
    output_path: Path,
    schema: dict | None = None,
    **kwargs,
) -> dict:
    """Call llmx Python API, write output to file, return result dict."""
    context = context_path.read_text()
    full_prompt = context + "\n\n---\n\n" + prompt
    # Reasoning models (GPT-5.x, Gemini 3.x) require temperature=1.0
    temperature = 1.0 if any(m in model for m in ("gpt-5", "gemini-3")) else 0.7
    api_kwargs: dict = {**kwargs}
    if schema:
        # OpenAI strict mode requires additionalProperties:false; Google rejects it
        if provider == "openai":
            api_kwargs["response_format"] = _add_additional_properties(schema)
        else:
            api_kwargs["response_format"] = _strip_additional_properties(schema)
    try:
        response = llmx_chat(
            prompt=full_prompt,
            provider=provider,
            model=model,
            temperature=temperature,
            **api_kwargs,
        )
        output_path.write_text(response.content)
        return {
            "exit_code": 0,
            "size": output_path.stat().st_size,
            "latency": response.latency,
            "error": None,
        }
    except Exception as e:
        error_msg = str(e)[:500]
        print(f"warning: llmx call failed ({model}): {error_msg}", file=sys.stderr)
        return {
            "exit_code": 1,
            "size": 0,
            "latency": 0,
            "error": error_msg,
        }


def axis_output_failed(info: object) -> bool:
    """Return True when an axis failed to produce a usable review artifact."""
    if not isinstance(info, dict):
        return False
    return int(info.get("exit_code", 0)) != 0 or int(info.get("size", 0)) == 0


def collect_dispatch_failures(
    dispatch_result: dict,
    ctx_files: dict[str, Path],
) -> list[dict[str, object]]:
    """Summarize failed axes for machine-readable failure artifacts."""
    failures: list[dict[str, object]] = []
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}
    for axis, info in dispatch_result.items():
        if axis in skip_keys or not axis_output_failed(info):
            continue
        entry = dict(info)
        entry["axis"] = axis
        entry["context"] = str(ctx_files.get(axis, ""))
        entry["failure_reason"] = (
            "nonzero_exit" if int(entry.get("exit_code", 0)) != 0 else "empty_output"
        )
        failures.append(entry)
    return failures


def is_gemini_rate_limit_failure(model: str, exit_code: int, stderr: str, output_size: int) -> bool:
    if model != GEMINI_PRO_MODEL:
        return False
    if exit_code == 0 and output_size > 0:
        return False
    stderr_lower = stderr.lower()
    return exit_code == 3 or any(marker in stderr_lower for marker in GEMINI_RATE_LIMIT_MARKERS)


def rerun_axis_with_flash(
    axis: str,
    axis_def: dict[str, object],
    review_dir: Path,
    ctx_file: Path,
    prompt: str,
) -> dict:
    """Retry a failed Gemini Pro axis with Gemini Flash."""
    out_path = review_dir / f"{axis}-output.md"
    print(
        f"warning: {axis} hit Gemini Pro rate limits; retrying once with Gemini Flash",
        file=sys.stderr,
    )
    api_kwargs = dict(axis_def.get("api_kwargs") or {})  # type: ignore[arg-type]
    return _call_llmx(
        provider="google",
        model=GEMINI_FLASH_MODEL,
        context_path=ctx_file,
        prompt=prompt,
        output_path=out_path,
        **api_kwargs,
    )


def find_constitution(project_dir: Path) -> tuple[str, str | None]:
    """Find constitution text and GOALS.md path in project dir."""
    constitution = ""
    goals_path = None

    # Check .claude/rules/constitution.md first (genomics, projects with standalone file)
    rules_const = project_dir / ".claude" / "rules" / "constitution.md"
    if rules_const.exists():
        constitution = rules_const.read_text().strip()

    # Fall back to CLAUDE.md <constitution> tag or ## Constitution heading
    if not constitution:
        claude_md = project_dir / "CLAUDE.md"
        if claude_md.exists():
            text = claude_md.read_text()
            m = re.search(r"<constitution>(.*?)</constitution>", text, re.DOTALL)
            if m:
                constitution = m.group(1).strip()
            elif "## Constitution" in text:
                idx = text.index("## Constitution")
                rest = text[idx:]
                end = re.search(r"\n## (?!Constitution)", rest)
                constitution = rest[: end.start()].strip() if end else rest.strip()

    for gp in [project_dir / "GOALS.md", project_dir / "docs" / "GOALS.md"]:
        if gp.exists():
            goals_path = str(gp)
            break

    return constitution, goals_path


def parse_file_spec(spec: str) -> str:
    """Parse a file:start-end spec and return the content.

    Formats:
      path/file.py           — entire file
      path/file.py:100-150   — lines 100-150 (1-based, inclusive)
      path/file.py:100       — single line
    """
    if ":" in spec and not spec.startswith("/") or spec.count(":") == 1:
        parts = spec.rsplit(":", 1)
        file_path = parts[0]
        range_spec = parts[1] if len(parts) > 1 else ""
    else:
        file_path = spec
        range_spec = ""

    path = Path(file_path).expanduser()
    if not path.exists():
        return f"# [FILE NOT FOUND: {file_path}]\n"

    text = path.read_text()

    if range_spec and "-" in range_spec:
        try:
            start, end = range_spec.split("-", 1)
            start_line = int(start) - 1  # 0-based
            end_line = int(end)
            lines = text.splitlines()
            text = "\n".join(lines[start_line:end_line])
        except (ValueError, IndexError):
            pass
    elif range_spec:
        try:
            line_no = int(range_spec) - 1
            lines = text.splitlines()
            text = lines[line_no] if 0 <= line_no < len(lines) else text
        except (ValueError, IndexError):
            pass

    return f"# {file_path}" + (f" (lines {range_spec})" if range_spec else "") + f"\n\n{text}\n\n"


def assemble_context_files(specs: list[str]) -> str:
    """Assemble content from multiple file:range specs into one context string."""
    parts = []
    for spec in specs:
        parts.append(parse_file_spec(spec.strip()))
    return "\n".join(parts)


def build_context(
    review_dir: Path,
    project_dir: Path,
    context_file: Path | None,
    axis_names: list[str],
    *,
    context_file_specs: list[str] | None = None,
) -> dict[str, Path]:
    """Assemble per-axis context files with constitutional preamble.

    Context sources (in order of precedence):
      1. --context FILE — single pre-assembled context file
      2. --context-files spec1 spec2 ... — auto-assembled from file:range specs
    """
    constitution, goals_path = find_constitution(project_dir)

    preamble = ""
    if constitution:
        # Always include full constitution verbatim — summaries lose nuance
        # that causes reviewers to over-apply or misapply principles
        preamble += "# PROJECT CONSTITUTION (verbatim — review against these, not your priors)\n\n"
        preamble += constitution + "\n\n"
    if goals_path:
        preamble += "# PROJECT GOALS\n\n"
        preamble += Path(goals_path).read_text() + "\n\n"

    # Agent economics framing — always included so reviewers don't
    # recommend trading quality for dev time (which is ~free with agents)
    preamble += "# DEVELOPMENT CONTEXT\n"
    preamble += "All code, plans, and features in this project are developed by AI agents, not human developers. "
    preamble += "Dev creation time is effectively zero. Therefore:\n"
    preamble += "- NEVER recommend trading stability, composability, or robustness for dev time savings\n"
    preamble += "- NEVER recommend simpler/hacky approaches because they're 'faster to implement'\n"
    preamble += "- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort\n"
    preamble += "- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters\n\n"

    # Assemble content from the right source
    if context_file:
        content = context_file.read_text()
    elif context_file_specs:
        content = assemble_context_files(context_file_specs)
    else:
        content = ""

    ctx_files = {}
    for axis in axis_names:
        ctx_path = review_dir / f"{axis}-context.md"
        ctx_path.write_text(preamble + content)
        ctx_files[axis] = ctx_path

    # Warn on size
    for axis, path in ctx_files.items():
        size = path.stat().st_size
        if size > 15_000:
            print(f"warning: {axis} context {size} bytes > 15KB — consider summarizing", file=sys.stderr)

    return ctx_files


def dispatch(
    review_dir: Path,
    ctx_files: dict[str, Path],
    axis_names: list[str],
    question: str,
    has_constitution: bool,
    question_overrides: dict[str, str] | None = None,
) -> dict:
    """Fire N llmx API calls in parallel (one per axis), wait, return results."""
    today = date.today().isoformat()

    const_instruction = {
        "arch": (
            "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?"
            if has_constitution
            else "No constitution provided — assess internal consistency only."
        ),
        "formal": (
            "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes."
            if has_constitution
            else "No constitution provided — assess internal logical consistency."
        ),
    }

    prompts: dict[str, str] = {}
    t0 = time.time()

    for axis in axis_names:
        axis_def = AXES[axis]
        axis_question = (question_overrides or {}).get(axis, question)
        prompts[axis] = axis_def["prompt"].format(
            date=today,
            question=axis_question,
            constitution_instruction=const_instruction.get(axis, ""),
        )

    def _run_axis(axis: str) -> tuple[str, dict]:
        axis_def = AXES[axis]
        out_path = review_dir / f"{axis}-output.md"
        result = _call_llmx(
            provider=str(axis_def["provider"]),
            model=str(axis_def["model"]),
            context_path=ctx_files[axis],
            prompt=prompts[axis],
            output_path=out_path,
            **dict(axis_def.get("api_kwargs") or {}),  # type: ignore[arg-type]
        )
        entry = {
            "label": axis_def["label"],
            "requested_model": str(axis_def["model"]),
            "model": str(axis_def["model"]),
            "exit_code": result["exit_code"],
            "output": str(out_path),
            "size": result["size"],
        }
        if result.get("latency"):
            entry["latency"] = result["latency"]
        if result.get("error"):
            entry["stderr"] = result["error"]

        # Gemini Pro fallback to Flash on rate limit
        if (
            str(axis_def["model"]) == GEMINI_PRO_MODEL
            and result["exit_code"] != 0
            and result.get("error")
            and any(m in result["error"].lower() for m in GEMINI_RATE_LIMIT_MARKERS)
        ):
            entry["fallback_from"] = str(axis_def["model"])
            entry["fallback_reason"] = "gemini_rate_limit"
            entry["initial_exit_code"] = result["exit_code"]
            flash_result = rerun_axis_with_flash(
                axis, axis_def, review_dir, ctx_files[axis], prompts[axis],
            )
            entry["model"] = GEMINI_FLASH_MODEL
            entry["exit_code"] = flash_result["exit_code"]
            entry["size"] = flash_result["size"]

        if entry["size"] == 0:
            entry["failure_reason"] = "empty_output"

        return axis, entry

    # Parallel dispatch via threads (720s timeout = max model timeout + 2min buffer)
    results: dict = {"review_dir": str(review_dir), "axes": axis_names, "queries": len(axis_names)}
    with ThreadPoolExecutor(max_workers=len(axis_names)) as pool:
        futures = {pool.submit(_run_axis, axis): axis for axis in axis_names}
        for future in as_completed(futures, timeout=720):
            try:
                axis, entry = future.result(timeout=720)
            except TimeoutError:
                axis = futures[future]
                entry = {
                    "label": AXES[axis]["label"],
                    "requested_model": str(AXES[axis]["model"]),
                    "model": str(AXES[axis]["model"]),
                    "exit_code": 1,
                    "output": str(review_dir / f"{axis}-output.md"),
                    "size": 0,
                    "failure_reason": "thread_timeout",
                }
            results[axis] = entry

    results["elapsed_seconds"] = round(time.time() - t0, 1)
    return results


EXTRACTION_PROMPT = (
    "Extract every discrete recommendation, finding, or claimed bug from the review. "
    "Return JSON matching the schema. For each finding: category, severity, a one-line title, "
    "description with the reviewer's evidence, file path if cited, proposed fix, "
    "and confidence 0.0-1.0 based on specificity of evidence. "
    "SKIP confirmatory observations that merely describe correct behavior. "
    "Only extract items that propose a change, flag a problem, or claim something is wrong/missing."
)


_UNCALIBRATED_RE = re.compile(
    r"(?:"
    r"(?:≥|>=|>|at least|minimum|must exceed)\s*(\d+(?:\.\d+)?)\s*"  # op NUMBER unit
    r"(?:%|pp|percentage points?|AUPRC|AUROC|PPV|NPV|F1|AUC)"
    r"|"
    r"(?:AUPRC|AUROC|PPV|NPV|F1|AUC)\s*(?:\w+\s+)?(?:≥|>=|>)\s*(\d+(?:\.\d+)?)"  # UNIT [by] op NUMBER
    r"|"
    r"(?:≥|>=|>)\s*(\d+(?:\.\d+)?)\s*(?:%|pp)[/,]"  # ≥95%/ or ≥50%, (slash-separated thresholds)
    r")",
    re.IGNORECASE,
)

# Source indicators — if these appear near the number, it's probably calibrated
_SOURCE_INDICATORS = re.compile(
    r"(?:paper|study|benchmark|calibrat|empirical|measured|observed|from\s+\w+\s+\d{4}|"
    r"doi|PMID|arXiv|Table\s+\d|Figure\s+\d|Supplementary)",
    re.IGNORECASE,
)


def _flag_uncalibrated_thresholds(text: str) -> str:
    """Flag numeric threshold claims that lack cited sources.

    Adds [UNCALIBRATED] tag to lines with threshold operators (≥X%, PPV ≥0.8)
    that don't mention a paper, benchmark, or empirical source nearby.
    """
    lines = text.split("\n")
    flagged = []
    for line in lines:
        if _UNCALIBRATED_RE.search(line) and not _SOURCE_INDICATORS.search(line):
            if "[UNCALIBRATED]" not in line:
                line = line.rstrip() + " [UNCALIBRATED]"
        flagged.append(line)
    return "\n".join(flagged)


def extract_claims(
    review_dir: Path,
    dispatch_result: dict,
) -> str | None:
    """Cross-family extraction: Flash extracts GPT outputs, GPT-Instant extracts Gemini outputs.

    Returns path to disposition.md, or None if no outputs to extract.
    """
    extraction_tasks: list[tuple[str, Path, str, str]] = []  # (axis, output_path, model, provider)
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}

    for axis, info in dispatch_result.items():
        if axis in skip_keys or not isinstance(info, dict):
            continue
        if info.get("size", 0) == 0:
            continue

        output_path = Path(info["output"])
        if not output_path.exists():
            continue

        model = info.get("model", "")

        # Cross-family: Gemini outputs → GPT extraction, GPT outputs → Gemini Flash extraction
        if "gemini" in model.lower():
            extraction_tasks.append((axis, output_path, "gpt-5.3-chat-latest", "openai"))
        else:
            extraction_tasks.append((axis, output_path, "gemini-3-flash-preview", "google"))

    if not extraction_tasks:
        return None

    print(
        f"Extracting claims from {len(extraction_tasks)} outputs...",
        file=sys.stderr,
    )

    def _extract_one(task: tuple[str, Path, str, str]) -> tuple[str, list[dict] | None]:
        axis, output_path, model, provider = task
        extraction_path = review_dir / f"{axis}-extraction.json"
        result = _call_llmx(
            provider=provider,
            model=model,
            context_path=output_path,
            prompt=EXTRACTION_PROMPT,
            output_path=extraction_path,
            schema=FINDING_SCHEMA,
            timeout=120,
        )
        if result["exit_code"] != 0:
            print(f"warning: extraction for {axis} failed: {result.get('error', 'unknown')}", file=sys.stderr)
            return axis, None
        if result["size"] > 0:
            try:
                data = json.loads(extraction_path.read_text())
                return axis, data.get("findings", [])
            except (json.JSONDecodeError, KeyError) as e:
                print(f"warning: extraction for {axis} returned invalid JSON: {e}", file=sys.stderr)
                # Fall back to raw text
                return axis, None
        print(f"warning: extraction for {axis} produced empty output", file=sys.stderr)
        return axis, None

    # Parallel extraction
    axis_findings: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=len(extraction_tasks)) as pool:
        for axis, findings in pool.map(_extract_one, extraction_tasks):
            if findings:
                axis_findings[axis] = findings

    if not axis_findings:
        return None

    # Merge findings across axes — keyword overlap for cross-model dedup
    def _fingerprint(f: dict) -> set[str]:
        """Extract significant keywords for fuzzy matching."""
        text = f"{f.get('title', '')} {f.get('file', '')} {f.get('description', '')[:200]}"
        words = set(re.findall(r"[a-z_]{4,}", text.lower()))
        # Remove common stop-words that inflate false matches
        words -= {"this", "that", "with", "from", "should", "could", "would", "does", "have", "will", "also", "been"}
        return words

    merged_findings: list[dict] = []
    seen: list[tuple[set[str], dict]] = []  # (keywords, finding)
    for axis, findings in axis_findings.items():
        source_label = dispatch_result[axis].get("label", axis)
        source_model = dispatch_result[axis].get("model", "unknown")
        for f in findings:
            f["source_axis"] = axis
            f["source_model"] = source_model
            f["source_label"] = source_label
            fp = _fingerprint(f)
            # Check for overlap with existing findings (Jaccard > 0.3)
            matched = False
            for existing_fp, existing in seen:
                if len(fp & existing_fp) > 0 and len(fp & existing_fp) / len(fp | existing_fp) > 0.3:
                    existing.setdefault("also_found_by", []).append(source_label)
                    existing["cross_model"] = True
                    existing["confidence"] = min(1.0, existing.get("confidence", 0.5) + 0.2)
                    matched = True
                    break
            if not matched:
                seen.append((fp, f))
                merged_findings.append(f)

    # Sort: cross-model agreements first, then by severity, then confidence
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    merged_findings.sort(key=lambda f: (
        0 if f.get("cross_model") else 1,
        severity_order.get(f.get("severity", "low"), 3),
        -(f.get("confidence", 0)),
    ))

    # Renumber
    for i, f in enumerate(merged_findings, 1):
        f["id"] = i

    # Write structured JSON
    structured_path = review_dir / "findings.json"
    structured_path.write_text(json.dumps({"findings": merged_findings}, indent=2) + "\n")

    # Write human-readable disposition
    extractions: list[str] = []
    for f in merged_findings:
        source = f.get("source_label", "unknown")
        also = f.get("also_found_by", [])
        agreement = f" **[CROSS-MODEL: also {', '.join(also)}]**" if also else ""
        conf = f.get("confidence", 0)
        extractions.append(
            f"{f['id']}. **[{f.get('severity', '?').upper()}]** {f.get('title', '?')}{agreement}\n"
            f"   Category: {f.get('category', '?')} | Confidence: {conf:.1f} | Source: {source}\n"
            f"   {f.get('description', '')}\n"
            f"   File: {f.get('file', 'N/A')}\n"
            f"   Fix: {f.get('fix', 'N/A')}"
        )

    if not extractions:
        return None

    disposition = review_dir / "disposition.md"
    merged = "\n\n---\n\n".join(extractions)

    # Flag uncalibrated thresholds — numeric claims without cited sources
    merged = _flag_uncalibrated_thresholds(merged)

    response_template = (
        "\n\n---\n\n"
        "## Agent Response (fill before implementing)\n\n"
        "### Where I disagree with the disposition:\n"
        '<!-- "Nowhere" is valid. Don\'t invent disagreements. -->\n\n\n'
        "### Context I had that the models didn't:\n"
        "<!-- If context file was comprehensive, say so. -->\n\n"
    )
    cross_model_count = sum(1 for f in merged_findings if f.get("cross_model"))
    header = (
        f"# Review Findings — {date.today().isoformat()}\n\n"
        f"**{len(merged_findings)} findings** from {len(axis_findings)} axes"
        f" ({cross_model_count} cross-model agreements)\n"
        f"Structured data: `findings.json`\n\n"
    )
    disposition.write_text(header + merged + response_template)
    return str(disposition)


def verify_claims(
    review_dir: Path,
    disposition_path: str,
    project_dir: Path,
) -> str:
    """Verify extracted claims against the actual codebase.

    Checks if cited files and symbols exist. Grades each claim:
    - CONFIRMED: all cited files/symbols found
    - HALLUCINATED: cited file does not exist in project
    - UNVERIFIABLE: no file references to check

    Returns path to verified-disposition.md.
    """
    disposition_text = Path(disposition_path).read_text()

    # Parse claims: numbered lines (e.g., "1. Function X in foo.py has bug")
    claims: list[dict] = []
    current_section = ""
    for line in disposition_text.splitlines():
        section_match = re.match(r"^##\s+(.+)", line)
        if section_match:
            current_section = section_match.group(1).strip()
            continue
        claim_match = re.match(r"^(\d+)\.\s+(.+)", line.strip())
        if claim_match:
            claims.append({
                "num": int(claim_match.group(1)),
                "text": claim_match.group(2),
                "section": current_section,
            })

    if not claims:
        print("No numbered claims found in disposition.", file=sys.stderr)
        return disposition_path

    # Verify each claim
    verified: list[dict] = []
    for claim in claims:
        text = claim["text"]
        verdict = "UNVERIFIABLE"
        notes: list[str] = []

        # Extract file references: path/file.ext or file.ext:line or `file.ext`
        file_refs = re.findall(
            r"`?([a-zA-Z_][\w/.-]*\.(?:py|js|ts|md|sh|json|yaml|yml|toml|cfg|sql|html|css|clj|cljc|edn))(?::(\d+))?`?",
            text,
        )

        if not file_refs:
            verified.append({**claim, "verdict": verdict, "notes": "no file references"})
            continue

        all_found = True
        for filepath, line_str in file_refs:
            candidates = list(project_dir.rglob(filepath))
            if not candidates:
                verdict = "HALLUCINATED"
                notes.append(f"{filepath} not found")
                all_found = False
            else:
                found_path = candidates[0]
                if line_str:
                    line_num = int(line_str)
                    try:
                        lines = found_path.read_text().splitlines()
                        if line_num > len(lines):
                            notes.append(f"{filepath}:{line_num} beyond EOF ({len(lines)} lines)")
                        else:
                            notes.append(f"{filepath} exists, L{line_num} readable")
                    except Exception:
                        notes.append(f"{filepath} exists but unreadable")
                else:
                    notes.append(f"{filepath} exists")

        if all_found and verdict != "HALLUCINATED":
            verdict = "CONFIRMED"

        verified.append({**claim, "verdict": verdict, "notes": "; ".join(notes)})

    # Stats
    confirmed = sum(1 for v in verified if v["verdict"] == "CONFIRMED")
    hallucinated = sum(1 for v in verified if v["verdict"] == "HALLUCINATED")
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


## Current tests

from __future__ import annotations

import importlib.util
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

        with patch.object(model_review, "llmx_chat", mock_chat):
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

        with patch.object(model_review, "llmx_chat", mock_chat):
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
                    "items": {"type": "object", "properties": {"name": {"type": "string"}}},
                }
            },
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
            with patch.object(model_review, "llmx_chat", exploding_chat):
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
            with patch.object(model_review, "llmx_chat", capture_chat):
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
            with patch.object(model_review, "llmx_chat", capture_chat):
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
