# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler/hacky approaches because they're 'faster to implement'
- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort
- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters

# Plan-Close Review Packet

- Repo: `/Users/alien/Projects/skills`
- Mode: `worktree`
- Ref: `HEAD vs current worktree`

## Scope

- Target users: agents and repo hooks consuming `~/Projects/skills` across local project repos; not a public SaaS surface
- Scale: currently ~18 active skills, ~33 hooks, several sibling repos consuming overview/research/review hooks; designed for repeated automation across many local repos
- Rate of change: high; dispatch patterns and skill instructions are still changing weekly

## Migration note

- Active-path migration target: normal automation should stop composing raw `llmx chat` calls and route through the shared dispatch helper instead.
- Remaining live compatibility boundary: `hooks/generate-overview.sh` still accepts sibling repos' existing `OVERVIEW_MODEL` config because `/Users/alien/Projects/{genomics,intel,meta,selve,arc-agi,research-mcp,skills}/.claude/overview.conf` already set it.
- Removal condition for that seam: once those repos migrate their overview configs to `OVERVIEW_PROFILE`, delete the `OVERVIEW_MODEL` -> profile mapping in `hooks/generate-overview.sh`.

## Touched Files

- `shared/llm_dispatch.py`
- `review/scripts/model-review.py`
- `hooks/generate-overview.sh`
- `hooks/pretool-llmx-guard.sh`
- `hooks/test_pretool_llmx_guard.py`
- `research-ops/scripts/run-cycle.sh`

## Git Status

```text
M .claude/overview-marker-source
 M .claude/overviews/source-overview.md
 M _archive/architect/SKILL.md
 M brainstorm/SKILL.md
 M brainstorm/references/llmx-dispatch.md
 M hooks/epistemic-domain-router.sh
 M hooks/generate-overview.sh
 M hooks/permission-auto-allow.sh
 M hooks/pretool-llmx-guard.sh
 M improve/SKILL.md
 M llmx-guide/SKILL.md
 M observe/SKILL.md
 M research-ops/SKILL.md
 M research-ops/scripts/run-cycle.sh
 M review/SKILL.md
 M review/lenses/plan-close-review.md
 M review/scripts/model-review.py
 M review/scripts/test_model_review.py
 M upgrade/SKILL.md
```

## Diff Stat

```text
hooks/generate-overview.sh        |  92 +++++++++++++++++------
 hooks/pretool-llmx-guard.sh       |  41 ++++++++---
 research-ops/scripts/run-cycle.sh |  49 +++++++++----
 review/scripts/model-review.py    | 150 ++++++++++++++------------------------
 4 files changed, 188 insertions(+), 144 deletions(-)
```

## Unified Diff

