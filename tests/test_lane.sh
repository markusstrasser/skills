#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
LANE="$ROOT/bin/lane"
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/lane-test.XXXXXX")
mkdir -p "$TEST_TMP/lanes"
LANE_HOME=$(cd "$TEST_TMP/lanes" && pwd -P)
export LANE_HOME
unset LANE_CODEX_MODEL LANE_CODEX_EFFORT LANE_CODEX_ADD_DIRS LANE_CODEX_NETWORK
unset LANE_CLAUDE_MODEL LANE_CLAUDE_EFFORT
REPO="$TEST_TMP/repo"
BRIEF="$TEST_TMP/brief.md"
FAKE_BIN="$TEST_TMP/bin"
LANE_CAPTURE="$TEST_TMP/capture"
export LANE_CAPTURE
UNRELATED_PID=""

cleanup() {
  local name
  for name in first hang inline codexargs codexoverride codexuvcache claudeargs claudeoverride ocargs ocquota failure rvcache rvown rvnone; do
    if [ -f "$LANE_HOME/$name.json" ]; then
      "$LANE" stop "$name" >/dev/null 2>&1 || true
    fi
  done
  if [ -n "$UNRELATED_PID" ]; then
    kill "$UNRELATED_PID" >/dev/null 2>&1 || true
  fi
  chmod -R u+rwX "$TEST_TMP" 2>/dev/null || true
  rm -rf "$TEST_TMP"
}
trap cleanup EXIT INT TERM

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_eq() {
  local expected="$1"
  local actual="$2"
  local label="$3"
  [ "$actual" = "$expected" ] || fail "$label: expected '$expected', got '$actual'"
}

assert_file() {
  [ -f "$1" ] || fail "missing file: $1"
}

assert_no_file() {
  [ ! -e "$1" ] || fail "unexpected file: $1"
}

wait_for_file() {
  local path="$1"
  local attempts=0
  while [ ! -f "$path" ] && [ "$attempts" -lt 100 ]; do
    sleep 0.1
    attempts=$((attempts + 1))
  done
  assert_file "$path"
}

wait_for_absent() {
  local path="$1"
  local attempts=0
  while [ -e "$path" ] && [ "$attempts" -lt 100 ]; do
    sleep 0.1
    attempts=$((attempts + 1))
  done
  assert_no_file "$path"
}

json_value() {
  python3 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]])' "$1" "$2"
}

worker_setting() {
  python3 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["worker_settings"][sys.argv[2]])' "$1" "$2"
}

set_started_epoch() {
  python3 -c 'import json, sys; path = sys.argv[1]; data = json.load(open(path, encoding="utf-8")); data["started_epoch"] = int(sys.argv[2]); open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2, sort_keys=True) + "\n")' "$1" "$2"
}

clear_started_epoch() {
  python3 -c 'import json, sys; path = sys.argv[1]; data = json.load(open(path, encoding="utf-8")); data["started_epoch"] = ""; open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2, sort_keys=True) + "\n")' "$1"
}

state_for() {
  local name="$1"
  shift
  "$LANE" ls "$@" | awk -v wanted="$name" '$1 == wanted { print $2 }'
}

dirty_for() {
  local name="$1"
  "$LANE" ls | awk -v wanted="$name" '$1 == wanted { print $5 }'
}

review_for() {
  local name="$1"
  "$LANE" ls | awk -v wanted="$name" '$1 == wanted { print $6 }'
}

arg_after() {
  local flag="$1"
  local input="$2"
  awk -v wanted="$flag" '$0 == wanted { getline; print; exit }' "$input"
}

mkdir -p "$REPO"
git -C "$REPO" init -q
git -C "$REPO" config user.email lane-test@example.invalid
git -C "$REPO" config user.name "Lane Test"
printf '%s\n' base >"$REPO/tracked.txt"
git -C "$REPO" add tracked.txt
git -C "$REPO" commit -qm "test base"
printf '%s\n' "Do the fake task." >"$BRIEF"
REPO_REAL=$(cd "$REPO" && pwd -P)
BRIEF_REAL=$(cd "$(dirname "$BRIEF")" && pwd -P)/$(basename "$BRIEF")
mkdir -p "$FAKE_BIN" "$LANE_CAPTURE"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'printf "%s\n" "$@" > "$LANE_CAPTURE/codex.args"' \
  'pwd -P > "$LANE_CAPTURE/codex.cwd"' \
  'sleep 0.5' \
  'exit "${CODEX_FAKE_RC:-0}"' >"$FAKE_BIN/codex"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [ "${ANTHROPIC_API_KEY+x}" = x ]; then exit 9; fi' \
  'printf "%s\n" "$@" > "$LANE_CAPTURE/claude.args"' \
  'pwd -P > "$LANE_CAPTURE/claude.cwd"' \
  'sleep 0.5' >"$FAKE_BIN/claude"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'printf "%s\n" "Thu Aug 27 18:00:00 2026"' >"$FAKE_BIN/ps"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'capture="$LANE_CAPTURE/${LLMX_CAPTURE_NAME:-llmx}.args"' \
  'printf "%s\n" "$@" > "$capture"' \
  'out=""' \
  'while [ "$#" -gt 0 ]; do' \
  '  if [ "$1" = "-o" ]; then out="$2"; shift 2; else shift; fi' \
  'done' \
  'attempts=0' \
  'while [ -n "${LLMX_FAKE_WAIT_FILE:-}" ] && [ ! -f "$LLMX_FAKE_WAIT_FILE" ] && [ "$attempts" -lt 100 ]; do' \
  '  sleep 0.1' \
  '  attempts=$((attempts + 1))' \
  'done' \
  'if [ -n "${LLMX_FAKE_WAIT_FILE:-}" ] && [ ! -f "$LLMX_FAKE_WAIT_FILE" ]; then exit 8; fi' \
  'sleep "${LLMX_FAKE_SLEEP:-0}"' \
  'printf "%s\n" "fake review body" > "$out"' \
  'printf "%s\n" "fake llmx stdout"' \
  'exit "${LLMX_FAKE_RC:-0}"' >"$FAKE_BIN/llmx"
