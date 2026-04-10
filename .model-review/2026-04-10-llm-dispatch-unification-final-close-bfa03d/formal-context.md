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

- `shared/__init__.py`
- `shared/llm_dispatch.py`
- `scripts/llm-dispatch.py`
- `scripts/test_llm_dispatch.py`
- `review/scripts/model-review.py`
- `review/scripts/test_model_review.py`
- `hooks/generate-overview.sh`
- `hooks/pretool-llmx-guard.sh`
- `hooks/test_pretool_llmx_guard.py`
- `research-ops/scripts/run-cycle.sh`
- `llmx-guide/SKILL.md`
- `research-ops/SKILL.md`
- `improve/SKILL.md`
- `observe/SKILL.md`
- `review/SKILL.md`
- `brainstorm/references/llmx-dispatch.md`

## Git Status

```text
M .claude/overview-marker-source
 M .claude/overviews/source-overview.md
 M _archive/architect/SKILL.md
 M brainstorm/SKILL.md
 M brainstorm/references/llmx-dispatch.md
 M hooks/generate-overview.sh
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
brainstorm/references/llmx-dispatch.md |  37 ++++----
 hooks/generate-overview.sh             |  90 +++++++++++++++-----
 hooks/pretool-llmx-guard.sh            |  41 ++++++---
 improve/SKILL.md                       |  30 ++++---
 llmx-guide/SKILL.md                    |  31 +++++--
 observe/SKILL.md                       |  50 ++++-------
 research-ops/SKILL.md                  |  26 +++---
 research-ops/scripts/run-cycle.sh      |  49 +++++++----
 review/SKILL.md                        |  10 ++-
 review/scripts/model-review.py         | 150 ++++++++++++---------------------
 review/scripts/test_model_review.py    |  19 +++--
 11 files changed, 304 insertions(+), 229 deletions(-)
```

## Unified Diff