```diff
hooks/generate-overview.sh --- 1/6 --- Bash
  1 #!/usr/bin/env bash                    1 #!/usr/bin/env bash
  2 # generate-overview.sh — Shared ove    2 # generate-overview.sh — Shared ove
  . rview generator: repomix → prompt →    . rview generator: repomix → shared d
  .  llmx/Gemini → markdown                . ispatch → markdown
  3 # Used by sessionend-overview-trigg    3 # Used by sessionend-overview-trigg
  . er.sh and manual invocation.           . er.sh and manual invocation.
  4 #                                      4 #
  5 # Config: reads .claude/overview.co    5 # Config: reads .claude/overview.co
  . nf from project root (or env vars).    . nf from project root (or env vars).

hooks/generate-overview.sh --- 2/6 --- Bash
 16  16 
 17  17 # --- Defaults (overridden by .claude/overview.conf or env) ---
 18  18 OVERVIEW_TYPES="${OVERVIEW_TYPES:-source}"
 ..  19 OVERVIEW_PROFILE="${OVERVIEW_PROFILE:-}"
 19  20 OVERVIEW_MODEL="${OVERVIEW_MODEL:-gemini-3-flash-preview}"
 20  21 OVERVIEW_OUTPUT_DIR="${OVERVIEW_OUTPUT_DIR:-.claude/overviews}"
 21  22 OVERVIEW_PROMPT_DIR="${OVERVIEW_PROMPT_DIR:-.claude/overview-prompts}"

hooks/generate-overview.sh --- 3/6 --- Bash
 79  80 
 80  81 # Re-read after config load (env vars may have been set)
 81  82 OVERVIEW_TYPES="${OVERVIEW_TYPES:-source}"
 ..  83 OVERVIEW_PROFILE="${OVERVIEW_PROFILE:-}"
 82  84 OVERVIEW_MODEL="${OVERVIEW_MODEL:-gemini-3-flash-preview}"
 83  85 OVERVIEW_OUTPUT_DIR="${OVERVIEW_OUTPUT_DIR:-.claude/overviews}"
 84  86 OVERVIEW_PROMPT_DIR="${OVERVIEW_PROMPT_DIR:-.claude/overview-prompts}"

hooks/generate-overview.sh --- 4/6 --- Bash
 88 check_deps() {                        90 check_deps() {
 89   local missing=()                    91   local missing=()
 90   command -v repomix &>/dev/null ||   92   command -v repomix &>/dev/null ||
 ..  missing+=("repomix")                 ..  missing+=("repomix")
 91   command -v llmx &>/dev/null || mi   93   command -v uv &>/dev/null || miss
 .. ssing+=("llmx")                       .. ing+=("uv")
 92   if [[ ${#missing[@]} -gt 0 ]]; th   94   if [[ ${#missing[@]} -gt 0 ]]; th
 .. en                                    .. en
 93     echo "Missing dependencies: ${m   95     echo "Missing dependencies: ${m
 .. issing[*]}" >&2                       .. issing[*]}" >&2
 94     exit 1                            96     exit 1
 95   fi                                  97   fi
 96 }                                     98 }
 ..                                       99 
 ..                                      100 resolve_overview_profile() {
 ..                                      101   if [[ -n "$OVERVIEW_PROFILE" ]]; 
 ..                                      ... then
 ..                                      102     echo "$OVERVIEW_PROFILE"
 ..                                      103     return 0
 ..                                      104   fi
 ..                                      105 
 ..                                      106   case "$OVERVIEW_MODEL" in
 ..                                      107     gemini-3-flash-preview)
 ..                                      108       echo "fast_extract"
 ..                                      109       ;;
 ..                                      110     gemini-3.1-pro-preview)
 ..                                      111       echo "deep_review"
 ..                                      112       ;;
 ..                                      113     gpt-5.4)
 ..                                      114       echo "gpt_general"
 ..                                      115       ;;
 ..                                      116     *)
 ..                                      117       echo "ERROR: No dispatch prof
 ..                                      ... ile mapping for OVERVIEW_MODEL=$OVE
 ..                                      ... RVIEW_MODEL" >&2
 ..                                      118       return 1
 ..                                      119       ;;
 ..                                      120   esac
 ..                                      121 }
 ..                                      122 
 ..                                      123 profile_token_limit() {
 ..                                      124   local profile="$1"
 ..                                      125   case "$profile" in
 ..                                      126     gpt_general|formal_review)
 ..                                      127       echo 120000
 ..                                      128       ;;
 ..                                      129     *)
 ..                                      130       echo 900000
 ..                                      131       ;;
 ..                                      132   esac
 ..                                      133 }
 97                                      134 
 98 # --- Generate a single overview --  135 # --- Generate a single overview --
 .. -                                    ... -
 99 generate_one() {                     136 generate_one() {

hooks/generate-overview.sh --- 5/6 --- Bash
138                                      175 
139   mkdir -p "$output_dir"             176   mkdir -p "$output_dir"
140                                      177 
141   local temp_prompt                  178   local temp_prompt dispatch_profil
...                                      ... e
142   temp_prompt=$(mktemp /tmp/overvie  179   temp_prompt=$(mktemp /tmp/overvie
... w-prompt-$$-${type}-XXXXXX.txt)      ... w-prompt-$$-${type}-XXXXXX)
...                                      180   dispatch_profile=$(resolve_overvi
...                                      ... ew_profile) || return 1
143                                      181 
144   # Step 1: Extract content with re  182   # Step 1: Extract content with re
... pomix (--stdout avoids clipboard ra  ... pomix (--stdout avoids clipboard ra
... ces)                                 ... ces)
145   local include_pattern=""           183   local include_pattern=""

hooks/generate-overview.sh --- 6/6 --- Bash
178   prompt_size=$(wc -c < "$temp_prom  216   prompt_size=$(wc -c < "$temp_prom
... pt")                                 ... pt")
179   prompt_tokens=$((prompt_size / 4)  217   prompt_tokens=$((prompt_size / 4)
... )                                    ... )
180                                      218 
181   echo "[$type] Generating (~${prom  219   echo "[$type] Generating (~${prom
... pt_tokens} tokens, model: $OVERVIEW  ... pt_tokens} tokens, profile: $dispat
... _MODEL)..."                          ... ch_profile)..."
182                                      220 
183   # Step 4: Check token estimate ag  221   # Step 4: Check token estimate ag
... ainst model limits                   ... ainst model limits
...                                      222   local token_limit
...                                      223   token_limit=$(profile_token_limit
...                                      ...  "$dispatch_profile")
184   if [[ $prompt_tokens -gt 900000 ]  224   if [[ $prompt_tokens -gt $token_l
... ]; then                              ... imit ]]; then
185     echo "[$type] ERROR: prompt (~$  225     echo "[$type] ERROR: prompt (~$
... {prompt_tokens} tokens) exceeds saf  ... {prompt_tokens} tokens) exceeds saf
... e limit for $OVERVIEW_MODEL. Tighte  ... e limit (${token_limit}) for $dispa
... n OVERVIEW_EXCLUDE or dirs." >&2     ... tch_profile. Tighten OVERVIEW_EXCLU
...                                      ... DE or dirs." >&2
186     rm -f "$temp_prompt"             226     rm -f "$temp_prompt"
187     return 1                         227     return 1
188   fi                                 228   fi
189                                      229 
190   # Step 5: Generate via llmx (atom  230   # Step 5: Generate via shared dis
... ic write — temp file, mv on success  ... patch (atomic write — temp file, mv
... )                                    ...  on success)
191   local llmx_stderr llmx_output      231   local dispatch_meta dispatch_erro
...                                      ... r llm_output dispatch_exit resolved
...                                      ... _model
192   llmx_stderr=$(mktemp /tmp/overvie  232   dispatch_meta=$(mktemp /tmp/overv
... w-llmx-stderr-XXXXXX)                ... iew-dispatch-meta-XXXXXX)
...                                      233   dispatch_error=$(mktemp /tmp/over
...                                      ... view-dispatch-error-XXXXXX)
193   llmx_output=$(mktemp "${output_di  234   llm_output=$(mktemp "${output_dir
... r}/.overview-tmp-${type}-XXXXXX")    ... }/.overview-tmp-${type}-XXXXXX")
194                                      235 
195   # Disable errexit to capture exit  236   # Disable errexit to capture exit
...  code (set -e would skip cleanup on  ...  code (set -e would skip cleanup on
...  failure)                            ...  failure)
196   set +e                             237   set +e
...                                      238   uv run python3 "$SCRIPT_DIR/../sc
...                                      ... ripts/llm-dispatch.py" \
...                                      239     --profile "$dispatch_profile" \
197   cat "$temp_prompt" | timeout 300   240     --context "$temp_prompt" \
... llmx chat -m "$OVERVIEW_MODEL" 2>"$  ... 
... llmx_stderr" > "$llmx_output"        ... 
...                                      241     --prompt "Write the requested c
...                                      ... odebase overview in markdown." \
...                                      242     --output "$llm_output" \
...                                      243     --meta "$dispatch_meta" \
...                                      244     --error-output "$dispatch_error
...                                      ... " \
...                                      245     >/dev/null
198   local llmx_exit=$?                 246   dispatch_exit=$?
199   set -e                             247   set -e
200                                      248 
201   # Cleanup prompt (no longer neede  249   # Cleanup prompt (no longer neede
... d)                                   ... d)
202   rm -f "$temp_prompt"               250   rm -f "$temp_prompt"
203                                      251 
204   # Check for failure: non-zero exi  252   # Check for failure: non-zero exi
... t or empty output                    ... t or empty output
205   if [[ $llmx_exit -ne 0 ]] || [[ !  253   if [[ $dispatch_exit -ne 0 ]] || 
...  -s "$llmx_output" ]]; then          ... [[ ! -s "$llm_output" ]]; then
206     echo "[$type] ERROR: llmx faile  254     echo "[$type] ERROR: dispatch f
... d (exit=$llmx_exit). stderr:" >&2    ... ailed (exit=$dispatch_exit)." >&2
207     cat "$llmx_stderr" >&2           255     [[ -f "$dispatch_error" ]] && c
...                                      ... at "$dispatch_error" >&2
...                                      256     [[ -f "$dispatch_meta" ]] && ca
...                                      ... t "$dispatch_meta" >&2
208     rm -f "$llmx_stderr" "$llmx_out  257     rm -f "$dispatch_error" "$dispa
... put"                                 ... tch_meta" "$llm_output"
209     return 1                         258     return 1
210   fi                                 259   fi
...                                      260   resolved_model=$(python3 -c 'impo
...                                      ... rt json,sys; print(json.load(open(s
...                                      ... ys.argv[1])).get("resolved_model","
...                                      ... unknown"))' "$dispatch_meta" 2>/dev
...                                      ... /null || echo "unknown")
211   rm -f "$llmx_stderr"               261   rm -f "$dispatch_error"
212                                      262 
213   # Step 6: Prepend freshness metad  263   # Step 6: Prepend freshness metad
... ata to temp output, then atomic mv   ... ata to temp output, then atomic mv
214   local git_sha gen_ts meta_line     264   local git_sha gen_ts meta_line
215   git_sha=$(echo "$COMMIT_HASH" | h  265   git_sha=$(echo "$COMMIT_HASH" | h
... ead -c 7)                            ... ead -c 7)
216   gen_ts=$(date -u +"%Y-%m-%dT%H:%M  266   gen_ts=$(date -u +"%Y-%m-%dT%H:%M
... :%SZ")                               ... :%SZ")
217   meta_line="<!-- Generated: ${gen_  267   meta_line="<!-- Generated: ${gen_
... ts} | git: ${git_sha} | model: ${OV  ... ts} | git: ${git_sha} | profile: ${
... ERVIEW_MODEL} -->"                   ... dispatch_profile} | model: ${resolv
...                                      ... ed_model} -->"
218                                      268 
219   local tmp_final                    269   local tmp_final
220   tmp_final=$(mktemp "${output_dir}  270   tmp_final=$(mktemp "${output_dir}
... /.overview-final-${type}-XXXXXX")    ... /.overview-final-${type}-XXXXXX")
221   { echo "$meta_line"; echo ""; cat  271   { echo "$meta_line"; echo ""; cat
...  "$llmx_output"; } > "$tmp_final"    ...  "$llm_output"; } > "$tmp_final"
222   rm -f "$llmx_output"               272   rm -f "$llm_output" "$dispatch_me
...                                      ... ta"
223                                      273 
224   # Atomic move — old overview pres  274   # Atomic move — old overview pres
... erved until this succeeds            ... erved until this succeeds
225   mv "$tmp_final" "$output_file"     275   mv "$tmp_final" "$output_file"

hooks/pretool-llmx-guard.sh --- Bash
 94                                       94 
 95 # --- ADVISORY checks (warnings onl   95 # --- ADVISORY checks (warnings onl
 .. y) ---                                .. y) ---
 96                                       96 
 97 # 0. BLOCK llmx chat CLI — use Pyth   97 # 0. BLOCK default llmx chat-style 
 .. on API instead                        .. CLI automation — use shared dispatc
 ..                                       .. h instead
 98 # The CLI has 5 known failure modes   98 # The CLI has recurring failure mod
 ..  in agent context (multi-file drops   .. es in agent context (multi-file dro
 .. , 0-byte -o,                          .. ps, 0-byte -o,
 99 # rate limit loops, stdin EOF, pipe   99 # rate limit loops, stdin EOF, pipe
 ..  masking). The Python API bypasses    ..  masking). Keep non-chat subcommand
 .. all of them.                          .. s available.
 ..                                      100 LLMX_NEXT_TOKEN=$(echo "$CMD" | sed
 ..                                      ...  -nE 's/.*(^|[;&|[:space:]])llmx[[:
 ..                                      ... space:]]+([^[:space:]]+).*/\2/p' | 
 ..                                      ... head -1)
 ..                                      101 case "$LLMX_NEXT_TOKEN" in
 ..                                      102   image|vision|svg|research|keys|ba
 ..                                      ... tch|help|--help|-h|"")
 ..                                      103     ;;
 ..                                      104   chat|-*|\"*|\'*)
 ..                                      105     echo "[llmx-guard] BLOCKED: Do 
 ..                                      ... not use llmx chat-style CLI automat
 ..                                      ... ion. Use the shared dispatch helper
 ..                                      ...  instead:" >&2
 ..                                      106     echo "  uv run python3 ~/Projec
 ..                                      ... ts/skills/scripts/llm-dispatch.py \
 ..                                      ... \" >&2
 ..                                      107     echo "    --profile fast_extrac
 ..                                      ... t \\" >&2
 ..                                      108     echo "    --context context.md 
 ..                                      ... \\" >&2
 ..                                      109     echo "    --prompt 'Analyze thi
 ..                                      ... s' \\" >&2
 ..                                      110     echo "    --output /tmp/result.
 ..                                      ... md" >&2
 ..                                      111     ~/Projects/skills/hooks/hook-tr
 ..                                      ... igger-log.sh "llmx-chat-blocked" "b
 ..                                      ... lock" "$(echo "$CMD" | head -c 200)
 ..                                      ... " 2>/dev/null || true
 ..                                      112     exit 2
 ..                                      113     ;;
 ..                                      114   *)
100 if echo "$CMD" | grep -qE 'llmx\s+c  115     if echo "$CMD" | grep -qE '(^|[
... hat'; then                           ... ;&|[:space:]])llmx([[:space:]]+|$)'
...                                      ... ; then
101   echo "[llmx-guard] BLOCKED: Do no  116       echo "[llmx-guard] BLOCKED: D
... t use 'llmx chat' CLI. Use the Pyth  ... o not use llmx default chat mode fo
... on API instead:" >&2                 ... r automation. Use the shared dispat
...                                      ... ch helper instead:" >&2
...                                      117       echo "  uv run python3 ~/Proj
...                                      ... ects/skills/scripts/llm-dispatch.py
...                                      ...  \\" >&2
...                                      118       echo "    --profile fast_extr
...                                      ... act \\" >&2
102   echo "  from llmx.api import chat  119       echo "    --context context.m
...  as llmx_chat" >&2                   ... d \\" >&2
103   echo "  r = llmx_chat(prompt=...,  120       echo "    --prompt 'Analyze t
...  provider='google', model='gemini-3  ... his' \\" >&2
... .1-pro-preview', api_only=True, tim  ... 
... eout=300)" >&2                       ... 
104   echo "  Bootstrap: sys.path.inser  121       echo "    --output /tmp/resul
... t(0, glob.glob(str(Path.home() / '.  ... t.md" >&2
... local/share/uv/tools/llmx/lib/pytho  ... 
... n*/site-packages'))[0])" >&2         ... 
105   ~/Projects/skills/hooks/hook-trig  122       ~/Projects/skills/hooks/hook-
... ger-log.sh "llmx-chat-blocked" "blo  ... trigger-log.sh "llmx-chat-blocked" 
... ck" "$(echo "$CMD" | head -c 200)"   ... "block" "$(echo "$CMD" | head -c 20
... 2>/dev/null || true                  ... 0)" 2>/dev/null || true
106   exit 2                             123       exit 2
107 fi                                   124     fi
...                                      125     ;;
...                                      126 esac
108                                      127 
109 # 0a. Gemini Pro without --stream —  128 # 0a. Gemini Pro without --stream —
...  CLI transport hangs on thinking mo  ...  CLI transport hangs on thinking mo
... dels + piped input, hits capacity l  ... dels + piped input, hits capacity l
... imits                                ... imits
110 #    Flash/Lite on CLI is fine (non  129 #    Flash/Lite on CLI is fine (non
... -thinking, better capacity) — no wa  ... -thinking, better capacity) — no wa
... rning needed                         ... rning needed

research-ops/scripts/run-cycle.sh --- 1/3 --- Bash
 1 #!/usr/bin/env bash                    1 #!/usr/bin/env bash
 2 # Rate-limit-aware research cycle r    2 # Rate-limit-aware research cycle r
 . unner.                                 . unner.
 3 # If Claude is rate-limited (>=6 pr    3 # If Claude is rate-limited (>=6 pr
 . ocesses), runs via llmx (Gemini Fla    . ocesses), runs through the shared P
 . sh)                                    . ython
 4 # instead of loading the skill into    4 # dispatch helper instead of raw ll
 .  a Claude session.                     . mx CLI subprocess dispatch.
 5 #                                      5 #
 6 # Usage: run-cycle.sh [project_dir]    6 # Usage: run-cycle.sh [project_dir]
 7 #   Or from Claude Code: ! ~/Projec    7 #   Or from Claude Code: ! ~/Projec
 . ts/skills/research-cycle/scripts/ru    . ts/skills/research-cycle/scripts/ru
 . n-cycle.sh                             . n-cycle.sh

research-ops/scripts/run-cycle.sh --- 2/3 --- Bash
17 echo "Claude processes: $CLAUDE_PRO   17 echo "Claude processes: $CLAUDE_PRO
.. CS (threshold: $MAX_PROCS)"           .. CS (threshold: $MAX_PROCS)"
18                                       18 
19 if [ "$CLAUDE_PROCS" -ge "$MAX_PROC   19 if [ "$CLAUDE_PROCS" -ge "$MAX_PROC
.. S" ]; then                            .. S" ]; then
20     echo "Rate-limited mode: routin   20     echo "Rate-limited mode: routin
.. g through Gemini Flash via llmx"      .. g through shared LLM dispatch"
21                                       21 
22     # Gather state (same script the   22     # Gather state (same script the
..  skill uses)                          ..  skill uses)
23     STATE=$("$SKILL_DIR/scripts/gat   23     STATE=$("$SKILL_DIR/scripts/gat
.. her-cycle-state.sh" "$PROJECT_DIR"    .. her-cycle-state.sh" "$PROJECT_DIR" 
.. 2>&1 | head -80)                      .. 2>&1 | head -80)

research-ops/scripts/run-cycle.sh --- 3/3 --- Bash
33         CYCLE_CONTENT=$(head -200 "   33         CYCLE_CONTENT=$(head -200 "
.. $CYCLE_FILE")                         .. $CYCLE_FILE")
34     fi                                34     fi
..                                       35 
..                                       36     cycle_context=$(mktemp /tmp/cyc
..                                       .. le-dispatch-context-XXXXXX)
..                                       37     cycle_output=$(mktemp /tmp/cycl
..                                       .. e-dispatch-output-XXXXXX)
..                                       38     cycle_meta=$(mktemp /tmp/cycle-
..                                       .. dispatch-meta-XXXXXX)
..                                       39     cycle_error=$(mktemp /tmp/cycle
..                                       .. -dispatch-error-XXXXXX)
35                                       40 
36     cat > /tmp/cycle-llmx-prompt.md   41     cat > "$cycle_context" << PROMP
..  << PROMPT_EOF                        .. T_EOF
37 # Research Cycle Tick (rate-limited   42 # Research Cycle Tick (rate-limited
..  mode via Gemini Flash)               ..  mode)
38                                       43 
39 Project: $PROJECT_DIR                 44 Project: $PROJECT_DIR
40 Project name: $(basename "$PROJECT_   45 Project name: $(basename "$PROJECT_
.. DIR")                                 .. DIR")
41                                       46 
42 ## Current State                      47 ## Current State
43 $STATE                                48 $STATE
44                                       49 
45 ## CYCLE.md (current)                 50 ## CYCLE.md (current)
46 $CYCLE_CONTENT                        51 $CYCLE_CONTENT
47                                       52 
48 ## Instructions                       53 ## Instructions
49 You are running one tick of the res   54 You are running one tick of the res
.. earch cycle. Pick the highest-prior   .. earch cycle. Pick the highest-prior
.. ity phase:                            .. ity phase:
50 1. Recent execution without verific   55 1. Recent execution without verific
.. ation → verify                        .. ation → verify
51 2. Approved items in queue → execut   56 2. Approved items in queue → execut
.. e (skip — can't execute code via ll   .. e (skip — can't execute code via ll
.. mx)                                   .. mx)
52 3. Active plan not yet reviewed → r   57 3. Active plan not yet reviewed → r
.. eview                                 .. eview
53 4. Gaps without plan → plan           58 4. Gaps without plan → plan
54 5. Discoveries without gap analysis   59 5. Discoveries without gap analysis
..  → gap-analyze                        ..  → gap-analyze
55 6. Verification done without improv   60 6. Verification done without improv
.. e → improve                           .. e → improve
56 7. Nothing pending → discover         61 7. Nothing pending → discover
57                                       62 
58 For discover: search for new develo   63 For discover: search for new develo
.. pments relevant to this project.      .. pments relevant to this project.
59 For gap-analyze: analyze discoverie   64 For gap-analyze: analyze discoverie
.. s and write gaps.                     .. s and write gaps.
60 For plan/review: analyze and write    65 For plan/review: analyze and write 
.. recommendations.                      .. recommendations.
61                                       66 
62 Output your findings as markdown th   67 Output your findings as markdown th
.. at should be appended to CYCLE.md.    .. at should be appended to CYCLE.md.
63 Start with "## [Phase]: [descriptio   68 Start with "## [Phase]: [descriptio
.. n]" and include a date.               .. n]" and include a date.
64 Be concise — this will be appended    69 Be concise — this will be appended 
.. to a file.                            .. to a file.
65 PROMPT_EOF                            70 PROMPT_EOF
66                                       71 
67     OUTPUT=$(llmx chat -m gemini-3-   72     set +e
.. flash-preview \                       .. 
68         -f /tmp/cycle-llmx-prompt.m   73     uv run python3 "$SKILL_DIR/../s
.. d \                                   .. cripts/llm-dispatch.py" \
69         --timeout 120 \               74         --profile cheap_tick \
..                                       75         --context "$cycle_context" 
..                                       .. \
70         "Run one research cycle tic   76         --prompt "Run one research 
.. k. Output markdown for CYCLE.md." 2   .. cycle tick. Output markdown for CYC
.. >/dev/null)                           .. LE.md." \
..                                       77         --output "$cycle_output" \
..                                       78         --meta "$cycle_meta" \
..                                       79         --error-output "$cycle_erro
..                                       .. r" \
..                                       80         >/dev/null
..                                       81     dispatch_exit=$?
..                                       82     set -e
71                                       83 
72     if [ -n "$OUTPUT" ]; then         84     if [ "$dispatch_exit" -eq 0 ] &
..                                       .. & [ -s "$cycle_output" ]; then
73         echo "" >> "$CYCLE_FILE"      85         echo "" >> "$CYCLE_FILE"
74         echo "$OUTPUT" >> "$CYCLE_F   86         cat "$cycle_output" >> "$CY
.. ILE"                                  .. CLE_FILE"
75         echo "---"                    87         echo "---"
76         echo "Appended to CYCLE.md    88         echo "Appended to CYCLE.md 
.. via Gemini Flash (rate-limited mode   .. via shared dispatch (rate-limited m
.. )"                                    .. ode)"
77         echo "$OUTPUT" | head -5      89         head -5 "$cycle_output"
78     else                              90     else
79         echo "llmx returned empty o   91         echo "Dispatch failed — ski
.. utput — skipping this tick"           .. pping this tick" >&2
..                                       92         if [ -s "$cycle_error" ]; t
..                                       .. hen
..                                       93             cat "$cycle_error" >&2
..                                       94         elif [ -s "$cycle_meta" ]; 
..                                       .. then
..                                       95             cat "$cycle_meta" >&2
..                                       96         fi
80     fi                                97     fi
..                                       98 
..                                       99     rm -f "$cycle_context" "$cycle_
..                                       .. output" "$cycle_meta" "$cycle_error
..                                       .. "
81 else                                 100 else
82     echo "Normal mode: running via   101     echo "Normal mode: running via 
.. Claude skill"                        ... Claude skill"
83     echo "Use /research cycle in yo  102     echo "Use /research cycle in yo
.. ur Claude session instead."          ... ur Claude session instead."

review/scripts/model-review.py --- 1/16 --- Python
 30 from datetime import date             30 from datetime import date
 31 from pathlib import Path              31 from pathlib import Path
 32                                       32 
 33 # llmx is editable-installed as a u   33 ROOT = Path(__file__).resolve().par
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
 39     if _tool_site:                    34 if str(ROOT) not in sys.path:
 40         sys.path.insert(0, _tool_si   .. 
 .. te[0])                                .. 
 41     sys.path.insert(0, str(Path.hom   35     sys.path.insert(0, str(ROOT))
 .. e() / "Projects" / "llmx"))           .. 
 42     from llmx.api import chat as ll   36 
 .. mx_chat                               .. 
 ..                                       37 import shared.llm_dispatch as dispa
 ..                                       .. tch_core
 43                                       38 
 44 # --- Structured output schema (bot   39 # --- Structured output schema (bot
 .. h models return this) ---             .. h models return this) ---
 45                                       40 

review/scripts/model-review.py --- 2/16 --- Python
 75 AXES = {                              70 AXES = {
 76     "arch": {                         71     "arch": {
 77         "label": "Gemini (architect   72         "label": "Gemini (architect
 .. ure/patterns)",                       .. ure/patterns)",
 78         "model": "gemini-3.1-pro-pr   .. 
 .. eview",                               .. 
 79         "provider": "google",         73         "profile": "deep_review",
 80         "api_kwargs": {"timeout": 3   .. 
 .. 00},                                  .. 
 81         "prompt": """\                74         "prompt": """\
 82 <system>                              75 <system>
 83 You are reviewing a codebase. Be co   76 You are reviewing a codebase. Be co
 .. ncrete. No platitudes. Reference sp   .. ncrete. No platitudes. Reference sp
 .. ecific code, configs, and findings.   .. ecific code, configs, and findings.
 ..  It is {date}.                        ..  It is {date}.

review/scripts/model-review.py --- 3/16 --- Python
108     },                               101     },
109     "formal": {                      102     "formal": {
110         "label": "GPT-5.4 (quantita  103         "label": "GPT-5.4 (quantita
... tive/formal)",                       ... tive/formal)",
111         "model": "gpt-5.4",          ... 
112         "provider": "openai",        104         "profile": "formal_review",
113         "api_kwargs": {"timeout": 6  ... 
... 00, "reasoning_effort": "high", "ma  ... 
... x_tokens": 32768},                   ... 
114         "prompt": """\               105         "prompt": """\
115 <system>                             106 <system>
116 You are performing QUANTITATIVE and  107 You are performing QUANTITATIVE and
...  FORMAL analysis. Other reviewers h  ...  FORMAL analysis. Other reviewers h
... andle qualitative pattern review. F  ... andle qualitative pattern review. F
... ocus on what they can't do well. Be  ... ocus on what they can't do well. Be
...  precise. Show your reasoning. No h  ...  precise. Show your reasoning. No h
... and-waving.                          ... and-waving.

review/scripts/model-review.py --- 4/16 --- Python
141     },                               132     },
142     "domain": {                      133     "domain": {
143         "label": "Gemini Pro (domai  134         "label": "Gemini Pro (domai
... n correctness)",                     ... n correctness)",
144         "model": "gemini-3.1-pro-pr  ... 
... eview",                              ... 
145         "provider": "google",        135         "profile": "deep_review",
146         "api_kwargs": {"timeout": 3  ... 
... 00},                                 ... 
147         "prompt": """\               136         "prompt": """\
148 <system>                             137 <system>
149 You are verifying DOMAIN-SPECIFIC C  138 You are verifying DOMAIN-SPECIFIC C
... LAIMS in this plan. Other reviewers  ... LAIMS in this plan. Other reviewers
...  handle architecture and formal log  ...  handle architecture and formal log
... ic.                                  ... ic.

review/scripts/model-review.py --- 5/16 --- Python
164     },                               153     },
165     "mechanical": {                  154     "mechanical": {
166         "label": "Gemini Flash (mec  155         "label": "Gemini Flash (mec
... hanical audit)",                     ... hanical audit)",
167         "model": "gemini-3-flash-pr  ... 
... eview",                              ... 
168         "provider": "google",        156         "profile": "fast_extract",
169         "api_kwargs": {"timeout": 1  ... 
... 20},                                 ... 
170         "prompt": """\               157         "prompt": """\
171 <system>                             158 <system>
172 Mechanical audit only. No analysis,  159 Mechanical audit only. No analysis,
...  no recommendations. Fast and preci  ...  no recommendations. Fast and preci
... se.                                  ... se.

review/scripts/model-review.py --- 6/16 --- Python
182     },                               169     },
183     "alternatives": {                170     "alternatives": {
184         "label": "Gemini Pro (alter  171         "label": "Gemini Pro (alter
... native approaches)",                 ... native approaches)",
185         "model": "gemini-3.1-pro-pr  ... 
... eview",                              ... 
186         "provider": "google",        172         "profile": "deep_review",
187         "api_kwargs": {"timeout": 3  ... 
... 00},                                 ... 
188         "prompt": """\               173         "prompt": """\
189 <system>                             174 <system>
190 You are generating ALTERNATIVE APPR  175 You are generating ALTERNATIVE APPR
... OACHES to the proposed plan. Other   ... OACHES to the proposed plan. Other 
... reviewers check correctness.         ... reviewers check correctness.

review/scripts/model-review.py --- 7/16 --- Python
204     },                               189     },
205     "simple": {                      190     "simple": {
206         "label": "Gemini Pro (combi  191         "label": "Gemini Pro (combi
... ned review)",                        ... ned review)",
207         "model": "gemini-3.1-pro-pr  ... 
... eview",                              ... 
208         "provider": "google",        192         "profile": "deep_review",
209         "api_kwargs": {"timeout": 3  ... 
... 00},                                 ... 
210         "prompt": """\               193         "prompt": """\
211 <system>                             194 <system>
212 Quick combined review. Be concrete.  195 Quick combined review. Be concrete.
...  It is {date}. Budget: ~1000 words.  ...  It is {date}. Budget: ~1000 words.

review/scripts/model-review.py --- 8/16 --- Python
227     "full": ["arch", "formal", "dom  210     "full": ["arch", "formal", "dom
... ain", "mechanical", "alternatives"]  ... ain", "mechanical", "alternatives"]
... ,                                    ... ,
228 }                                    211 }
229                                      212 
230 GEMINI_PRO_MODEL = "gemini-3.1-pro-  213 GEMINI_PRO_MODEL = dispatch_core.PR
... preview"                             ... OFILES["deep_review"].model
231 GEMINI_FLASH_MODEL = "gemini-3-flas  214 GEMINI_FLASH_MODEL = dispatch_core.
... h-preview"                           ... PROFILES["fast_extract"].model
232 GEMINI_RATE_LIMIT_MARKERS = (        215 GEMINI_RATE_LIMIT_MARKERS = (
233     "503",                           216     "503",
234     "rate limit",                    217     "rate limit",

review/scripts/model-review.py --- 9/16 --- Python
248                                      231 
249 def _add_additional_properties(sche  232 def _add_additional_properties(sche
... ma: dict) -> dict:                   ... ma: dict) -> dict:
250     """Recursively add additionalPr  233     """Recursively add additionalPr
... operties:false to all objects (Open  ... operties:false to all objects (Open
... AI strict mode)."""                  ... AI strict mode)."""
251     import copy                      ... 
252     s = copy.deepcopy(schema)        234     return dispatch_core._add_addit
...                                      ... ional_properties(schema)
253     def _walk(obj: dict) -> None:    ... 
254         if obj.get("type") == "obje  ... 
... ct":                                 ... 
255             obj["additionalProperti  ... 
... es"] = False                         ... 
256         for v in obj.values():       ... 
257             if isinstance(v, dict):  ... 
258                 _walk(v)             ... 
259             elif isinstance(v, list  ... 
... ):                                   ... 
260                 for item in v:       ... 
261                     if isinstance(i  ... 
... tem, dict):                          ... 
262                         _walk(item)  ... 
263     _walk(s)                         ... 
264     return s                         ... 
265                                      235 
266                                      236 
267 def _strip_additional_properties(sc  237 def _strip_additional_properties(sc
... hema: dict) -> dict:                 ... hema: dict) -> dict:
268     """Recursively remove additiona  238     """Recursively remove additiona
... lProperties from all objects (Googl  ... lProperties from all objects (Googl
... e API)."""                           ... e API)."""
269     import copy                      ... 
270     s = copy.deepcopy(schema)        239     return dispatch_core._strip_add
...                                      ... itional_properties(schema)
271     def _walk(obj: dict) -> None:    ... 
272         obj.pop("additionalProperti  ... 
... es", None)                           ... 
273         for v in obj.values():       ... 
274             if isinstance(v, dict):  ... 
275                 _walk(v)             ... 
276             elif isinstance(v, list  ... 
... ):                                   ... 
277                 for item in v:       ... 
278                     if isinstance(i  ... 
... tem, dict):                          ... 
279                         _walk(item)  ... 
280     _walk(s)                         ... 
281     return s                         ... 
282                                      240 
283                                      241 
284 def _call_llmx(                      242 def _call_llmx(

review/scripts/model-review.py --- 10/16 --- Python
290     schema: dict | None = None,      248     schema: dict | None = None,
291     **kwargs,                        249     **kwargs,
292 ) -> dict:                           250 ) -> dict:
293     """Call llmx Python API, write   251     """Call the shared dispatch hel
... output to file, return result dict.  ... per and adapt its result shape for 
... """                                  ... review logic."""
294     context = context_path.read_tex  ... 
... t()                                  ... 
295     full_prompt = context + "\n\n--  ... 
... -\n\n" + prompt                      ... 
296     # Reasoning models (GPT-5.x, Ge  ... 
... mini 3

... [diff truncated] ...
```