# The opencode worker runs under `env -i`, so the fake finds the capture dir beside its own bin dir, and flag files
# there pick its behaviour: a transport error once, a step cut off without an error event once, a provider failure
# once, or an exhausted balance.
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'capture="$(cd "$(dirname "$0")/.." && pwd -P)/capture"' \
  'n=$(find "$capture" -name "opencode.args.*" | wc -l | tr -d " ")' \
  'printf "%s\n" "$@" > "$capture/opencode.args.$n"' \
  'pwd -P > "$capture/opencode.cwd"' \
  'env > "$capture/opencode.env"' \
  'if [ -f "$capture/opencode-transport-once" ]; then' \
  '  rm "$capture/opencode-transport-once"' \
  '  printf "%s\n" "{\"type\":\"step_start\",\"sessionID\":\"ses_fake\"}" "{\"type\":\"error\",\"sessionID\":\"ses_fake\",\"error\":{\"type\":\"provider.transport\",\"message\":\"The socket connection was closed\"}}"' \
  '  exit 1' \
  'fi' \
  'if [ -f "$capture/opencode-interrupt-once" ]; then' \
  '  rm "$capture/opencode-interrupt-once"' \
  '  printf "%s\n" "{\"type\":\"step_start\",\"sessionID\":\"ses_fake\"}"' \
  '  exit 1' \
  'fi' \
  'if [ -f "$capture/opencode-fail-once" ]; then' \
  '  rm "$capture/opencode-fail-once"' \
  '  printf "%s\n" "{\"type\":\"error\",\"sessionID\":\"ses_fake\",\"error\":{\"type\":\"provider.http\",\"message\":\"500 Internal Server Error\"}}"' \
  '  exit 1' \
  'fi' \
  'if [ -f "$capture/opencode-quota" ]; then' \
  '  printf "%s\n" "{\"type\":\"error\",\"sessionID\":\"ses_fake\",\"error\":{\"type\":\"provider.http\",\"message\":\"402 Insufficient Balance\"}}"' \
  '  exit 0' \
  'fi' \
  'printf "%s\n" "{\"type\":\"step_finish\",\"sessionID\":\"ses_fake\",\"part\":{\"cost\":0.01,\"tokens\":{\"input\":100,\"output\":20,\"reasoning\":7,\"cache\":{\"read\":50,\"write\":0}}}}"' \
  >"$FAKE_BIN/opencode"
chmod +x "$FAKE_BIN/codex" "$FAKE_BIN/claude" "$FAKE_BIN/ps" "$FAKE_BIN/llmx" "$FAKE_BIN/opencode"
export PATH="$FAKE_BIN:$PATH"

echo "test: codex and claude worker commands match the dispatch contract"
CODEX_PROMPT="Do the task in $BRIEF_REAL.
Git metadata is read-only in this sandbox: edit files and run checks, but do not merge, stage or commit. The parent does that. The sandbox also denies ps and sysctl, so /usr/bin/time -l exits 1 after a successful command: measure time and memory from Python (time.perf_counter, resource.getrusage). End by listing every path you changed."
"$LANE" run codexargs --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/codexargs.done"
expected_codex=$(printf '%s\n' \
  exec \
  -m \
  gpt-6-astra \
  -s \
  workspace-write \
  --add-dir \
  "$HOME/.cache/uv" \
  --skip-git-repo-check \
  "$CODEX_PROMPT")
assert_eq "$expected_codex" "$(<"$LANE_CAPTURE/codex.args")" "codex arguments"
assert_eq "$REPO_REAL" "$(<"$LANE_CAPTURE/codex.cwd")" "codex cwd"
override_output=$(LANE_CODEX_MODEL=gpt-6.1-sol LANE_CODEX_EFFORT=high LANE_CODEX_ADD_DIRS="$TEST_TMP/slots:$TEST_TMP/extra root:" LANE_CODEX_NETWORK=1 "$LANE" run codexoverride --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree)
wait_for_file "$LANE_HOME/codexoverride.done"
expected_override=$(printf '%s\n' \
  exec \
  -m \
  gpt-6.1-sol \
  -c \
  'model_reasoning_effort="high"' \
  --add-dir \
  "$TEST_TMP/slots" \
  --add-dir \
  "$TEST_TMP/extra root" \
  -c \
  'sandbox_workspace_write.network_access=true' \
  -s \
  workspace-write \
  --add-dir \
  "$HOME/.cache/uv" \
  --skip-git-repo-check \
  "$CODEX_PROMPT")
assert_eq "$expected_override" "$(<"$LANE_CAPTURE/codex.args")" "codex model and effort env override"

echo "test: codex adds the target of a symlinked project uv cache as a writable root"
mkdir -p "$TEST_TMP/shared-uv"
ln -s "$TEST_TMP/shared-uv" "$REPO/.uv-cache"
SHARED_UV_REAL=$(cd "$TEST_TMP/shared-uv" && pwd -P)
uvcache_output=$("$LANE" run codexuvcache --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree)
wait_for_file "$LANE_HOME/codexuvcache.done"
rm "$REPO/.uv-cache"
expected_uvcache=$(printf '%s\n' \
  exec \
  -m \
  gpt-6-astra \
  --add-dir \
  "$SHARED_UV_REAL" \
  -s \
  workspace-write \
  --add-dir \
  "$HOME/.cache/uv" \
  --skip-git-repo-check \
  "$CODEX_PROMPT")
assert_eq "$expected_uvcache" "$(<"$LANE_CAPTURE/codex.args")" "codex uv-cache writable root"
grep -Fq "add_dirs=$SHARED_UV_REAL network=" <<<"$uvcache_output" || fail "settings line omitted the uv-cache root"

echo "test: codex adds the genomics cpu-slot directory as a writable root"
mkdir -p "$REPO/scripts"
: > "$REPO/scripts/cpu_slot.py"
slot_output=$(GENOMICS_CPU_SLOT_DIR="$TEST_TMP/cpu-slots" "$LANE" run codexcpuslot --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree)
wait_for_file "$LANE_HOME/codexcpuslot.done"
rm "$REPO/scripts/cpu_slot.py"
SLOT_REAL=$(cd "$TEST_TMP/cpu-slots" && pwd -P)
expected_slot=$(printf '%s\n' \
  exec \
  -m \
  gpt-6-astra \
  --add-dir \
  "$SLOT_REAL" \
  -s \
  workspace-write \
  --add-dir \
  "$HOME/.cache/uv" \
  --skip-git-repo-check \
  "$CODEX_PROMPT")