```diff
brainstorm/references/llmx-dispatch.md --- 1/2 --- Text
  1 <!-- Reference file for brainstorm     1 <!-- Reference file for brainstorm 
  . skill. Loaded on demand. -->           . skill. Loaded on demand. -->
  2 # llmx Dispatch Templates              2 # llmx Dispatch Templates
  3                                        3 
  4 > **DISPATCH VIA PYTHON API, NOT CL    4 > **Automation path:** use `uv run 
  . I.** Use `from llmx.api import chat    . python3 ~/Projects/skills/scripts/l
  .  as llmx_chat` and call                . lm-dispatch.py` or the shared Pytho
  .                                        . n module in `shared/llm_dispatch.py
  .                                        . `.
  5 > `llmx_chat(prompt=..., provider=.    . 
  . .., model=..., timeout=...)`. Read     . 
  . context files with                     . 
  6 > `Path(...).read_text()` and write    . 
  .  outputs with `Path(...).write_text    . 
  . (response.content)`.                   . 
  7 > The CLI commands below are templa    5 > The CLI commands below are manual
  . te references for the prompt conten    .  prompt templates only. Do not past
  . t — adapt them to Python API calls.    . e them into agent automation unchan
  .                                        . ged.
  8 > Bootstrap: `sys.path.insert(0, gl    . 
  . ob.glob(str(Path.home() / ".local/s    . 
  . hare/uv/tools/llmx/lib/python*/site    . 
  . -packages"))[0])`                      . 
  9                                        6 
 10 All templates assume `$BRAINSTORM_D    7 All templates assume `$BRAINSTORM_D
 .. IR`, `$N_IDEAS`, `$CONSTITUTION`, a    . IR`, `$N_IDEAS`, `$CONSTITUTION`, a
 .. nd `$TOPIC` are set.                   . nd `$TOPIC` are set.
 11 Date injection: `$(date +%Y-%m-%d)`    8 Date injection: `$(date +%Y-%m-%d)`
 ..  in every system prompt.               .  in every system prompt.
 12                                        9 
 13 ## Initial Generation (Step 2)        10 ## Initial Generation (Step 2)
 14                                       11 
 15 **With llmx (and not `--no-llmx`):*   12 **With external dispatch (and not `
 .. * Dispatch to an external model for   .. --no-llmx`):** Dispatch to an exter
 ..  parallel volume while you also gen   .. nal model for parallel volume while
 .. erate your own set.                   ..  you also generate your own set.
 16                                       13 
 17 ```bash                               14 ```bash
 18 llmx chat -m gemini-3.1-pro-preview   15 cat > "$BRAINSTORM_DIR/external-gen
 ..  \                                    .. eration.prompt.md" <<'EOF'
 19   ${CONSTITUTION:+-f "$BRAINSTORM_D   .. 
 .. IR/context.md"} \                     .. 
 20   --max-tokens 65536 --timeout 300    .. 
 .. \                                     .. 
 21   -o "$BRAINSTORM_DIR/external-gene   .. 
 .. ration.md" "                          .. 
 22 <system>                              16 <system>
 23 Generate approaches to the design s   17 Generate approaches to the design s
 .. pace below. Maximize breadth — $N_I   .. pace below. Maximize breadth — $N_I
 .. DEAS genuinely different approaches   .. DEAS genuinely different approaches
 .. , not variations on a theme. No fea   .. , not variations on a theme. No fea
 .. sibility filtering yet. It is $(dat   .. sibility filtering yet. It is $(dat
 .. e +%Y-%m-%d).                         .. e +%Y-%m-%d).
 24 </system>                             18 </system>
 25                                       19 
 26 [Design space + constraints + user-   20 [Design space + constraints + user-
 .. provided seeds if any]                .. provided seeds if any]
 ..                                       21 
 ..                                       22 For each approach: one paragraph on
 ..                                       ..  the mechanism and why it differs f
 ..                                       .. rom the others.
 ..                                       23 EOF
 27                                       24 
 28 For each approach: one paragraph on   25 uv run python3 ~/Projects/skills/sc
 ..  the mechanism and why it differs f   .. ripts/llm-dispatch.py \
 .. rom the others."                      .. 
 ..                                       26   --profile deep_review \
 ..                                       27   --context "$BRAINSTORM_DIR/contex
 ..                                       .. t.md" \
 ..                                       28   --prompt-file "$BRAINSTORM_DIR/ex
 ..                                       .. ternal-generation.prompt.md" \
 ..                                       29   --output "$BRAINSTORM_DIR/externa
 ..                                       .. l-generation.md"
 29 ```                                   30 ```
 30                                       31 
 31 Simultaneously, generate your own `   32 Simultaneously, generate your own `
 .. $N_IDEAS` approaches. Write to `$BR   .. $N_IDEAS` approaches. Write to `$BR
 .. AINSTORM_DIR/claude-generation.md`.   .. AINSTORM_DIR/claude-generation.md`.

brainstorm/references/llmx-dispatch.md --- 2/2 --- Text
130     > "$BRAINSTORM_DIR/all-raw.md"   131     > "$BRAINSTORM_DIR/all-raw.md" 
... 2>/dev/null                          ... 2>/dev/null
131 ```                                  132 ```
132                                      133 
133 If llmx available, dispatch extract  134 If shared dispatch is available, se
... ion to a fast model:                 ... nd extraction to a fast profile:
134                                      135 
135 ```bash                              136 ```bash
136 llmx chat -m gemini-3-flash-preview  137 uv run python3 ~/Projects/skills/sc
...  --timeout 120 \                     ... ripts/llm-dispatch.py \
...                                      138   --profile fast_extract \
137   -f "$BRAINSTORM_DIR/all-raw.md" \  139   --context "$BRAINSTORM_DIR/all-ra
...                                      ... w.md" \
138   -o "$BRAINSTORM_DIR/extraction.md  140   --prompt "
... " "                                  ... 
139 <system>                             141 <system>
140 Extract every discrete idea, approa  142 Extract every discrete idea, approa
... ch, or insight as a numbered list.   ... ch, or insight as a numbered list. 
... One per line. Tag the source (initi  ... One per line. Tag the source (initi
... al/denial-r1/denial-r2/domain/const  ... al/denial-r1/denial-r2/domain/const
... raint). Do not evaluate — extract m  ... raint). Do not evaluate — extract m
... echanically.                         ... echanically.
141 </system>                            143 </system>
142                                      144 
143 Extract all discrete ideas from the  145 Extract all discrete ideas from the
...  brainstorm artifacts."              ...  brainstorm artifacts." \
...                                      146   --output "$BRAINSTORM_DIR/extract
...                                      ... ion.md"
144 ```                                  147 ```
145                                      148 
146 If no llmx, extract yourself.        149 If no shared dispatch is available,
...                                      ...  extract yourself.

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
138 175 
139 176   mkdir -p "$output_dir"
140 177 
141 178   local temp_prompt dispatch_profile
142 179   temp_prompt=$(mktemp /tmp/overview-prompt-$$-${type}-XXXXXX.txt)
... 180   dispatch_profile=$(resolve_overview_profile) || return 1
143 181 
144 182   # Step 1: Extract content with repomix (--stdout avoids clipboard races)
145 183   local include_pattern=""

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
... w-llmx-stderr-XXXXXX)                ... iew-dispatch-meta-XXXXXX.json)
...                                      233   dispatch_error=$(mktemp /tmp/over
...                                      ... view-dispatch-error-XXXXXX.json)
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

improve/SKILL.md --- 1/2 --- Text
179                                      179 
180 ### Step 3: Dispatch to Gemini       180 ### Step 3: Dispatch to Gemini
181                                      181 
182 Send transcripts + tool sequence an  182 Send transcripts + tool sequence an
... alysis to Gemini 3.1 Pro via `llmx.  ... alysis to Gemini 3.1 Pro via the sh
... api.chat()`:                         ... ared dispatch helper:
183                                      183 
184 ```python                            184 ```python
185 from llmx.api import chat as llmx_c  185 from pathlib import Path
... hat                                  ... 
...                                      186 import sys
186                                      187 
...                                      188 sys.path.insert(0, str(Path.home() 
...                                      ... / "Projects" / "skills"))
...                                      189 from shared.llm_dispatch import dis
...                                      ... patch
...                                      190 
187 transcripts = Path("$ARTIFACT_DIR/i  191 transcripts = Path("$ARTIFACT_DIR/i
... nput.md").read_text()                ... nput.md").read_text()
188 response = llmx_chat(                192 response = dispatch(
189     prompt=transcripts + "\n\nAnaly  193     profile="deep_review",
... ze Claude Code session transcripts   ... 
... for repeated workflows. "            ... 
...                                      194     prompt=(
...                                      195         "Analyze Claude Code sessio
...                                      ... n transcripts for repeated workflow
...                                      ... s. "
190     "Classify as SKILL candidate (m  196         "Classify as SKILL candidat
... ulti-step, judgment needed) or MCP   ... e (multi-step, judgment needed) or 
... TOOL candidate (deterministic, reus  ... MCP TOOL candidate (deterministic, 
... able). "                             ... reusable). "
191     "For each: pattern, frequency,   197         "For each: pattern, frequen
... current cost, trigger, parameters,   ... cy, current cost, trigger, paramete
... skeleton. "                          ... rs, skeleton. "
192     "Only patterns appearing 2+ tim  198         "Only patterns appearing 2+
... es across different sessions. Max 7  ...  times across different sessions. M
...  candidates. "                       ... ax 7 candidates. "
193     "Rank by frequency x complexity  199         "Rank by frequency x comple
...  saved.",                            ... xity saved."
194     provider="google",               200     ),
195     model="gemini-3.1-pro-preview",  201     context_text=transcripts,
196     timeout=300,                     202     output_path=Path("$ARTIFACT_DIR
...                                      ... /candidates.md"),
197 )                                    203 )
198 ```                                  204 ```
199                                      205 

improve/SKILL.md --- 2/2 --- Text
270 ```bash                              276 ```bash
271 CLAUDE_PROCS=$(pgrep -lf claude 2>/  277 CLAUDE_PROCS=$(pgrep -lf claude 2>/
... dev/null | wc -l | tr -d ' ')        ... dev/null | wc -l | tr -d ' ')
272 ```                                  278 ```
273 If >= 5: skip subagent dispatch (Ti  279 If >= 5: skip subagent dispatch (Ti
... er 2). Route LLM-heavy analysis thr  ... er 2). Route LLM-heavy analysis thr
... ough `llmx chat -m gemini-3-flash-p  ... ough `uv run python3 ~/Projects/ski
... review` (free).                      ... lls/scripts/llm-dispatch.py --profi
...                                      ... le cheap_tick ...`.
274                                      280 
275 ### Each Tick: Pick ONE Task by Pri  281 ### Each Tick: Pick ONE Task by Pri
... ority                                ... ority
276                                      282 

llmx-guide/SKILL.md --- 1/4 --- Text
  8                                        8 
  9 # llmx Quick Reference                 9 # llmx Quick Reference
 10                                       10 
 ..                                       11 Most agents should not call `llmx` 
 ..                                       .. directly for normal repo automation
 ..                                       .. . Use the shared wrapper first:
 ..                                       12 
 ..                                       13 ```bash
 ..                                       14 uv run python3 ~/Projects/skills/sc
 ..                                       .. ripts/llm-dispatch.py \
 ..                                       15   --profile fast_extract \
 ..                                       16   --context context.md \
 ..                                       17   --prompt "Analyze this" \
 ..                                       18   --output result.md
 ..                                       19 ```
 ..                                       20 
 ..                                       21 Use this skill when:
 ..                                       22 - debugging shared dispatch failure
 ..                                       .. s
 ..                                       23 - writing or reviewing low-level co
 ..                                       .. de that calls `llmx.api.chat()`
 ..                                       24 - doing manual terminal work where 
 ..                                       .. raw CLI transport matters
 ..                                       25 
 ..                                       26 Agent note: the repo hook blocks ra
 ..                                       .. w `llmx` chat-style Bash automation
 ..                                       .. . The CLI examples below are for ma
 ..                                       .. nual terminal debugging or maintain
 ..                                       .. er reference, not for normal agent 
 ..                                       .. execution through the Bash tool.
 ..                                       27 
 11 > Detail files in `references/`: [m   28 > Detail files in `references/`: [m
 .. odels.md](references/models.md) | [   .. odels.md](references/models.md) | [
 .. error-codes.md](references/error-co   .. error-codes.md](references/error-co
 .. des.md) | [transport-routing.md](re   .. des.md) | [transport-routing.md](re
 .. ferences/transport-routing.md) | [c   .. ferences/transport-routing.md) | [c
 .. odex-dispatch.md](references/codex-   .. odex-dispatch.md](references/codex-
 .. dispatch.md) | [subcommands.md](ref   .. dispatch.md) | [subcommands.md](ref
 .. erences/subcommands.md)               .. erences/subcommands.md)
 12                                       29 
 13 ## Before You Call llmx — Checklist   30 ## Before You Call llmx — Checklist
 14                                       31 
 15 1. **Model name correct?** Hyphens    32 1. **Model name correct?** Hyphens 
 .. not dots (`claude-sonnet-4-6` not `   .. not dots (`claude-sonnet-4-6` not `
 .. claude-sonnet-4.6`)                   .. claude-sonnet-4.6`)
 16 2. **Timeout set?** Reasoning model   33 2. **Timeout set?** Reasoning model
 .. s need `--timeout 600` or `--stream   .. s need `--timeout 600` or `--stream
 .. `. Max allowed: **900s**. GPT-5.4 x   .. `. Max allowed: **900s**. If dispat
 .. high can exceed this on domain-heav   .. ching from an agent shell, set the 
 .. y prompts.                            .. outer shell timeout above this (for
 ..                                       ..  Claude Code, use at least `1200000
 ..                                       .. ` ms).
 17 3. **Using `shell=True`?** Don't —    34 3. **Using `shell=True`?** Don't — 
 .. parentheses in prompts break it. Us   .. parentheses in prompts break it. Us
 .. e list args + `input=`                .. e list args + `input=`
 18 4. **Using `-o FILE`?** Never use `   35 4. **Using `-o FILE`?** Never use `
 .. > file` shell redirects — they buff   .. > file` shell redirects — they buff
 .. er until exit                         .. er until exit
 19 5. **No provider prefixes needed.**   36 5. **No provider prefixes needed.**
 ..  `gemini-3.1-pro-preview` not `gemi   ..  `gemini-3.1-pro-preview` not `gemi
 .. ni/gemini-3.1-pro-preview`.           .. ni/gemini-3.1-pro-preview`.
 20 6. **Know the transport triggers:**   37 6. **Know the transport triggers:**
 ..  `google` prefers `gemini` CLI (fre   ..  `google` prefers `gemini` CLI (fre
 .. e). Falls back to API for: `--schem   .. e). Gemini falls back to API for: `
 .. a`, `--search`, `--stream`, `--max-   .. --schema`, `--search`, `--stream`, 
 .. tokens`. GPT goes direct to API.      .. `--max-tokens`. Codex CLI also fall
 ..                                       .. s back for `--search` and `--stream
 ..                                       .. `, but can keep `--schema` via `cod
 ..                                       .. ex exec --output-schema`. GPT goes 
 ..                                       .. direct to API unless you explicitly
 ..                                       ..  force `-p codex-cli`.
 21 7. **Hangs in agent context?** Clau   38 7. **Hangs in agent context?** Clau
 .. de Code's Bash tool pipes stdin wit   .. de Code's Bash tool pipes stdin wit
 .. hout EOF. Fixed in current llmx (sk   .. hout EOF. Fixed in current llmx (sk
 .. ips stdin when prompt provided).      .. ips stdin when prompt provided).
 22 8. **Prompt is positional, context    39 8. **Prompt is positional, context 
 .. is `-f`.** `llmx "analyze this" -f    .. is `-f`.** `llmx "analyze this" -f 
 .. context.md` — prompt as first posit   .. context.md` — prompt as first posit
 .. ional arg, context files as `-f`. T   .. ional arg, context files as `-f`. T
 .. wo `-f` flags with no positional =    .. wo `-f` flags with no positional = 
 .. no prompt = model invents a task fr   .. no prompt = model invents a task fr
 .. om the context. (Evidence: 2026-04-   .. om the context. (Evidence: 2026-04-
 .. 05 — Gemini received two `-f` files   .. 05 — Gemini received two `-f` files
 .. , hallucinated a script implementat   .. , hallucinated a script implementat
 .. ion instead of analysis.)             .. ion instead of analysis.)
 23 9. **For critical reviews, use one    40 9. **For critical reviews, use one 
 .. combined context file.** Multi-file   .. combined context file.** Multi-file
 ..  `-f` has recurring failure modes w   ..  `-f` has recurring failure modes w
 .. ith Gemini/CLI transport, including   .. ith Gemini/CLI transport, including
 ..  silently dropping earlier files. P   ..  silently dropping earlier files. P
 .. re-concatenate first.                 .. re-concatenate first, but preserve 
 ..                                       .. file boundaries in the combined fil
 ..                                       .. e.
 24                                       41 
 25 ## When llmx Fails — Diagnose, Don'   42 ## When llmx Fails — Diagnose, Don'
 .. t Downgrade                           .. t Downgrade
 26                                       43 

llmx-guide/SKILL.md --- 2/4 --- Text
 56 If the task is high-stakes or revie   73 If the task is high-stakes or revie
 .. w-oriented, do this:                  .. w-oriented, do this:
 57                                       74 
 58 ```bash                               75 ```bash
 59 cat overview.md diff.md touched-fil   76 awk 'FNR==1{print "\n# File: " FILE
 .. es.md > combined-context.md           .. NAME "\n"}1' overview.md diff.md to
 ..                                       .. uched-files.md > combined-context.m
 ..                                       .. d
 60 llmx chat -m gemini-3.1-pro-preview   77 llmx chat -m gemini-3.1-pro-preview
 ..  -f combined-context.md --timeout 3   ..  -f combined-context.md --timeout 3
 .. 00 "Review this"                      .. 00 "Review this"
 61 ```                                   78 ```
 62                                       79 

llmx-guide/SKILL.md --- 3/4 --- Text
 72                                       89 
 73 ### 2. GPT-5.x Timeouts               90 ### 2. GPT-5.x Timeouts
 74                                       91 
 75 GPT-5.4 with reasoning burns time B   92 GPT-5.4 with reasoning burns time B
 .. EFORE producing output. Non-streami   .. EFORE producing output. Non-streami
 .. ng holds the connection idle during   .. ng holds the connection idle during
 ..  reasoning. Default timeout: 300s.    ..  reasoning. Default timeout: 300s. 
 .. Max: **900s** (hard cap). GPT-5.4 x   .. Max: **900s** (hard cap). GPT-5.4 x
 .. high on domain-heavy prompts can ex   .. high on domain-heavy prompts can ex
 .. ceed 900s — use ChatGPT Pro for tho   .. ceed 900s; for those, chunk the tas
 .. se.                                   .. k, stream, or switch to an async/ba
 ..                                       .. tch path if available. Do not punt 
 ..                                       .. operational work to a GUI tool.
 76                                       93 
 77 **`max_completion_tokens` includes    94 **`max_completion_tokens` includes 
 .. reasoning tokens.** If you set `--m   .. reasoning tokens.** If you set `--m
 .. ax-tokens 4096` on GPT-5.4 with rea   .. ax-tokens 4096` on GPT-5.4 with rea
 .. soning, the model may exhaust the b   .. soning, the model may exhaust the b
 .. udget on thinking. Use 16K+ for rea   .. udget on thinking. Use 16K+ for rea
 .. soning models.                        .. soning models.
 78                                       95 

llmx-guide/SKILL.md --- 4/4 --- Text
123 set -o pipefail                      140 set -o pipefail
124 llmx chat -m gpt-5.4 --debug -o /tm  141 llmx chat -m gpt-5.4 --debug -o /tm
... p/review.md "query" 2> /tmp/review.  ... p/review.md "query" 2> /tmp/review.
... err                                  ... err
125 echo $?                              142 echo $?
126 sed -n '1,80p' /tmp/review.err       143 tail -n 200 /tmp/review.err
127 sed -n '1,80p' /tmp/review.md        144 sed -n '1,80p' /tmp/review.md
128 ```                                  145 ```
129                                      146 
130 From Claude Code: set Bash tool `ti  147 From Claude Code: set Bash tool `ti
... meout: 660000` (11 min) — mus

... [diff truncated] ...
```

## Current File Excerpts

### shared/__init__.py

```text
"""Shared helpers for the skills repo."""


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

### scripts/llm-dispatch.py

```text
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.llm_dispatch import DispatchOverrides, STATUS_EXIT_CODES, dispatch


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified llmx Python dispatch wrapper for skills automation")
    parser.add_argument("--profile", required=True, help="Named dispatch profile")
    parser.add_argument("--output", required=True, type=Path, help="Output markdown/text artifact path")
    parser.add_argument("--context", type=Path, help="Single assembled context file")
    parser.add_argument("--prompt", help="Inline prompt text")
    parser.add_argument("--prompt-file", type=Path, help="Read prompt text from file")
    parser.add_argument("--meta", type=Path, help="Optional meta.json path")
    parser.add_argument("--error-output", type=Path, help="Optional error.json path")
    parser.add_argument("--parsed-output", type=Path, help="Optional parsed JSON output path")
    parser.add_argument("--schema-file", type=Path, help="Optional JSON schema file")
    parser.add_argument("--timeout", type=int, help="Allowed override: timeout seconds")
    parser.add_argument("--reasoning-effort", help="Allowed override: reasoning effort")
    parser.add_argument("--max-tokens", type=int, help="Allowed override: max tokens")
    parser.add_argument("--search", action="store_true", help="Allowed override: enable search")
    parser.add_argument("--system", help="Optional system prompt")
    args = parser.parse_args()

    prompt = args.prompt
    if args.prompt_file:
        prompt = args.prompt_file.read_text()
    if not prompt:
        parser.error("one of --prompt or --prompt-file is required")

    schema = None
    if args.schema_file:
        schema = json.loads(args.schema_file.read_text())

    overrides = DispatchOverrides(
        timeout=args.timeout,
        reasoning_effort=args.reasoning_effort,
        max_tokens=args.max_tokens,
        search=True if args.search else None,
    )
    override_payload = overrides.as_dict()
    if not override_payload:
        overrides = None

    result = dispatch(
        profile=args.profile,
        prompt=prompt,
        context_path=args.context,
        output_path=args.output,
        meta_path=args.meta,
        error_path=args.error_output,
        parsed_path=args.parsed_output,
        schema=schema,
        overrides=overrides,
        system=args.system,
    )

    if result.status == "ok":
        print(result.output_path)
    else:
        print(f"{result.status}: {result.error_message or 'dispatch failed'}", file=sys.stderr)
    return STATUS_EXIT_CODES[result.status]


if __name__ == "__main__":
    raise SystemExit(main())

```

### scripts/test_llm_dispatch.py

```text
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from shared import llm_dispatch


class DispatchCoreTest(unittest.TestCase):
    def test_dispatch_success_writes_output_and_meta(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            context_path = root / "context.md"
            output_path = root / "out.md"
            context_path.write_text("context")

            def mock_chat(**kwargs):
                self.assertEqual(kwargs["provider"], "google")
                self.assertEqual(kwargs["model"], "gemini-3-flash-preview")
                response = MagicMock()
                response.content = "hello"
                response.latency = 0.25
                return response

            with patch.object(llm_dispatch, "_LLMX_CHAT", mock_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ):
                result = llm_dispatch.dispatch(
                    profile="fast_extract",
                    prompt="Analyze this",
                    context_path=context_path,
                    output_path=output_path,
                )

            self.assertEqual(result.status, "ok")
            self.assertEqual(output_path.read_text(), "hello")
            meta = json.loads((root / "out.meta.json").read_text())
            self.assertEqual(meta["status"], "ok")
            self.assertEqual(meta["resolved_model"], "gemini-3-flash-preview")

    def test_dispatch_classifies_rate_limit_and_clears_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_path = root / "out.md"
            output_path.write_text("stale")

            def exploding_chat(**kwargs):
                raise RuntimeError("429 resource_exhausted")

            with patch.object(llm_dispatch, "_LLMX_CHAT", exploding_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ):
                result = llm_dispatch.dispatch(
                    profile="deep_review",
                    prompt="Review",
                    context_text="ctx",
                    output_path=output_path,
                )

            self.assertEqual(result.status, "rate_limit")
            self.assertFalse(output_path.exists())
            error_payload = json.loads((root / "out.error.json").read_text())
            self.assertEqual(error_payload["error_type"], "rate_limit")

    def test_dispatch_writes_parsed_json_when_schema_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_path = root / "out.md"
            schema = {
                "type": "object",
                "properties": {"findings": {"type": "array"}},
                "required": ["findings"],
            }

            def mock_chat(**kwargs):
                self.assertIn("response_format", kwargs)
                response = MagicMock()
                response.content = '{"findings": []}'
                response.latency = 0.1
                return response

            with patch.object(llm_dispatch, "_LLMX_CHAT", mock_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ):
                result = llm_dispatch.dispatch(
                    profile="gpt_general",
                    prompt="Extract",
                    context_text="ctx",
                    output_path=output_path,
                    schema=schema,
                )

            self.assertEqual(result.status, "ok")
            parsed = json.loads((root / "out.parsed.json").read_text())
            self.assertEqual(parsed["findings"], [])

    def test_dispatch_marks_parse_error_but_preserves_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_path = root / "out.md"
            schema = {
                "type": "object",
                "properties": {"findings": {"type": "array"}},
                "required": ["findings"],
            }

            def mock_chat(**kwargs):
                response = MagicMock()
                response.content = "not json"
                response.latency = 0.1
                return response

            with patch.object(llm_dispatch, "_LLMX_CHAT", mock_chat), patch.object(
                llm_dispatch, "_LLMX_VERSION", "test"
            ):
                result = llm_dispatch.dispatch(
                    profile="fast_extract",
                    prompt="Extract",
                    context_text="ctx",
                    output_path=output_path,
                    schema=schema,
                )

            self.assertEqual(result.status, "parse_error")
            self.assertTrue(output_path.exists())
            self.assertFalse((root / "out.parsed.json").exists())
            meta = json.loads((root / "out.meta.json").read_text())
            self.assertEqual(meta["error_type"], "parse_error")


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
            

... [truncated for review packet] ...

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

rompt_size / 4))

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
  dispatch_meta=$(mktemp /tmp/overview-dispatch-meta-XXXXXX.json)
  dispatch_error=$(mktemp /tmp/overview-dispatch-error-XXXXXX.json)
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

    cycle_context=$(mktemp /tmp/cycle-dispatch-context-XXXXXX.md)
    cycle_output=$(mktemp /tmp/cycle-dispatch-output-XXXXXX.md)
    cycle_meta=$(mktemp /tmp/cycle-dispatch-meta-XXXXXX.json)
    cycle_error=$(mktemp /tmp/cycle-dispatch-error-XXXXXX.json)

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

### llmx-guide/SKILL.md

```text
---
name: llmx-guide
description: Critical gotchas when calling llmx from Python or Bash. Non-obvious bugs and incompatibilities. Use when writing code that calls llmx, debugging llmx failures, or choosing llmx model/provider options.
user-invocable: true
argument-hint: '[model name or issue description]'
effort: medium
---

# llmx Quick Reference

Most agents should not call `llmx` directly for normal repo automation. Use the shared wrapper first:

```bash
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile fast_extract \
  --context context.md \
  --prompt "Analyze this" \
  --output result.md
```

Use this skill when:
- debugging shared dispatch failures
- writing or reviewing low-level code that calls `llmx.api.chat()`
- doing manual terminal work where raw CLI transport matters

Agent note: the repo hook blocks raw `llmx` chat-style Bash automation. The CLI examples below are for manual terminal debugging or maintainer reference, not for normal agent execution through the Bash tool.

> Detail files in `references/`: [models.md](references/models.md) | [error-codes.md](references/error-codes.md) | [transport-routing.md](references/transport-routing.md) | [codex-dispatch.md](references/codex-dispatch.md) | [subcommands.md](references/subcommands.md)

## Before You Call llmx — Checklist

1. **Model name correct?** Hyphens not dots (`claude-sonnet-4-6` not `claude-sonnet-4.6`)
2. **Timeout set?** Reasoning models need `--timeout 600` or `--stream`. Max allowed: **900s**. If dispatching from an agent shell, set the outer shell timeout above this (for Claude Code, use at least `1200000` ms).
3. **Using `shell=True`?** Don't — parentheses in prompts break it. Use list args + `input=`
4. **Using `-o FILE`?** Never use `> file` shell redirects — they buffer until exit
5. **No provider prefixes needed.** `gemini-3.1-pro-preview` not `gemini/gemini-3.1-pro-preview`.
6. **Know the transport triggers:** `google` prefers `gemini` CLI (free). Gemini falls back to API for: `--schema`, `--search`, `--stream`, `--max-tokens`. Codex CLI also falls back for `--search` and `--stream`, but can keep `--schema` via `codex exec --output-schema`. GPT goes direct to API unless you explicitly force `-p codex-cli`.
7. **Hangs in agent context?** Claude Code's Bash tool pipes stdin without EOF. Fixed in current llmx (skips stdin when prompt provided).
8. **Prompt is positional, context is `-f`.** `llmx "analyze this" -f context.md` — prompt as first positional arg, context files as `-f`. Two `-f` flags with no positional = no prompt = model invents a task from the context. (Evidence: 2026-04-05 — Gemini received two `-f` files, hallucinated a script implementation instead of analysis.)
9. **For critical reviews, use one combined context file.** Multi-file `-f` has recurring failure modes with Gemini/CLI transport, including silently dropping earlier files. Pre-concatenate first, but preserve file boundaries in the combined file.

## When llmx Fails — Diagnose, Don't Downgrade

**Never swap to a weaker model as a "fix."** The problem is the dispatch, not the model.

1. Check exit code: 3=rate-limit, 4=timeout, 5=model-error, 6=billing-exhausted (permanent, don't retry)
2. Check stderr JSON diagnostics
3. Check for transport switch / truncation warnings
4. Re-run with `--debug` on a small prompt
5. Common fixes: increase `--timeout`, add `--stream`, reduce context, check API key
6. **When transport matters, probe it.** Run one tiny `--debug` smoke test before assuming CLI vs API routing from docs or memory.

See [error-codes.md](references/error-codes.md) for full exit code table and Python patterns.

## The Five Footguns

### 1. Gemini CLI Transport — Free Tier

No `--stream` needed for Gemini. Without it, llmx routes through CLI (free tier). Add `--stream` only if CLI hits rate limits (forces paid API fallback).

```bash
# FREE — routes through Gemini CLI:
llmx chat -m gemini-3.1-pro-preview -f context.md --timeout 300 "Review this"

... [truncated for review packet] ...

adversarial review.

### 2. GPT-5.x Timeouts

GPT-5.4 with reasoning burns time BEFORE producing output. Non-streaming holds the connection idle during reasoning. Default timeout: 300s. Max: **900s** (hard cap). GPT-5.4 xhigh on domain-heavy prompts can exceed 900s; for those, chunk the task, stream, or switch to an async/batch path if available. Do not punt operational work to a GUI tool.

**`max_completion_tokens` includes reasoning tokens.** If you set `--max-tokens 4096` on GPT-5.4 with reasoning, the model may exhaust the budget on thinking. Use 16K+ for reasoning models.

### 3. Output Capture — Use `-o FILE`, Never `> file`

```bash
# CORRECT — llmx writes the output file itself:
llmx -m gpt-5.4 -f context.md --timeout 600 -o output.md "query"

# BROKEN — 0 bytes until exit:
llmx -m gpt-5.4 "query" > output.md
```

`-o` does not imply `--stream`. Current llmx preserves the requested transport and writes the returned result itself when needed. If the file is still 0 bytes, llmx emits `[llmx:WARN]` to stderr.

For GPT specifically:

- default `llmx -m gpt-5.4` routes to the OpenAI API in current llmx
- `-o` preserves that transport; it does not force a transport switch
- if you explicitly use `-p codex-cli`, diagnose any failure from stderr and output size, not shell exit alone

If you need to verify the actual route, run:

```bash
llmx chat -p codex-cli -m gpt-5.4 --debug -o /tmp/probe.txt "Reply with exactly OK."
```

Then inspect the debug line for `transport`.

### 3.5. Shell Pipelines Can Hide llmx Failures

These are bad diagnostic patterns:

```bash
llmx chat -m gpt-5.4 "query" 2>/dev/null | head -200
llmx chat -m gpt-5.4 "query" | sed -n '1,80p'
```

Why:

- `2>/dev/null` discards llmx's real diagnostics
- without `set -o pipefail`, the shell returns the last consumer's exit code (`head`, `sed`), not llmx's
- an empty llmx response can look like success if the downstream command exits 0

Safer pattern:

```bash
set -o pipefail
llmx chat -m gpt-5.4 --debug -o /tmp/review.md "query" 2> /tmp/review.err
echo $?
tail -n 200 /tmp/review.err
sed -n '1,80p' /tmp/review.md
```

From Claude Code: set Bash tool `timeout: 1200000` (20 min) — it must exceed llmx's `--timeout`.

### 4. shell=True + Parentheses

```python
# BREAKS if prompt has ():
subprocess.run(f'echo {repr(prompt)} | llmx ...', shell=True)

# CORRECT — always use list args:
subprocess.run(['llmx', '--provider', 'google'], input=prompt, capture_output=True, text=True)
```

### 5. Model Name 404 Traps

- `gemini-3-flash` -- missing `-preview`
- `gemini-flash-3` -- wrong order
- `gpt-5.3` -- needs `-chat-latest` suffix
- `claude-sonnet-4.6` -- dots, needs hyphens

See [models.md](references/models.md) for full model table, token limits, and reasoning effort values.

## Transport Routing Summary

| Provider | Default transport | Forces API fallback |
|----------|------------------|---------------------|
| `google` | Gemini CLI (free) | `--schema`, `--search`, `--stream`, `--max-tokens` |
| `openai` | OpenAI API | explicit `-p codex-cli` if you want Codex CLI instead |
| `claude` | Claude CLI | v0.6.0+, non-nested contexts only |

Both CLIs ignore explicit `--reasoning-effort` — they use their own defaults. See [transport-routing.md](references/transport-routing.md) for CLI vs API decision table, context budget, piping patterns.

## Codex `-o` Gotcha (Parallel Dispatch)

`-o FILE` captures the agent's **last text message only**. If the agent spends all turns on tool calls with no final text response, `-o` writes 0 bytes. Prompt **must** include: `"End with a COMPLETE markdown report as your final message."` Without this, ~50% produce empty output.

See [codex-dispatch.md](references/codex-dispatch.md) for full parallel dispatch pattern, Brave contention, Perplexity quota.

## Subcommands

`llmx research`, `llmx image`, `llmx vision`, `llmx svg`. Flags: `--fast` (Flash+low), `--use-old`, `--no-thinking`. See [subcommands.md](references/subcommands.md).

$ARGUMENTS

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
  --context /tmp/cycle-phase-prompt.md 

... [truncated for review packet] ...

rn, then exhaust turns filling it in. Failed 3/4 sessions. Use `-o FILE` instead — captures final text message automatically.

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


(Omitted 4 additional touched files from excerpts.)