## Current File Excerpts

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
    ),
    "deep_review": DispatchProfile(
        name="deep_review",
        intent="Long-context structural critique and review",
        provider="google",
        model="gemini-3.1-pro-preview",
        timeout=300,
        reasoning_effort="high",
    ),
    "formal_review": DispatchProfile(
        name="formal_review",
        intent="Formal or quantitative GPT-backed review",
        provider="openai",
        model="gpt-5.4",
        timeout=600,
        reasoning_effort="high",
        max_tokens=32768,
    ),
    "gpt_general": DispatchProfile(
        name="gpt_general",
        intent="General-purpose GPT-backed dispatch",
        provider="openai",
        model="gpt-5.4",
        timeout=600,
        reasoning_effort="medium",
        max_tokens=16384,
    ),
    "search_grounded": DispatchProfile(
        name="search_grounded",
        intent="Search-backed answer synthesis",
        provider="google",
        model="gemini-3.1-pro-preview",
        timeout=300,
        search=True,
    ),
    "cheap_tick": DispatchProfile(
        name="cheap_tick",
        intent="Low-cost maintenance or cycle tick synthesis",
        provider="google",
        model="gemini-3-flash-preview",
        timeout=120,
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

    

... [truncated for review packet] ...

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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import shared.llm_dispatch as dispatch_core

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
You are pe

... [truncated for review packet] ...

for constitution discovery (default: cwd)")
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

### hooks/generate-overview.sh

```text
#!/usr/bin/env bash
# generate-overview.sh — Shared overview generator: repomix → shared dispatch → markdown
# Used by sessionend-overview-trigger.sh and manual invocation.
#
# Config: reads .claude/overview.conf from project root (or env vars).
# Prompts: reads from $OVERVIEW_PROMPT_DIR/<type>.md
#
# Usage:
#   generate-overview.sh --type source       # Single overview type
#   generate-overview.sh --auto              # All configured types in parallel
#   generate-overview.sh --dry-run --auto    # Log what would happen, don't generate

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Defaults (overridden by .claude/overview.conf or env) ---
OVERVIEW_TYPES="${OVERVIEW_TYPES:-source}"
OVERVIEW_PROFILE="${OVERVIEW_PROFILE:-}"
OVERVIEW_MODEL="${OVERVIEW_MODEL:-gemini-3-flash-preview}"
OVERVIEW_OUTPUT_DIR="${OVERVIEW_OUTPUT_DIR:-.claude/overviews}"
OVERVIEW_PROMPT_DIR="${OVERVIEW_PROMPT_DIR:-.claude/overview-prompts}"
OVERVIEW_EXCLUDE="${OVERVIEW_EXCLUDE:-}"

# --- Parse arguments ---
TYPE=""
AUTO=false
DRY_RUN=false
PROJECT_ROOT=""
COMMIT_HASH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)
      TYPE="$2"; shift 2 ;;
    --auto)
      AUTO=true; shift ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    --project-root)
      PROJECT_ROOT="$2"; shift 2 ;;
    --commit-hash)
      COMMIT_HASH="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: generate-overview.sh [--type TYPE|--auto] [--dry-run] [--project-root DIR] [--commit-hash SHA]"
      echo "  --type TYPE        Generate single overview (source, tooling, structure, etc.)"
      echo "  --auto             Generate all types from OVERVIEW_TYPES config"
      echo "  --dry-run          Log what would happen without generating"
      echo "  --project-root DIR Project root (default: git root or cwd)"
      echo "  --commit-hash SHA  Commit hash for marker (default: HEAD at execution time)"
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# --- Resolve project root ---
if [[ -z "$PROJECT_ROOT" ]]; then
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
fi
cd "$PROJECT_ROOT"

# --- Resolve commit hash (for marker writes) ---
if [[ -z "$COMMIT_HASH" ]]; then
  COMMIT_HASH=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
fi

# --- Load config ---
CONF_FILE="$PROJECT_ROOT/.claude/overview.conf"
if [[ -f "$CONF_FILE" ]]; then
  # Source as shell vars (simple key=value, no export needed)
  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$key" ]] && continue
    key=$(echo "$key" | xargs)  # trim whitespace
    value=$(echo "$value" | xargs | sed 's/^"//;s/"$//')  # trim + unquote
    export "$key=$value"
  done < "$CONF_FILE"
fi

# Re-read after config load (env vars may have been set)
OVERVIEW_TYPES="${OVERVIEW_TYPES:-source}"
OVERVIEW_PROFILE="${OVERVIEW_PROFILE:-}"
OVERVIEW_MODEL="${OVERVIEW_MODEL:-gemini-3-flash-preview}"
OVERVIEW_OUTPUT_DIR="${OVERVIEW_OUTPUT_DIR:-.claude/overviews}"
OVERVIEW_PROMPT_DIR="${OVERVIEW_PROMPT_DIR:-.claude/overview-prompts}"
OVERVIEW_EXCLUDE="${OVERVIEW_EXCLUDE:-}"

# --- Check dependencies ---
check_deps() {
  local missing=()
  command -v repomix &>/dev/null || missing+=("repomix")
  command -v uv &>/dev/null || missing+=("uv")
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Missing dependencies: ${missing[*]}" >&2
    exit 1
  fi
}

resolve_overview_profile() {
  if [[ -n "$OVERVIEW_PROFILE" ]]; then
    echo "$OVERVIEW_PROFILE"
    return 0
  fi

  case "$OVERVIEW_MODEL" in
    gemini-3-flash-preview)
      echo "fast_extract"
      ;;
    gemini-3.1-pro-preview)
      echo "deep_review"
      ;;
    gpt-5.4)
      echo "gpt_general"
      ;;
    *)
      echo "ERROR: No dispatch profile mapping for OVERVIEW_MODEL=$OVERVIEW_MODEL" >&2
      return 1
      ;;
  esac
}

profile_token_limit() {
  local profile="$1"
  case "$profile" in
    gpt_general|formal_revi

... [truncated for review packet] ...

okens=$((prompt_size / 4))

  echo "[$type] Generating (~${prompt_tokens} tokens, profile: $dispatch_profile)..."

  # Step 4: Check token estimate against model limits
  local token_limit
  token_limit=$(profile_token_limit "$dispatch_profile")
  if [[ $prompt_tokens -gt $token_limit ]]; then
    echo "[$type] ERROR: prompt (~${prompt_tokens} tokens) exceeds safe limit (${token_limit}) for $dispatch_profile. Tighten OVERVIEW_EXCLUDE or dirs." >&2
    rm -f "$temp_prompt"
    return 1
  fi

  # Step 5: Generate via shared dispatch (atomic write — temp file, mv on success)
  local dispatch_meta dispatch_error llm_output dispatch_exit resolved_model
  dispatch_meta=$(mktemp /tmp/overview-dispatch-meta-XXXXXX)
  dispatch_error=$(mktemp /tmp/overview-dispatch-error-XXXXXX)
  llm_output=$(mktemp "${output_dir}/.overview-tmp-${type}-XXXXXX")

  # Disable errexit to capture exit code (set -e would skip cleanup on failure)
  set +e
  uv run python3 "$SCRIPT_DIR/../scripts/llm-dispatch.py" \
    --profile "$dispatch_profile" \
    --context "$temp_prompt" \
    --prompt "Write the requested codebase overview in markdown." \
    --output "$llm_output" \
    --meta "$dispatch_meta" \
    --error-output "$dispatch_error" \
    >/dev/null
  dispatch_exit=$?
  set -e

  # Cleanup prompt (no longer needed)
  rm -f "$temp_prompt"

  # Check for failure: non-zero exit or empty output
  if [[ $dispatch_exit -ne 0 ]] || [[ ! -s "$llm_output" ]]; then
    echo "[$type] ERROR: dispatch failed (exit=$dispatch_exit)." >&2
    [[ -f "$dispatch_error" ]] && cat "$dispatch_error" >&2
    [[ -f "$dispatch_meta" ]] && cat "$dispatch_meta" >&2
    rm -f "$dispatch_error" "$dispatch_meta" "$llm_output"
    return 1
  fi
  resolved_model=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("resolved_model","unknown"))' "$dispatch_meta" 2>/dev/null || echo "unknown")
  rm -f "$dispatch_error"

  # Step 6: Prepend freshness metadata to temp output, then atomic mv
  local git_sha gen_ts meta_line
  git_sha=$(echo "$COMMIT_HASH" | head -c 7)
  gen_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  meta_line="<!-- Generated: ${gen_ts} | git: ${git_sha} | profile: ${dispatch_profile} | model: ${resolved_model} -->"

  local tmp_final
  tmp_final=$(mktemp "${output_dir}/.overview-final-${type}-XXXXXX")
  { echo "$meta_line"; echo ""; cat "$llm_output"; } > "$tmp_final"
  rm -f "$llm_output" "$dispatch_meta"

  # Atomic move — old overview preserved until this succeeds
  mv "$tmp_final" "$output_file"

  # Step 7: Write per-type success marker
  echo "$COMMIT_HASH" > "$PROJECT_ROOT/.claude/overview-marker-${type}"

  echo "[$type] Done → $output_file (marker: ${COMMIT_HASH:0:7})"
}

# --- Main ---
if ! $DRY_RUN; then
  check_deps
fi

if $AUTO; then
  # Generate types with capped concurrency (avoid Gemini CLI rate limits)
  # For cross-project refresh, prefer generate-overview-batch.sh (Batch API, 50% discount)
  MAX_CONCURRENT=2
  IFS=',' read -ra TYPES <<< "$OVERVIEW_TYPES"
  pids=()
  type_names=()
  running=0

  for t in "${TYPES[@]}"; do
    t=$(echo "$t" | xargs)
    # Skip types whose per-type marker already matches target commit
    marker_file="$PROJECT_ROOT/.claude/overview-marker-${t}"
    if [[ -f "$marker_file" ]] && [[ "$(cat "$marker_file" 2>/dev/null)" == "$COMMIT_HASH" ]]; then
      echo "[$t] Already current (marker matches ${COMMIT_HASH:0:7}), skipping"
      continue
    fi
    generate_one "$t" &
    pids+=($!)
    type_names+=("$t")
    ((running++))
    if [ "$running" -ge "$MAX_CONCURRENT" ]; then
      wait "${pids[-$MAX_CONCURRENT]}" 2>/dev/null || true
      ((running--))
    fi
  done

  # Wait for remaining
  failures=0
  for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}" 2>/dev/null; then
      echo "FAILED: ${type_names[$i]}" >&2
      ((failures++))
    fi
  done

  [[ $failures -gt 0 ]] && exit 1
  exit 0
fi

if [[ -n "$TYPE" ]]; then
  generate_one "$TYPE"
  exit 0
fi

echo "Error: specify --type TYPE or --auto" >&2
exit 1

```

### hooks/pretool-llmx-guard.sh

```text
#!/usr/bin/env bash
# PreToolUse:Bash — catch common llmx dispatch mistakes
# Advisory (exit 0) for warnings, BLOCK (exit 2) for Gemini 2.5 and invalid flags

if [ "$CLAUDE_TOOL_NAME" != "Bash" ]; then exit 0; fi

INPUT="$CLAUDE_TOOL_INPUT"
CMD=$(echo "$INPUT" | jq -r '.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Only check commands that invoke llmx
echo "$CMD" | grep -q 'llmx' || exit 0

WARNINGS=""

# --- SPIN-LOOP detection (per-session llmx call counter) ---
LLMX_COUNTER="/tmp/claude-llmx-count-${PPID:-0}"
LLMX_COUNT=0
[ -f "$LLMX_COUNTER" ] && LLMX_COUNT=$(cat "$LLMX_COUNTER" 2>/dev/null || echo 0)
LLMX_COUNT=$((LLMX_COUNT + 1))
echo "$LLMX_COUNT" > "$LLMX_COUNTER"

if [ "$LLMX_COUNT" -ge 6 ]; then
  echo "[llmx-guard] BLOCKED: $LLMX_COUNT llmx calls this session. This looks like a spin loop." >&2
  echo "  - Diagnose WHY previous calls failed (check stderr, exit code)" >&2
  echo "  - Don't retry the same command — try a different model or approach" >&2
  echo "  - If rate-limited, wait or use a different provider" >&2
  # Log trigger for ROI analysis
  ~/Projects/skills/hooks/hook-trigger-log.sh "llmx-spin-loop" "block" "$LLMX_COUNT calls" 2>/dev/null || true
  exit 2
fi

if [ "$LLMX_COUNT" -ge 4 ]; then
  WARNINGS="${WARNINGS}[llmx-guard] WARNING: $LLMX_COUNT llmx calls this session. Approaching spin-loop territory.\n"
  WARNINGS="${WARNINGS}  - After 2 failures: diagnose before retrying (check stderr/exit code)\n"
  WARNINGS="${WARNINGS}  - Use --fallback for automatic model fallback on rate limits\n"
  WARNINGS="${WARNINGS}  - Blocked at 6 calls.\n"
fi

# --- BLOCKING checks (exit 2) ---

# Gemini 2.5 forbidden — user mandate: always use gemini-3.1-pro
if echo "$CMD" | grep -qiE 'gemini.?2\.5'; then
  echo "[llmx-guard] BLOCKED: Gemini 2.5 is forbidden. Use gemini-3.1-pro-preview instead." >&2
  exit 2
fi

# Invalid/hallucinated flags — these don't exist in llmx
# Known valid long flags (from `llmx chat --help`):
# --model --provider --temperature --reasoning-effort --stream --no-stream
# --compare --providers --timeout --debug --json --list-providers --no-thinking
# --use-old --fast --search --system --file --schema --max-tokens --output --fallback
INVALID_FLAGS=""
for flag in $(echo "$CMD" | grep -oE -- '--[a-z][-a-z]*' | sort -u); do
  case "$flag" in
    --model|--timeout|--max-tokens|--reasoning-effort|--fallback) ;;
    --stream|--schema|--search|--output|--fast|--use-old|--no-thinking|--debug) ;;
    --provider|--providers|--no-stream|--mini|--help|--version) ;;
    --compare|--json|--temperature|--system|--file|--list-providers) ;;
    *) INVALID_FLAGS="${INVALID_FLAGS} ${flag}" ;;
  esac
done
if [ -n "$INVALID_FLAGS" ]; then
  echo "[llmx-guard] BLOCKED: Unknown llmx flags:${INVALID_FLAGS}. Check llmx-guide skill for valid flags." >&2
  exit 2
fi

# Invalid model names — catch common hallucinations
MODEL=$(echo "$CMD" | grep -oE '(-m|--model)\s+[a-zA-Z0-9._-]+' | head -1 | sed -E 's/^(-m|--model)[[:space:]]+//; s/^[[:space:]]+//; s/[[:space:]]+$//')
if [ -n "$MODEL" ]; then
  case "$MODEL" in
    gemini-3.1-pro-preview|gemini-3-flash-preview|gemini-3.1-flash-image-preview) ;;
    gpt-5.4|gpt-5.2|gpt-5.3-chat-latest|gpt-5-codex|o4-mini) ;;
    gemini-3.1-flash-lite-preview) ;;
    claude-sonnet-4-6|claude-opus-4-6|claude-haiku-4-5) ;;
    *gemini-3.1-pro*|*gemini-3-flash*) ;; # close enough variants
    *)
      # Catch common hallucinations
      if echo "$MODEL" | grep -qE '^gemini-3\.1-pro$'; then
        echo "[llmx-guard] BLOCKED: Model 'gemini-3.1-pro' needs '-preview' suffix. Use gemini-3.1-pro-preview." >&2
        exit 2
      elif echo "$MODEL" | grep -qE '^gemini-3-flash$|^gemini-flash-3'; then
        echo "[llmx-guard] BLOCKED: Model '$MODEL' is wrong. Use gemini-3-flash-preview." >&2
        exit 2
      elif echo "$MODEL" | grep -qE '^gpt-5\.3$'; then
        echo "[llmx-guard] BLOCKED: Model 'gpt-5.3' needs '-chat-latest' suffix. Use gpt-5.3-chat-latest." >&2
        exit 2
     

... [truncated for review packet] ...

ts/skills/scripts/llm-dispatch.py \\" >&2
      echo "    --profile fast_extract \\" >&2
      echo "    --context context.md \\" >&2
      echo "    --prompt 'Analyze this' \\" >&2
      echo "    --output /tmp/result.md" >&2
      ~/Projects/skills/hooks/hook-trigger-log.sh "llmx-chat-blocked" "block" "$(echo "$CMD" | head -c 200)" 2>/dev/null || true
      exit 2
    fi
    ;;
esac

# 0a. Gemini Pro without --stream — CLI transport hangs on thinking models + piped input, hits capacity limits
#    Flash/Lite on CLI is fine (non-thinking, better capacity) — no warning needed
if echo "$CMD" | grep -qiE 'gemini-3\.1-pro|gemini-3-pro' && ! echo "$CMD" | grep -qE -- '--stream'; then
  WARNINGS="${WARNINGS}[llmx-guard] Gemini Pro without --stream. CLI transport hangs on thinking models and hits capacity limits. Add --stream for API transport. (Flash on CLI is fine.)\n"
fi

# 0b. --fallback used — model should be the model, no silent switching
if echo "$CMD" | grep -qE -- '--fallback'; then
  WARNINGS="${WARNINGS}[llmx-guard] --fallback silently switches models on failure. Prefer --stream (API transport) over --fallback (model downgrade). Diagnose failures, don't mask them.\n"
fi

# 1. Shell redirect with llmx output
if echo "$CMD" | grep -qE 'llmx\s+(chat|research|image|svg|vision)?.*[^2]>\s*["\$\./~a-zA-Z]'; then
  WARNINGS="${WARNINGS}[llmx-guard] Shell redirect detected. Use --output/-o instead of > file — shell redirects buffer until process exit.\n"
fi

# 2. PYTHONUNBUFFERED cargo cult
if echo "$CMD" | grep -qE 'PYTHONUNBUFFERED.*llmx|llmx.*PYTHONUNBUFFERED'; then
  WARNINGS="${WARNINGS}[llmx-guard] PYTHONUNBUFFERED does nothing for llmx output capture. Use --output/-o flag instead.\n"
fi

# 3. stdbuf/script with llmx
if echo "$CMD" | grep -qE '(stdbuf|script\s+-q).*llmx'; then
  WARNINGS="${WARNINGS}[llmx-guard] stdbuf/script won't fix output buffering. Use --output/-o flag instead.\n"
fi

# 4. max_tokens with GPT-5.x reasoning models — warn about small values
if echo "$CMD" | grep -qE 'gpt-5\.[234]' && echo "$CMD" | grep -qE -- '--max-tokens\s+[0-9]{1,4}(\s|$)'; then
  WARNINGS="${WARNINGS}[llmx-guard] Small --max-tokens with GPT-5.x reasoning model. max_completion_tokens includes reasoning tokens — use 16384+ to avoid truncated output.\n"
fi

# 5. Old LiteLLM model prefixes (deprecated in v0.6.0)
if echo "$CMD" | grep -qE 'llmx.*(-m|--model)\s+(gemini/|openai/|xai/|moonshot/)'; then
  WARNINGS="${WARNINGS}[llmx-guard] LiteLLM-style model prefix detected. Prefixes are deprecated in v0.6.0 — use bare model names.\n"
fi

# 6. Stdin pipe + prompt arg (stdin silently dropped — use -f instead)
if echo "$CMD" | grep -qE '(\||cat\s).*llmx' && echo "$CMD" | grep -qE 'llmx\s+chat\s' && echo "$CMD" | grep -vqE '\s-f\s'; then
  # Only warn if there's a trailing prompt argument (not just piped input)
  if echo "$CMD" | grep -qE 'llmx\s+chat\s.*"'; then
    WARNINGS="${WARNINGS}[llmx-guard] Piping stdin + prompt argument — stdin is silently dropped. Use -f FILE instead of cat FILE | llmx. (Fixed in gemini-cli 0.32.1: -f works now.)\n"
  fi
fi

# 7. Background dispatch without -o (output lost)
if echo "$CMD" | grep -qE 'llmx.*&\s*$' && ! echo "$CMD" | grep -qE -- '--output|-o\s'; then
  WARNINGS="${WARNINGS}[llmx-guard] Background llmx (&) without --output/-o. Output will be lost. Add -o file.md.\n"
fi

# 8. Suppressing llmx stderr hides the real failure cause
if echo "$CMD" | grep -qE 'llmx.*2>\s*/dev/null|2>/dev/null.*llmx'; then
  WARNINGS="${WARNINGS}[llmx-guard] llmx stderr is redirected to /dev/null. This hides transport/quota diagnostics; capture stderr to a file instead.\n"
fi

# 9. Downstream shell consumers can mask llmx exit codes
if echo "$CMD" | grep -qE 'llmx.*\|\s*(head|tail|sed|awk)\b'; then
  WARNINGS="${WARNINGS}[llmx-guard] llmx output is piped into a shell consumer. Without 'set -o pipefail', the shell reports the consumer's exit code, not llmx's.\n"
fi

if [ -n "$WARNINGS" ]; then
  echo -e "$WARNINGS" >&2
fi
exit 0

```

### hooks/test_pretool_llmx_guard.py

```text
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "pretool-llmx-guard.sh"


class LlmxGuardTest(unittest.TestCase):
    def run_guard(self, command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT)],
            env={
                "CLAUDE_TOOL_NAME": "Bash",
                "CLAUDE_TOOL_INPUT": json.dumps({"command": command}),
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def test_blocks_default_llmx_chat_mode_without_chat_subcommand(self) -> None:
        proc = self.run_guard('llmx -m gemini-3.1-pro-preview "hello"')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("shared dispatch helper", proc.stderr)

    def test_allows_non_chat_subcommands(self) -> None:
        proc = self.run_guard('llmx image "robot mascot" -o /tmp/robot.png')
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()

```

### research-ops/scripts/run-cycle.sh

```text
#!/usr/bin/env bash
# Rate-limit-aware research cycle runner.
# If Claude is rate-limited (>=6 processes), runs through the shared Python
# dispatch helper instead of raw llmx CLI subprocess dispatch.
#
# Usage: run-cycle.sh [project_dir]
#   Or from Claude Code: ! ~/Projects/skills/research-cycle/scripts/run-cycle.sh

set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
CYCLE_FILE="$PROJECT_DIR/CYCLE.md"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

MAX_PROCS="${RATE_LIMIT_THRESHOLD:-6}"
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
echo "Claude processes: $CLAUDE_PROCS (threshold: $MAX_PROCS)"

if [ "$CLAUDE_PROCS" -ge "$MAX_PROCS" ]; then
    echo "Rate-limited mode: routing through shared LLM dispatch"

    # Gather state (same script the skill uses)
    STATE=$("$SKILL_DIR/scripts/gather-cycle-state.sh" "$PROJECT_DIR" 2>&1 | head -80)

    if echo "$STATE" | grep -q "NO STATE CHANGE"; then
        echo "No state change — noop."
        exit 0
    fi

    # Build prompt from CYCLE.md + state
    CYCLE_CONTENT=""
    if [ -f "$CYCLE_FILE" ]; then
        CYCLE_CONTENT=$(head -200 "$CYCLE_FILE")
    fi

    cycle_context=$(mktemp /tmp/cycle-dispatch-context-XXXXXX)
    cycle_output=$(mktemp /tmp/cycle-dispatch-output-XXXXXX)
    cycle_meta=$(mktemp /tmp/cycle-dispatch-meta-XXXXXX)
    cycle_error=$(mktemp /tmp/cycle-dispatch-error-XXXXXX)

    cat > "$cycle_context" << PROMPT_EOF
# Research Cycle Tick (rate-limited mode)

Project: $PROJECT_DIR
Project name: $(basename "$PROJECT_DIR")

## Current State
$STATE

## CYCLE.md (current)
$CYCLE_CONTENT

## Instructions
You are running one tick of the research cycle. Pick the highest-priority phase:
1. Recent execution without verification → verify
2. Approved items in queue → execute (skip — can't execute code via llmx)
3. Active plan not yet reviewed → review
4. Gaps without plan → plan
5. Discoveries without gap analysis → gap-analyze
6. Verification done without improve → improve
7. Nothing pending → discover

For discover: search for new developments relevant to this project.
For gap-analyze: analyze discoveries and write gaps.
For plan/review: analyze and write recommendations.

Output your findings as markdown that should be appended to CYCLE.md.
Start with "## [Phase]: [description]" and include a date.
Be concise — this will be appended to a file.
PROMPT_EOF

    set +e
    uv run python3 "$SKILL_DIR/../scripts/llm-dispatch.py" \
        --profile cheap_tick \
        --context "$cycle_context" \
        --prompt "Run one research cycle tick. Output markdown for CYCLE.md." \
        --output "$cycle_output" \
        --meta "$cycle_meta" \
        --error-output "$cycle_error" \
        >/dev/null
    dispatch_exit=$?
    set -e

    if [ "$dispatch_exit" -eq 0 ] && [ -s "$cycle_output" ]; then
        echo "" >> "$CYCLE_FILE"
        cat "$cycle_output" >> "$CYCLE_FILE"
        echo "---"
        echo "Appended to CYCLE.md via shared dispatch (rate-limited mode)"
        head -5 "$cycle_output"
    else
        echo "Dispatch failed — skipping this tick" >&2
        if [ -s "$cycle_error" ]; then
            cat "$cycle_error" >&2
        elif [ -s "$cycle_meta" ]; then
            cat "$cycle_meta" >&2
        fi
    fi

    rm -f "$cycle_context" "$cycle_output" "$cycle_meta" "$cycle_error"
else
    echo "Normal mode: running via Claude skill"
    echo "Use /research cycle in your Claude session instead."
    echo "(This script is for rate-limited fallback only)"
fi

```