assert_eq "$expected_slot" "$(<"$LANE_CAPTURE/codex.args")" "codex cpu-slot writable root"
grep -Fq "add_dirs=$SLOT_REAL network=" <<<"$slot_output" || fail "settings line omitted the cpu-slot root"

echo "test: codex resume retains settings without caller exports"
resume_output=$("$LANE" resume codexoverride --no-note)
wait_for_file "$LANE_HOME/codexoverride.done"
assert_eq "$expected_override" "$(<"$LANE_CAPTURE/codex.args")" "resumed codex settings"
settings_line="lane: settings codex_model=gpt-6.1-sol codex_effort=high add_dirs=$TEST_TMP/slots:$TEST_TMP/extra root network=1"
grep -Fxq "$settings_line" <<<"$override_output" || fail "run omitted effective codex settings"
grep -Fxq "$settings_line" <<<"$resume_output" || fail "resume omitted effective codex settings"
assert_eq "gpt-6.1-sol" "$(worker_setting "$LANE_HOME/codexoverride.json" codex_model)" "recorded codex model"
assert_eq "high" "$(worker_setting "$LANE_HOME/codexoverride.json" codex_effort)" "recorded codex effort"
assert_eq "$TEST_TMP/slots:$TEST_TMP/extra root" "$(worker_setting "$LANE_HOME/codexoverride.json" codex_add_dirs)" "recorded writable roots"
assert_eq "1" "$(worker_setting "$LANE_HOME/codexoverride.json" codex_network)" "recorded network"
assert_eq "gpt-6-astra" "$(worker_setting "$LANE_HOME/codexargs.json" codex_model)" "recorded default codex model"
assert_eq "" "$(worker_setting "$LANE_HOME/codexargs.json" codex_effort)" "recorded config effort"
assert_eq "0" "$(worker_setting "$LANE_HOME/codexargs.json" codex_network)" "recorded default network"

echo "test: resume effort override wins and becomes the recorded setting"
LANE_CODEX_EFFORT=xhigh "$LANE" resume codexoverride --no-note >/dev/null
wait_for_file "$LANE_HOME/codexoverride.done"
assert_eq "gpt-6.1-sol" "$(arg_after -m "$LANE_CAPTURE/codex.args")" "override retained model"
assert_eq 'model_reasoning_effort="xhigh"' "$(arg_after -c "$LANE_CAPTURE/codex.args")" "resumed effort override"
"$LANE" resume codexoverride --no-note >/dev/null
wait_for_file "$LANE_HOME/codexoverride.done"
assert_eq 'model_reasoning_effort="xhigh"' "$(arg_after -c "$LANE_CAPTURE/codex.args")" "second resume retained effort override"

echo "test: exported empty settings clear recorded overrides"
LANE_CODEX_MODEL= LANE_CODEX_EFFORT= LANE_CODEX_ADD_DIRS= LANE_CODEX_NETWORK=0 "$LANE" resume codexoverride --no-note >/dev/null
wait_for_file "$LANE_HOME/codexoverride.done"
assert_eq "$expected_codex" "$(<"$LANE_CAPTURE/codex.args")" "empty exports restore default codex arguments"

echo "test: legacy resume warns and uses caller environment"
python3 -c 'import json, sys; path = sys.argv[1]; data = json.load(open(path, encoding="utf-8")); del data["worker_settings"]; open(path, "w", encoding="utf-8").write(json.dumps(data) + "\n")' "$LANE_HOME/codexoverride.json"
legacy_output=$(LANE_CODEX_MODEL=gpt-6.1-sol LANE_CODEX_EFFORT=high LANE_CODEX_ADD_DIRS="$TEST_TMP/slots:$TEST_TMP/extra root" LANE_CODEX_NETWORK=1 "$LANE" resume codexoverride --no-note 2>&1)
wait_for_file "$LANE_HOME/codexoverride.done"
grep -Fq 'original worker settings are unknown; using caller environment' <<<"$legacy_output" || fail "legacy resume omitted settings warning"
assert_eq "$expected_override" "$(<"$LANE_CAPTURE/codex.args")" "legacy codex environment fallback"
for key in name repo worktree brief pid started_at started_epoch worker; do
  grep -q "\"$key\"" "$LANE_HOME/codexargs.json" || fail "metadata omitted $key"
done

OTHER_REPO="$TEST_TMP/other-repo"
mkdir -p "$OTHER_REPO"
git -C "$OTHER_REPO" init -q
if "$LANE" run codexargs --repo "$OTHER_REPO" --brief "$BRIEF" --worker fake --no-worktree >/dev/null 2>&1; then
  fail "run reused a lane name for a different repository"
fi

export ANTHROPIC_API_KEY="must-be-removed"
"$LANE" run claudeargs --repo "$REPO" --brief "$BRIEF" --worker claude --no-worktree >/dev/null
wait_for_file "$LANE_HOME/claudeargs.done"
unset ANTHROPIC_API_KEY
expected_claude=$(printf '%s\n' -p --model opus --output-format stream-json --verbose "Do the fake task.")
assert_eq "$expected_claude" "$(<"$LANE_CAPTURE/claude.args")" "claude arguments"
assert_eq "$REPO_REAL" "$(<"$LANE_CAPTURE/claude.cwd")" "claude cwd"
assert_eq "opus" "$(worker_setting "$LANE_HOME/claudeargs.json" claude_model)" "recorded default claude model"
assert_eq "" "$(worker_setting "$LANE_HOME/claudeargs.json" claude_effort)" "recorded default claude effort"

echo "test: claude resume retains model and effort without caller exports"
claude_output=$(LANE_CLAUDE_MODEL=sonnet LANE_CLAUDE_EFFORT=high "$LANE" run claudeoverride --repo "$REPO" --brief "$BRIEF" --worker claude --no-worktree)
wait_for_file "$LANE_HOME/claudeoverride.done"
expected_claude_override=$(printf '%s\n' -p --model sonnet --effort high --output-format stream-json --verbose "Do the fake task.")
assert_eq "$expected_claude_override" "$(<"$LANE_CAPTURE/claude.args")" "initial claude overrides"
claude_resume_output=$("$LANE" resume claudeoverride --no-note)
wait_for_file "$LANE_HOME/claudeoverride.done"
assert_eq "$expected_claude_override" "$(<"$LANE_CAPTURE/claude.args")" "resumed claude settings"
grep -Fxq 'lane: settings claude_model=sonnet claude_effort=high' <<<"$claude_output" || fail "run omitted effective claude settings"
grep -Fxq 'lane: settings claude_model=sonnet claude_effort=high' <<<"$claude_resume_output" || fail "resume omitted effective claude settings"
assert_eq "sonnet" "$(worker_setting "$LANE_HOME/claudeoverride.json" claude_model)" "recorded claude model"
assert_eq "high" "$(worker_setting "$LANE_HOME/claudeoverride.json" claude_effort)" "recorded claude effort"
LANE_CLAUDE_EFFORT=low "$LANE" resume claudeoverride --no-note >/dev/null
wait_for_file "$LANE_HOME/claudeoverride.done"
assert_eq "sonnet" "$(arg_after --model "$LANE_CAPTURE/claude.args")" "claude override retained model"
assert_eq "low" "$(arg_after --effort "$LANE_CAPTURE/claude.args")" "claude effort override"
LANE_CLAUDE_MODEL= LANE_CLAUDE_EFFORT= "$LANE" resume claudeoverride --no-note >/dev/null
wait_for_file "$LANE_HOME/claudeoverride.done"
assert_eq "$expected_claude" "$(<"$LANE_CAPTURE/claude.args")" "empty exports restore default claude arguments"

echo "test: opencode worker scrubs the env, writes its guard, resumes a transport error and logs usage"
export DEEPSEEK_API_KEY_METERED="must-not-leak" LANE_OPENCODE_RETRY_SLEEP=0 LANE_OPENCODE_PROVIDER_HOST=""
touch "$LANE_CAPTURE/opencode-transport-once"
"$LANE" run ocargs --repo "$REPO" --brief "$BRIEF" --worker opencode >/dev/null
wait_for_file "$LANE_HOME/ocargs.done"
unset DEEPSEEK_API_KEY_METERED
OC_WORKTREE="$REPO_REAL/.claude/worktrees/codex-ocargs"
assert_eq "EXIT=0" "$(<"$LANE_HOME/ocargs.done")" "opencode marker after one transport resume"
assert_eq "$OC_WORKTREE" "$(<"$LANE_CAPTURE/opencode.cwd")" "opencode cwd"
expected_oc=$(printf '%s\n' run --standalone --auto --format json --thinking -m deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017 --title ocargs)
assert_eq "$expected_oc" "$(head -10 "$LANE_CAPTURE/opencode.args.0")" "opencode arguments"
sed -n 11p "$LANE_CAPTURE/opencode.args.0" | grep -Fxq "Do the fake task." || fail "opencode prompt lacks the brief"
grep -Fq "do not stage, commit, merge, stash or switch branches" "$LANE_CAPTURE/opencode.args.0" || fail "opencode prompt lacks the git contract"
assert_eq "ses_fake" "$(arg_after --session "$LANE_CAPTURE/opencode.args.1")" "transport resume continues the session"
grep -Fq "ended on a transport error or a dropped connection" "$LANE_CAPTURE/opencode.args.1" ||
  fail "transport resume lacks the resume prompt"
if grep -Fq "must-not-leak" "$LANE_CAPTURE/opencode.env"; then fail "opencode saw a caller secret"; fi
grep -Fxq "TMPDIR=/tmp/lane-opencode/ocargs/" "$LANE_CAPTURE/opencode.env" || fail "opencode TMPDIR is not per lane"
[ ! -e /tmp/lane-opencode/ocargs ] || fail "opencode TMPDIR survived the run"
oc_guard="$OC_WORKTREE/.opencode/opencode.json"
assert_file "$oc_guard"
python3 - "$oc_guard" "$REPO_REAL" <<'PY' || fail "opencode guard lacks a required rule"
import json
import sys

rules = json.load(open(sys.argv[1]))["permissions"]
required = [
    {"action": "external_directory", "resource": sys.argv[2] + "/**", "effect": "deny"},
    {"action": "shell", "resource": "*git commit*", "effect": "deny"},
    {"action": "shell", "resource": f"*{sys.argv[2]}/tracked.txt*", "effect": "deny"},
    {"action": "edit", "resource": ".opencode/**", "effect": "deny"},
    {"action": "question", "resource": "*", "effect": "deny"},
]
sys.exit(0 if all(rule in rules for rule in required) else 1)
PY
assert_eq "" "$(git -C "$OC_WORKTREE" status --porcelain)" "opencode guard is excluded from git status"
grep -Fxq "lane-opencode: usage steps=1 input=100 output=20 reasoning=7 cache_read=50 cache_write=0 cost_list=0.0100" \
  "$LANE_HOME/ocargs.log" || fail "opencode usage line missing"
assert_eq "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017" "$(worker_setting "$LANE_HOME/ocargs.json" opencode_model)" "recorded opencode model"

echo "test: an exhausted opencode balance exits 86 without a retry"
touch "$LANE_CAPTURE/opencode-quota"
"$LANE" run ocquota --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocquota.done"
rm "$LANE_CAPTURE/opencode-quota"
unset LANE_OPENCODE_RETRY_SLEEP LANE_OPENCODE_PROVIDER_HOST
assert_eq "EXIT=86" "$(<"$LANE_HOME/ocquota.done")" "quota marker"
grep -Fq "do not retry" "$LANE_HOME/ocquota.log" || fail "quota stop message missing"
[ "$(find "$LANE_CAPTURE" -name 'opencode.args.*' | wc -l | tr -d ' ')" = 3 ] || fail "quota run retried"

echo "test: an opencode step cut off without an error event resumes its session, and lane resume continues it"
export LANE_OPENCODE_RETRY_SLEEP=0 LANE_OPENCODE_PROVIDER_HOST=""
rm -f "$LANE_CAPTURE"/opencode.args.*
touch "$LANE_CAPTURE/opencode-interrupt-once"
"$LANE" run ocint --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocint.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/ocint.done")" "opencode marker after a cut-off step"
assert_eq "ses_fake" "$(arg_after --session "$LANE_CAPTURE/opencode.args.1")" "cut-off step continues the session"
touch "$LANE_CAPTURE/opencode-fail-once"
"$LANE" run ocres --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocres.done"
assert_eq "EXIT=1" "$(<"$LANE_HOME/ocres.done")" "provider failure is not retried"
assert_eq "ses_fake" "$(<"$LANE_HOME/ocres.opencode-session")" "recorded opencode session"
[ ! -e "$LANE_CAPTURE/opencode.args.3" ] || fail "provider failure was retried"
"$LANE" resume ocres --no-note >/dev/null
wait_for_file "$LANE_HOME/ocres.done"
unset LANE_OPENCODE_RETRY_SLEEP LANE_OPENCODE_PROVIDER_HOST
assert_eq "EXIT=0" "$(<"$LANE_HOME/ocres.done")" "resumed opencode lane"
assert_eq "ses_fake" "$(arg_after --session "$LANE_CAPTURE/opencode.args.3")" "lane resume continues the session"
grep -Fq "This continues your session" "$LANE_CAPTURE/opencode.args.3" || fail "lane resume lacks the continuation prompt"
grep -Fq "Do the fake task." "$LANE_CAPTURE/opencode.args.3" || fail "lane resume lacks the brief"

echo "test: worker failures still produce an exit marker"
CODEX_FAKE_RC=7 "$LANE" run failure --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/failure.done"
assert_eq "EXIT=7" "$(<"$LANE_HOME/failure.done")" "failure marker"
assert_eq "DONE:7" "$(state_for failure)" "failed worker state"

echo "test: a reader that closes early cannot abort a resume half-done"
# Before the fix, SIGPIPE killed resume after it archived the log and before it removed the old marker or launched.
"$LANE" resume failure --no-note | head -1 >/dev/null
wait_for_file "$LANE_HOME/failure.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/failure.done")" "resume relaunched despite a closed reader"

echo "test: run reports RUNNING and creates its isolated worktree"
run_output=$(LANE_FAKE_HOLD="$TEST_TMP/release-first" "$LANE" run first --repo "$REPO" --brief "$BRIEF" --worker fake)
grep -q '^watch: while ' <<<"$run_output" || fail "run did not print a watch loop"
assert_eq "RUNNING" "$(state_for first)" "initial state"
[ -d "$REPO/.claude/worktrees/codex-first" ] || fail "worktree was not created"
assert_eq "codex/first" "$(git -C "$REPO/.claude/worktrees/codex-first" branch --show-current)" "worktree branch"
printf '%s\n' scratch >"$REPO/.claude/worktrees/codex-first/scratch.txt"
assert_eq "1" "$(dirty_for first)" "worktree dirty count"
touch "$TEST_TMP/release-first"

echo "test: completion marker and DONE state"
wait_for_file "$LANE_HOME/first.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/first.done")" "completion marker"
assert_eq "DONE:0" "$(state_for first)" "completed state"
assert_eq "-" "$(review_for first)" "initial review state"

echo "test: positive control proves git diff HEAD omits untracked files"
FIRST_WORKTREE="$REPO_REAL/.claude/worktrees/codex-first"
printf '%s\n' reviewed >>"$FIRST_WORKTREE/tracked.txt"
printf '%s\n' review-untracked-sentinel >"$FIRST_WORKTREE/review-new.txt"
printf '\0binary\n' >"$FIRST_WORKTREE/review-binary.dat"
dd if=/dev/zero of="$FIRST_WORKTREE/review-oversized.dat" bs=1024 count=1025 >/dev/null 2>&1
ln -s missing-target "$FIRST_WORKTREE/review-broken-link"
mkfifo "$FIRST_WORKTREE/review-fifo"
positive_patch=$(git -C "$FIRST_WORKTREE" diff --no-ext-diff HEAD)
grep -Fq 'reviewed' <<<"$positive_patch" || fail "positive control omitted the tracked edit"
if grep -Fq 'review-untracked-sentinel' <<<"$positive_patch"; then
  fail "positive control unexpectedly included the untracked file"
fi
echo "POSITIVE-CONTROL-FAIL: git diff HEAD omitted untracked review-new.txt"

echo "test: review patch includes tracked and untracked hunks despite --no-index exit 1"
mkdir -p "$FIRST_WORKTREE/docs/audit/deep"
printf '%s\n' old >"$FIRST_WORKTREE/docs/audit/old-report.md"
touch -t 202001010000 "$FIRST_WORKTREE/docs/audit/old-report.md"
printf '%s\n' report >"$FIRST_WORKTREE/docs/audit/deep/current-report.md"
printf '%s\n' 'Check path handling and background completion.' >"$TEST_TMP/review-axes.txt"
review_out="$TEST_TMP/custom-review.md"
review_stdout=$(LLMX_CAPTURE_NAME=foreground "$LANE" review first --model test-model --effort medium --focus "$TEST_TMP/review-axes.txt" --out "$review_out")
assert_file "$LANE_HOME/first.patch"
grep -Fq 'diff --git a/tracked.txt b/tracked.txt' "$LANE_HOME/first.patch" || fail "review patch omitted tracked diff"
grep -Fq 'diff --git a/review-new.txt b/review-new.txt' "$LANE_HOME/first.patch" || fail "review patch omitted untracked diff"
grep -Fq 'review-untracked-sentinel' "$LANE_HOME/first.patch" || fail "review patch omitted untracked contents"
grep -Fq '# skipped binary untracked file: review-binary.dat' "$LANE_HOME/first.patch" || fail "review patch omitted binary skip note"
grep -Fq '# skipped oversized untracked file (>1 MB): review-oversized.dat' "$LANE_HOME/first.patch" || fail "review patch omitted oversized skip note"
grep -Fq '# skipped: review-broken-link (broken symlink)' "$LANE_HOME/first.patch" || fail "review patch omitted broken-symlink skip note"
grep -Fq '# skipped: review-fifo (fifo)' "$LANE_HOME/first.patch" || fail "review patch omitted fifo skip note"
grep -Fq '# report attached separately; omitted untracked hunk: docs/audit/deep/current-report.md' "$LANE_HOME/first.patch" || fail "review patch omitted separate-report note"
if grep -Fq 'diff --git a/review-binary.dat' "$LANE_HOME/first.patch"; then fail "review patch included binary hunk"; fi
if grep -Fq 'diff --git a/review-oversized.dat' "$LANE_HOME/first.patch"; then fail "review patch included oversized hunk"; fi
if grep -Fq 'diff --git a/review-broken-link' "$LANE_HOME/first.patch"; then fail "review patch included broken-symlink hunk"; fi
if grep -Fq 'diff --git a/review-fifo' "$LANE_HOME/first.patch"; then fail "review patch included fifo hunk"; fi
if grep -Fq 'diff --git a/docs/audit/deep/current-report.md' "$LANE_HOME/first.patch"; then fail "review patch duplicated the attached report"; fi
git -C "$FIRST_WORKTREE" diff --cached --quiet || fail "review mutated the lane index"
grep -Eq '^lane: patch: .+ \([0-9]+ lines\)$' <<<"$review_stdout" || fail "review did not print patch path and line count"

echo "test: review passes llmx files, output, model, effort, and focus prompt without stdout capture"
foreground_args="$LANE_CAPTURE/foreground.args"
assert_file "$foreground_args"
assert_eq "test-model" "$(arg_after -m "$foreground_args")" "review model"
assert_eq "medium" "$(arg_after -e "$foreground_args")" "review effort"
assert_eq "900" "$(arg_after --timeout "$foreground_args")" "review timeout"
assert_eq "3" "$(grep -c '^-f$' "$foreground_args")" "review file arguments (patch, report, brief)"
grep -Fxq "$LANE_HOME/first.patch" "$foreground_args" || fail "llmx arguments omitted patch"
grep -Fxq "$FIRST_WORKTREE/docs/audit/deep/current-report.md" "$foreground_args" || fail "llmx arguments omitted newest report"
if grep -Fxq "$FIRST_WORKTREE/docs/audit/old-report.md" "$foreground_args"; then fail "llmx received a stale report"; fi
assert_eq "$review_out" "$(arg_after -o "$foreground_args")" "review output argument"
grep -Fq 'Check path handling and background completion.' "$foreground_args" || fail "review prompt omitted focus axes"
grep -Fq 'fake llmx stdout' <<<"$review_stdout" || fail "foreground review redirected llmx stdout"
assert_eq "fake review body" "$(<"$review_out")" "llmx -o review body"
assert_eq "DONE:0" "$(review_for first)" "foreground review state"
assert_no_file "$LANE_HOME/first.review.lock"

echo "test: forged review pid identity is not RUNNING and does not block review"
rm -f "$LANE_HOME/first.review.done"
printf '%s\n%s\n' "$$" 1 >"$LANE_HOME/first.review.pid"
assert_eq "-" "$(review_for first)" "forged review identity"
LLMX_CAPTURE_NAME=forged-review "$LANE" review first --out "$TEST_TMP/forged-review.md" >/dev/null
assert_eq "DONE:0" "$(review_for first)" "review after forged identity"

echo "test: background review reports RUNNING then writes its done marker"
review_release="$TEST_TMP/review-release"
bg_output=$(LLMX_CAPTURE_NAME=background LLMX_FAKE_WAIT_FILE="$review_release" "$LANE" review first --bg)
grep -Eq '^lane: review pid=[0-9]+$' <<<"$bg_output" || fail "background review omitted pid"
grep -Fq "$LANE_HOME/first.review.md" <<<"$bg_output" || fail "background review omitted output path"
grep -Fq "$LANE_HOME/first.review.done" <<<"$bg_output" || fail "background review omitted marker path"
assert_eq "RUNNING" "$(review_for first)" "running review state"
assert_file "$LANE_HOME/first.review.pid"
case "$(sed -n '2p' "$LANE_HOME/first.review.pid")" in "" | *[!0-9]*) fail "background review pid omitted started_epoch" ;; esac
[ -d "$LANE_HOME/first.review.lock" ] || fail "background review omitted atomic lock"
if overlap_error=$("$LANE" review first 2>&1); then
  fail "review allowed overlapping dispatches for one lane"
fi
grep -Fq 'review already running' <<<"$overlap_error" || fail "overlap guard did not report the review lock"
printf '%s\n' release >"$review_release"
wait_for_file "$LANE_HOME/first.review.done"
wait_for_absent "$LANE_HOME/first.review.lock"
assert_eq "EXIT=0" "$(<"$LANE_HOME/first.review.done")" "background review marker"
assert_eq "DONE:0" "$(review_for first)" "completed review state"
background_args="$LANE_CAPTURE/background.args"
assert_eq "gpt-6-astra" "$(arg_after -m "$background_args")" "default review model"
assert_eq "high" "$(arg_after -e "$background_args")" "default review effort"
assert_eq "$LANE_HOME/first.review.md" "$(arg_after -o "$background_args")" "default review output"

echo "test: background review preserves a nonzero llmx exit code"
LLMX_CAPTURE_NAME=background-failure LLMX_FAKE_RC=9 "$LANE" review first --bg >/dev/null
wait_for_file "$LANE_HOME/first.review.done"
wait_for_absent "$LANE_HOME/first.review.lock"
assert_eq "EXIT=9" "$(<"$LANE_HOME/first.review.done")" "failed background review marker"
assert_eq "DONE:9" "$(review_for first)" "failed background review state"
grep -Fq "fake llmx stdout" "$LANE_HOME/first.review.log" || fail "background review discarded llmx output (exit 3 left no diagnosis)"

echo "test: zero-minute stall threshold and exact stop archive"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [ "$1" = "-j" ]; then exit 1; fi' \
  'if [ "$1" = "-d" ]; then printf "%s\n" 1787846400; exit 0; fi' \
  'exec /bin/date "$@"' >"$FAKE_BIN/date"
chmod +x "$FAKE_BIN/date"
"$LANE" run hang --repo "$REPO" --brief "$BRIEF" --worker fake-hang >/dev/null
hang_metadata="$LANE_HOME/hang.json"
hang_pid=$(json_value "$hang_metadata" pid)
hang_started_epoch=$(json_value "$hang_metadata" started_epoch)
case "$hang_started_epoch" in "" | *[!0-9]*) fail "worker metadata omitted started_epoch" ;; esac
kill -0 -- "-$hang_pid" 2>/dev/null || fail "real worker process group is not alive"
set_started_epoch "$hang_metadata" "$((hang_started_epoch + 1))"
assert_eq "DEAD" "$(state_for hang)" "forged worker identity"
kill -0 -- "-$hang_pid" 2>/dev/null || fail "forged identity check signalled the real worker"
set_started_epoch "$hang_metadata" "$hang_started_epoch"
assert_eq "RUNNING" "$(state_for hang)" "real worker identity"
clear_started_epoch "$hang_metadata"
legacy_state=$(state_for hang 2>"$TEST_TMP/legacy-liveness.warn")
assert_eq "RUNNING" "$legacy_state" "legacy worker liveness fallback"
grep -Fq 'falling back to pid liveness' "$TEST_TMP/legacy-liveness.warn" || fail "legacy liveness fallback omitted warning"
set_started_epoch "$hang_metadata" "$hang_started_epoch"
sleep 2
assert_eq "STALLED" "$(state_for hang --stall-min 0)" "stalled state"
printf '%s\n' '{"type":"system","subtype":"api_retry","attempt":1,"max_retries":10,"retry_delay_ms":3600000,"error_status":429}' >>"$LANE_HOME/hang.log"
sleep 2
assert_eq "WAITING" "$(state_for hang --stall-min 0)" "usage-limit wait is not a stall"
printf '%s\n' '{"type":"system","subtype":"api_retry","attempt":2,"max_retries":10,"retry_delay_ms":0,"error_status":529}' >>"$LANE_HOME/hang.log"
python3 -c 'import os, sys, time; t = time.time() - 900; os.utime(sys.argv[1], (t, t))' "$LANE_HOME/hang.log"
assert_eq "STALLED" "$(state_for hang --stall-min 0)" "elapsed retry wait"
sleep 30 &
UNRELATED_PID=$!
"$LANE" stop hang >/dev/null
kill -0 "$UNRELATED_PID" 2>/dev/null || fail "stop signalled an unrelated process"
kill "$UNRELATED_PID"
wait "$UNRELATED_PID" 2>/dev/null || true
UNRELATED_PID=""
assert_file "$LANE_HOME/hang.stalled-1.log"
assert_no_file "$LANE_HOME/hang.done"
assert_eq "DEAD" "$(state_for hang)" "stopped state"

echo "test: resume --note prepends and consumes a per-lane note"
printf '%s\n' 'Inspect the review findings before editing.' >"$TEST_TMP/resume.txt"
"$LANE" resume first --note "$TEST_TMP/resume.txt" >/dev/null
assert_no_file "$LANE_HOME/first.resume-note.md"
assert_file "$LANE_HOME/first.resume-note.consumed-1.md"
if repeated_resume_error=$("$LANE" resume first 2>&1); then
  fail "second back-to-back resume reused one note"
fi
grep -Fq 'lane: no resume note for first' <<<"$repeated_resume_error" || fail "second resume did not report no resume note"
wait_for_file "$LANE_HOME/first.done"
assert_eq \
  "Inspect the review findings before editing." \
  "$(head -1 "$LANE_HOME/first.log")" \
  "resume prompt prefix"
grep -q '^hi$' "$LANE_HOME/first.log" || fail "resumed fake worker did not finish"

echo "test: resume consumes an existing per-lane note without flags"
printf '%s\n' 'Use the saved lane-specific follow-up.' >"$LANE_HOME/first.resume-note.md"
"$LANE" resume first >/dev/null
wait_for_file "$LANE_HOME/first.done"
assert_no_file "$LANE_HOME/first.resume-note.md"
assert_file "$LANE_HOME/first.resume-note.consumed-2.md"
assert_eq "Use the saved lane-specific follow-up." "$(head -1 "$LANE_HOME/first.log")" "saved resume prompt prefix"

echo "test: resume without a per-lane note fails closed"
if resume_error=$("$LANE" resume first 2>&1); then
  fail "resume succeeded without a per-lane note"
fi
grep -Fq 'lane: no resume note for first (pass --note <file> or --no-note)' <<<"$resume_error" || fail "resume failure did not explain note options"

echo "test: resume --no-note uses only the standard worker prompt"
"$LANE" resume first --no-note >/dev/null
wait_for_file "$LANE_HOME/first.done"
assert_eq "Do the task in $BRIEF_REAL." "$(head -1 "$LANE_HOME/first.log")" "no-note prompt"
grep -q '^hi$' "$LANE_HOME/first.log" || fail "no-note resumed fake worker did not finish"

echo "test: --no-note re-sends the note of a stopped run"
printf '%s\n' 'Revision note for the stopped run.' >"$TEST_TMP/stopnote.txt"
LANE_FAKE_HOLD="$TEST_TMP/never-released" "$LANE" resume first --note "$TEST_TMP/stopnote.txt" >/dev/null
"$LANE" stop first >/dev/null
assert_no_file "$LANE_HOME/first.done"
stopped_resume=$("$LANE" resume first --no-note)
grep -Fq "lane: re-sending the interrupted run's note: $LANE_HOME/first.resume-note.consumed-3.md" <<<"$stopped_resume" || fail "stopped-run resume did not announce the re-sent note"
wait_for_file "$LANE_HOME/first.done"
assert_eq "Revision note for the stopped run." "$(head -1 "$LANE_HOME/first.log")" "stopped-run note re-sent"

echo "test: --no-note re-sends the note of a failed run, then drops it after success"
"$LANE" run notefail --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/notefail.done"
printf '%s\n' 'Revision note for the failed run.' >"$TEST_TMP/failnote.txt"
CODEX_FAKE_RC=1 "$LANE" resume notefail --note "$TEST_TMP/failnote.txt" >/dev/null
wait_for_file "$LANE_HOME/notefail.done"
assert_eq "EXIT=1" "$(<"$LANE_HOME/notefail.done")" "failed note run marker"
failed_resume=$("$LANE" resume notefail --no-note)
grep -Fq "lane: re-sending the interrupted run's note:" <<<"$failed_resume" || fail "failed-run resume did not announce the re-sent note"
wait_for_file "$LANE_HOME/notefail.done"
grep -Fxq 'Revision note for the failed run.' "$LANE_CAPTURE/codex.args" || fail "failed-run note was not re-sent"
assert_eq "EXIT=0" "$(<"$LANE_HOME/notefail.done")" "re-sent note run marker"
ok_resume=$("$LANE" resume notefail --no-note)
if grep -Fq "re-sending" <<<"$ok_resume"; then fail "successful run's note was re-sent"; fi
wait_for_file "$LANE_HOME/notefail.done"
if grep -Fq 'Revision note for the failed run.' "$LANE_CAPTURE/codex.args"; then fail "brief-only resume carried the old note"; fi

echo "test: global resume note path is absent"
if grep -Fq 'LANE_HOME/resume-note.md' "$LANE"; then
  fail "lane still references the global resume note"
fi

echo "test: reap is inspect-only without --force, then removes the lane"
sleep 0.2
reap_output=$("$LANE" reap first)
grep -q '^lane: git diff --stat' <<<"$reap_output" || fail "reap did not print diff stat"
grep -q '^scratch.txt$' <<<"$reap_output" || fail "reap did not list untracked files"
[ -d "$REPO/.claude/worktrees/codex-first" ] || fail "non-forced reap removed worktree"
# A lane's pre-commit leaves read-only trees; a bare `git worktree remove --force`
# cannot delete inside them and strands the files after unregistering the tree.
readonly_tree="$REPO/.claude/worktrees/codex-first/.claude/cache/index-trees/abc"
mkdir -p "$readonly_tree/scripts"
printf 'x\n' >"$readonly_tree/scripts/a.py"
chmod -R a-w "$readonly_tree"
"$LANE" reap first --force >/dev/null
assert_no_file "$REPO/.claude/worktrees/codex-first"
assert_no_file "$LANE_HOME/first.json"
git -C "$REPO" show-ref --verify --quiet refs/heads/codex/first && fail "reap left branch behind"

echo "test: no-worktree lanes cannot reap their repository"
"$LANE" run inline --repo "$REPO" --brief "$BRIEF" --worker fake --no-worktree >/dev/null
wait_for_file "$LANE_HOME/inline.done"
if "$LANE" reap inline --force >/dev/null 2>&1; then
  fail "reap accepted a --no-worktree lane"
fi
[ -d "$REPO/.git" ] || fail "no-worktree reap damaged the repository"

echo "test: invalid stall threshold fails closed"
if "$LANE" ls --stall-min nope >/dev/null 2>&1; then
  fail "ls accepted a non-numeric stall threshold"
fi

echo "test: review attaches the lane's cache result, not an unchanged tracked report made newest by mtime"
"$LANE" run rvcache --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
wait_for_file "$LANE_HOME/rvcache.done"
RVCACHE_WT="$REPO_REAL/.claude/worktrees/codex-rvcache"
mkdir -p "$RVCACHE_WT/docs/audit/x" "$RVCACHE_WT/.claude/cache"
printf '%s\n' unrelated >"$RVCACHE_WT/docs/audit/x/old-report.md"
git -C "$RVCACHE_WT" add docs/audit/x/old-report.md
git -C "$RVCACHE_WT" commit -qm "tracked unrelated report"
printf '%s\n' result >"$RVCACHE_WT/.claude/cache/rvcache-result.md"
touch -t 202001010000 "$RVCACHE_WT/.claude/cache/rvcache-result.md"
touch "$RVCACHE_WT/docs/audit/x/old-report.md"
rv_stdout=$(LLMX_CAPTURE_NAME=rvcache "$LANE" review rvcache --out "$TEST_TMP/rvcache.md")
grep -Fxq "$RVCACHE_WT/.claude/cache/rvcache-result.md" "$LANE_CAPTURE/rvcache.args" || fail "review omitted the lane cache result"
if grep -Fxq "$RVCACHE_WT/docs/audit/x/old-report.md" "$LANE_CAPTURE/rvcache.args"; then fail "review attached an unchanged tracked report"; fi
grep -Fxq "lane: report: $RVCACHE_WT/.claude/cache/rvcache-result.md" <<<"$rv_stdout" || fail "review did not print the attached report"

echo "test: review attaches the brief from metadata"
grep -Fxq "$BRIEF_REAL" "$LANE_CAPTURE/rvcache.args" || fail "review omitted the brief"
grep -Fxq "lane: brief: $BRIEF_REAL" <<<"$rv_stdout" || fail "review did not print the attached brief"

echo "test: review attaches a report the lane added in its own diff"
"$LANE" run rvown --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
wait_for_file "$LANE_HOME/rvown.done"
RVOWN_WT="$REPO_REAL/.claude/worktrees/codex-rvown"
mkdir -p "$RVOWN_WT/docs/audit/topic"
printf '%s\n' mine >"$RVOWN_WT/docs/audit/topic/new-report.md"
LLMX_CAPTURE_NAME=rvown "$LANE" review rvown --out "$TEST_TMP/rvown.md" >/dev/null
grep -Fxq "$RVOWN_WT/docs/audit/topic/new-report.md" "$LANE_CAPTURE/rvown.args" || fail "review omitted the lane's own report"

echo "test: review with no report fails loud in header and prompt"
"$LANE" run rvnone --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
wait_for_file "$LANE_HOME/rvnone.done"
rv_stdout=$(LLMX_CAPTURE_NAME=rvnone "$LANE" review rvnone --out "$TEST_TMP/rvnone.md")
grep -Fxq '# no lane report found' "$LANE_HOME/rvnone.patch" || fail "patch header omitted no-report note"
grep -Fq 'No lane report was found' "$LANE_CAPTURE/rvnone.args" || fail "prompt omitted no-report sentence"
assert_eq "2" "$(grep -c '^-f$' "$LANE_CAPTURE/rvnone.args")" "no-report file arguments (patch + brief)"
grep -Fxq "lane: report: none" <<<"$rv_stdout" || fail "review did not print report: none"

echo "PASS: lane lifecycle"
