#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
# Every lane call on the machine runs the live bin/lane: test an edit in a copy beside it (LANE_UNDER_TEST=<copy>).
LANE="${LANE_UNDER_TEST:-$ROOT/bin/lane}"
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/lane-test.XXXXXX")
mkdir -p "$TEST_TMP/lanes"
LANE_HOME=$(cd "$TEST_TMP/lanes" && pwd -P)
export LANE_HOME
# Every archive pass, by hand or after a retire, writes here and never to the real SSD. TMPDIR can end in "/",
# which leaves "//" in TEST_TMP, and lane-archive prints its volume normalized, so the volume path is resolved.
ARCHIVE_BASE=$(cd "$TEST_TMP" && pwd -P)
LANE_ARCHIVE_VOLUME="$ARCHIVE_BASE/ssd"
LANE_ARCHIVE_REQUIRE_MOUNT=0
export LANE_ARCHIVE_VOLUME LANE_ARCHIVE_REQUIRE_MOUNT
mkdir -p "$LANE_ARCHIVE_VOLUME"
unset LANE_CODEX_MODEL LANE_CODEX_EFFORT LANE_CODEX_ADD_DIRS LANE_CODEX_NETWORK LANE_CODEX_SANDBOX
unset LANE_CLAUDE_MODEL LANE_CLAUDE_EFFORT LANE_OPENCODE_MODEL CODEX_API_KEY LANE_CODEX_API_DAILY_USD
# lane-api-spend prices with llmx; the fake llmx below shadows the real one, so its interpreter is read first.
LANE_LLMX_PYTHON=$(sed -n '1s/^#!//p' "$(command -v llmx)")
export LANE_LLMX_PYTHON
REPO="$TEST_TMP/repo"
BRIEF="$TEST_TMP/brief.md"
FAKE_BIN="$TEST_TMP/bin"
LANE_CAPTURE="$TEST_TMP/capture"
export LANE_CAPTURE
# Fake workers run at lane's own priority, so a loaded machine cannot starve them past a wait:
# at load 95 a nice-10 worker missed the 10 s harvest wait (2026-11-02). The hang lane checks the default.
export LANE_NICE=0
UNRELATED_PID=""
CAP_WAIT_PID=""
ESCAPED_PID=""

cleanup() {
  local name
  # A run still waiting for a slot would start its lane once the stops below free one.
  if [ -n "$CAP_WAIT_PID" ]; then
    kill "$CAP_WAIT_PID" >/dev/null 2>&1 || true
  fi
  # The live-lane test gives a running lane a fake marker, and lane stop signals no lane that has one.
  rm -f "$LANE_HOME/archlive.done"
  for name in first rvcommit rvnobase hang inline codexargs codexoverride codexuvcache apicap2 claudeargs claudeoverride claudedirs ocargs ocquota ocquotalate failure rvcache rvown rvnone retire1 retirefail retirebusy retiresnap retireread hook1 hook2 ochook arch1 arch1.b archkeep archco archbound archlive archexit capa capb capfree nice0 escape; do
    if [ -f "$LANE_HOME/$name.json" ]; then
      "$LANE" stop "$name" >/dev/null 2>&1 || true
    fi
  done
  if [ -n "$UNRELATED_PID" ]; then
    kill "$UNRELATED_PID" >/dev/null 2>&1 || true
  fi
  # The escape test's child leads its own group, so a stop that misses it leaves it to this.
  if [ -n "$ESCAPED_PID" ]; then
    kill "$ESCAPED_PID" >/dev/null 2>&1 || true
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
  local limit="${2:-100}"
  local attempts=0
  while [ ! -f "$path" ] && [ "$attempts" -lt "$limit" ]; do
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

wait_for_text() {
  local path="$1"
  local text="$2"
  local attempts=0
  while ! grep -Fq -- "$text" "$path" 2>/dev/null && [ "$attempts" -lt 300 ]; do
    sleep 0.1
    attempts=$((attempts + 1))
  done
  grep -Fq -- "$text" "$path" || fail "$path never said '$text': $(cat "$path" 2>/dev/null)"
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

latest_harvest_of() {
  local entry
  local latest=""
  for entry in "$LANE_HOME/$1.harvest"/*Z; do
    [ -d "$entry" ] && latest="$entry"
  done
  printf '%s\n' "$latest"
}

# Back-date files, and everything under a directory, by <days>: a lane is archived only when its marker is 14 days old
# and no file of it changed in the last hour.
age_paths() {
  python3 - "$@" <<'PY'
import os
import sys
import time

stamp = time.time() - float(sys.argv[1]) * 86400
for top in sys.argv[2:]:
    paths = [top]
    for root, dirs, files in os.walk(top):
        paths.extend(os.path.join(root, name) for name in dirs + files)
    for path in paths:
        os.utime(path, (stamp, stamp), follow_symlinks=False)
PY
}

# A worker's group outlives its marker while the exit path's archive pass runs.
wait_group_exit() {
  local pid
  local attempts=0
  pid=$(json_value "$LANE_HOME/$1.json" pid)
  while kill -0 -- "-$pid" 2>/dev/null && [ "$attempts" -lt 300 ]; do
    sleep 0.1
    attempts=$((attempts + 1))
  done
  if kill -0 -- "-$pid" 2>/dev/null; then fail "process group $pid of $1 did not exit"; fi
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
  'calls=$(( $(cat "$LANE_CAPTURE/codex.calls" 2>/dev/null || echo 0) + 1 ))' \
  'echo "$calls" > "$LANE_CAPTURE/codex.calls"' \
  'if [ "$calls" -le "${CODEX_FAKE_CAPACITY:-0}" ]; then echo "ERROR: Selected model is at capacity"; exit 1; fi' \
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
# once, an exhausted balance, or a provider at capacity for the number of runs opencode-ratelimit holds (or forever),
# or a turn ended on a background shell for the number of runs opencode-background holds (or forever).
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
  'if [ -f "$capture/opencode-quota-late" ]; then' \
  '  printf "%s\n" "{\"type\":\"error\",\"timestamp\":2000,\"sessionID\":\"ses_fake\",\"error\":{\"type\":\"provider.quota\",\"message\":\"the organization is out of credit, add more to continue\",\"status\":402}}"' \
  '  printf "%s\n" "{\"type\":\"step_start\",\"timestamp\":1000,\"sessionID\":\"ses_fake\"}"' \
  '  exit 1' \
  'fi' \
  'if [ -f "$capture/opencode-quota" ]; then' \
  '  printf "%s\n" "{\"type\":\"error\",\"sessionID\":\"ses_fake\",\"error\":{\"type\":\"provider.http\",\"message\":\"402 Insufficient Balance\"}}"' \
  '  exit 0' \
  'fi' \
  'if [ -f "$capture/opencode-crash-once" ] && [ -s "$capture/opencode-ratelimit" ] && [ "$(cat "$capture/opencode-ratelimit")" = 0 ]; then' \
  '  rm "$capture/opencode-crash-once"' \
  '  echo "opencode: unknown model" >&2' \
  '  exit 1' \
  'fi' \
  'if [ -s "$capture/opencode-ratelimit" ] && [ "$(cat "$capture/opencode-ratelimit")" != 0 ]; then' \
  '  left=$(cat "$capture/opencode-ratelimit")' \
  '  [ "$left" = forever ] || echo "$((left - 1))" > "$capture/opencode-ratelimit"' \
  '  [ ! -f "$capture/opencode-ratelimit-progress" ] || printf "%s\n" "{\"type\":\"step_finish\",\"sessionID\":\"ses_fake\",\"part\":{}}"' \
  '  printf "%s\n" "{\"type\":\"step_start\",\"sessionID\":\"ses_fake\"}" "{\"type\":\"error\",\"sessionID\":\"ses_fake\",\"error\":{\"type\":\"provider.rate-limit\",\"message\":\"the model is at capacity, retry shortly\",\"retryAfterMs\":1500,\"status\":429}}"' \
  '  exit 1' \
  'fi' \
  'if [ -s "$capture/opencode-background" ] && [ "$(cat "$capture/opencode-background")" != 0 ]; then' \
  '  left=$(cat "$capture/opencode-background")' \
  '  [ "$left" = forever ] || echo "$((left - 1))" > "$capture/opencode-background"' \
  '  printf "%s\n" "{\"type\":\"tool_use\",\"sessionID\":\"ses_fake\",\"part\":{\"tool\":\"shell\",\"state\":{\"status\":\"completed\",\"input\":{\"command\":\"make\",\"background\":true}}}}" "{\"type\":\"text\",\"sessionID\":\"ses_fake\",\"part\":{\"text\":\"Waiting on make.\"}}"' \
  '  exit 0' \
  'fi' \
  'printf "%s\n" "{\"type\":\"step_finish\",\"sessionID\":\"ses_fake\",\"part\":{\"cost\":0.01,\"tokens\":{\"input\":100,\"output\":20,\"reasoning\":7,\"cache\":{\"read\":50,\"write\":0}}}}"' \
  >"$FAKE_BIN/opencode"
# lane-opencode's transport resume probes the provider host with curl; the fake records the URL and answers at once.
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'capture="$(cd "$(dirname "$0")/.." && pwd -P)/capture"' \
  'printf "%s\n" "${@: -1}" >> "$capture/curl.urls"' >"$FAKE_BIN/curl"
chmod +x "$FAKE_BIN/codex" "$FAKE_BIN/claude" "$FAKE_BIN/ps" "$FAKE_BIN/llmx" "$FAKE_BIN/opencode" "$FAKE_BIN/curl"
export PATH="$FAKE_BIN:$PATH"

echo "test: codex and claude worker commands match the dispatch contract"
CODEX_PROMPT="Do the fake task.

Git metadata is read-only in this sandbox: edit files and run checks, but do not merge, stage or commit. The parent does that. The sandbox also denies ps and sysctl, so /usr/bin/time -l exits 1 after a successful command: measure time and memory from Python (time.perf_counter, resource.getrusage). End by listing every path you changed."
"$LANE" run codexargs --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/codexargs.done"
expected_codex=$(printf '%s\n' \
  exec \
  -m \
  gpt-6-astra \
  -c \
  'model_reasoning_effort="high"' \
  -c \
  'service_tier="default"' \
  -c \
  'shell_environment_policy.set.LANE_WORKER="1"' \
  -c \
  'shell_environment_policy.set.LANE_NAME="codexargs"' \
  -c \
  "shell_environment_policy.set.LANE_HOME=\"$LANE_HOME\"" \
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
  -c \
  'service_tier="default"' \
  -c \
  'shell_environment_policy.set.LANE_WORKER="1"' \
  -c \
  'shell_environment_policy.set.LANE_NAME="codexoverride"' \
  -c \
  "shell_environment_policy.set.LANE_HOME=\"$LANE_HOME\"" \
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
  -c \
  'model_reasoning_effort="high"' \
  -c \
  'service_tier="default"' \
  -c \
  'shell_environment_policy.set.LANE_WORKER="1"' \
  -c \
  'shell_environment_policy.set.LANE_NAME="codexuvcache"' \
  -c \
  "shell_environment_policy.set.LANE_HOME=\"$LANE_HOME\"" \
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
  -c \
  'model_reasoning_effort="high"' \
  -c \
  'service_tier="default"' \
  -c \
  'shell_environment_policy.set.LANE_WORKER="1"' \
  -c \
  'shell_environment_policy.set.LANE_NAME="codexcpuslot"' \
  -c \
  "shell_environment_policy.set.LANE_HOME=\"$LANE_HOME\"" \
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

echo "test: codex adds each directory the repo names in lane.codexAddDir as a writable root"
git -C "$REPO" config --add lane.codexAddDir "$TEST_TMP/repo-roots/a"
git -C "$REPO" config --add lane.codexAddDir "$TEST_TMP/repo-roots/b"
roots_output=$("$LANE" run codexreporoots --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree)
wait_for_file "$LANE_HOME/codexreporoots.done"
git -C "$REPO" config --unset-all lane.codexAddDir
ROOT_A=$(cd "$TEST_TMP/repo-roots/a" && pwd -P)
ROOT_B=$(cd "$TEST_TMP/repo-roots/b" && pwd -P)
expected_roots=$(printf '%s\n' \
  exec \
  -m \
  gpt-6-astra \
  -c \
  'model_reasoning_effort="high"' \
  -c \
  'service_tier="default"' \
  -c \
  'shell_environment_policy.set.LANE_WORKER="1"' \
  -c \
  'shell_environment_policy.set.LANE_NAME="codexreporoots"' \
  -c \
  "shell_environment_policy.set.LANE_HOME=\"$LANE_HOME\"" \
  --add-dir \
  "$ROOT_A" \
  --add-dir \
  "$ROOT_B" \
  -s \
  workspace-write \
  --add-dir \
  "$HOME/.cache/uv" \
  --skip-git-repo-check \
  "$CODEX_PROMPT")
assert_eq "$expected_roots" "$(<"$LANE_CAPTURE/codex.args")" "codex repo writable roots"
grep -Fq "add_dirs=$ROOT_A:$ROOT_B network=" <<<"$roots_output" || fail "settings line omitted the repo's roots"

echo "test: codex runs in the sandbox the repo names in lane.codexSandbox, under the caller's override"
git -C "$REPO" config lane.codexSandbox danger-full-access
full_output=$("$LANE" run codexfull --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree)
wait_for_file "$LANE_HOME/codexfull.done"
FULL_PROMPT="Do the fake task.

Git state belongs to the parent: edit files and run checks, but do not stage, commit, merge, stash or switch branches. Do not stop or kill processes you did not start. End by listing every path you changed."
HOOKS="$LANE_HOME/codex-git-hooks"
expected_full=$(printf '%s\n' exec -m gpt-6-astra \
  -c 'model_reasoning_effort="high"' \
  -c 'service_tier="default"' \
  -c 'shell_environment_policy.set.LANE_WORKER="1"' \
  -c 'shell_environment_policy.set.LANE_NAME="codexfull"' \
  -c "shell_environment_policy.set.LANE_HOME=\"$LANE_HOME\"" \
  -c 'shell_environment_policy.set.GIT_CONFIG_COUNT="1"' \
  -c 'shell_environment_policy.set.GIT_CONFIG_KEY_0="core.hooksPath"' \
  -c "shell_environment_policy.set.GIT_CONFIG_VALUE_0=\"$HOOKS\"" \
  -s danger-full-access --add-dir "$HOME/.cache/uv" --skip-git-repo-check "$FULL_PROMPT")
assert_eq "$expected_full" "$(<"$LANE_CAPTURE/codex.args")" "codex repo sandbox"
grep -Fq " sandbox=danger-full-access" <<<"$full_output" || fail "settings line omitted the repo's sandbox"
HOOKREPO="$TEST_TMP/hookrepo"
git init -q "$HOOKREPO"
git -C "$HOOKREPO" -c user.email=t@t -c user.name=t commit -q --allow-empty -m base
git init -q --bare "$TEST_TMP/hookremote.git"
hooked() { GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0="$HOOKS" git -C "$HOOKREPO" "$@"; }
# A scratch repository under a temporary directory is a test's fixture: its commits and pushes pass, through its
# own hook (arena's tools suite failed every fixture in a full-access lane on 2026-11-11).
hooked -c user.email=t@t -c user.name=t commit -q --allow-empty -m fixture ||
  fail "a full-access codex lane's hooks refused a temporary fixture repository's commit"
hooked push -q "$TEST_TMP/hookremote.git" HEAD:refs/heads/fixture ||
  fail "a full-access codex lane's hooks refused a temporary fixture repository's push"
printf '%s\n' '#!/bin/sh' 'echo own hook >&2' 'exit 1' > "$HOOKREPO/.git/hooks/pre-commit"
chmod +x "$HOOKREPO/.git/hooks/pre-commit"
if hooked -c user.email=t@t -c user.name=t commit -q --allow-empty -m own 2>"$TEST_TMP/own-hook.err"; then
  fail "a fixture repository's own pre-commit hook did not run under the lane's hooks"
fi
grep -Fxq "own hook" "$TEST_TMP/own-hook.err" || fail "the fixture's own hook was not the one that refused"
rm -f "$HOOKREPO/.git/hooks/pre-commit"
# Any other repository, the lane's own worktree's included, refuses: a fake git puts its common dir outside them.
mkdir -p "$TEST_TMP/realgit"
printf '%s\n' '#!/bin/sh' 'echo /Users/lane-test/project/.git' > "$TEST_TMP/realgit/git"
chmod +x "$TEST_TMP/realgit/git"
for hook in pre-commit pre-push pre-rebase pre-merge-commit pre-applypatch; do
  if PATH="$TEST_TMP/realgit:$PATH" "$HOOKS/$hook" 2>"$TEST_TMP/real-hook.err" </dev/null; then
    fail "a full-access codex lane's $hook let a write through outside a temporary directory"
  fi
  grep -Fq "git writes belong to the parent" "$TEST_TMP/real-hook.err" || fail "$hook refused without its reason"
done
printf '%s\n' '#!/bin/sh' 'exit 128' > "$TEST_TMP/realgit/git"
if PATH="$TEST_TMP/realgit:$PATH" "$HOOKS/pre-commit" 2>/dev/null; then
  fail "a full-access codex lane's hook let a write through when git could not name the repository"
fi
hooked status --short >/dev/null || fail "a full-access codex lane's hooks broke git status"
LANE_CODEX_SANDBOX=workspace-write "$LANE" run codexpinned --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/codexpinned.done"
assert_eq "${expected_codex//LANE_NAME=\"codexargs\"/LANE_NAME=\"codexpinned\"}" "$(<"$LANE_CAPTURE/codex.args")" "caller's sandbox over the repo's"
git -C "$REPO" config lane.codexSandbox bogus
if "$LANE" run codexbogus --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null 2>&1; then
  fail "an invalid lane.codexSandbox started a lane"
fi
git -C "$REPO" config --unset lane.codexSandbox

echo "test: codex resume retains settings without caller exports"
resume_output=$("$LANE" resume codexoverride --no-note)
wait_for_file "$LANE_HOME/codexoverride.done"
assert_eq "$expected_override" "$(<"$LANE_CAPTURE/codex.args")" "resumed codex settings"
settings_line="lane: settings codex_model=gpt-6.1-sol codex_effort=high add_dirs=$TEST_TMP/slots:$TEST_TMP/extra root network=1 sandbox=workspace-write"
grep -Fxq "$settings_line" <<<"$override_output" || fail "run omitted effective codex settings"
grep -Fxq "$settings_line" <<<"$resume_output" || fail "resume omitted effective codex settings"
assert_eq "gpt-6.1-sol" "$(worker_setting "$LANE_HOME/codexoverride.json" codex_model)" "recorded codex model"
assert_eq "high" "$(worker_setting "$LANE_HOME/codexoverride.json" codex_effort)" "recorded codex effort"
assert_eq "$TEST_TMP/slots:$TEST_TMP/extra root" "$(worker_setting "$LANE_HOME/codexoverride.json" codex_add_dirs)" "recorded writable roots"
assert_eq "1" "$(worker_setting "$LANE_HOME/codexoverride.json" codex_network)" "recorded network"
assert_eq "gpt-6-astra" "$(worker_setting "$LANE_HOME/codexargs.json" codex_model)" "recorded default codex model"
assert_eq "high" "$(worker_setting "$LANE_HOME/codexargs.json" codex_effort)" "recorded default codex effort"
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
assert_eq "${expected_codex//LANE_NAME=\"codexargs\"/LANE_NAME=\"codexoverride\"}" "$(<"$LANE_CAPTURE/codex.args")" "empty exports restore default codex arguments"

echo "test: legacy resume warns and uses caller environment"
python3 -c 'import json, sys; path = sys.argv[1]; data = json.load(open(path, encoding="utf-8")); del data["worker_settings"]; open(path, "w", encoding="utf-8").write(json.dumps(data) + "\n")' "$LANE_HOME/codexoverride.json"
legacy_output=$(LANE_CODEX_MODEL=gpt-6.1-sol LANE_CODEX_EFFORT=high LANE_CODEX_ADD_DIRS="$TEST_TMP/slots:$TEST_TMP/extra root" LANE_CODEX_NETWORK=1 "$LANE" resume codexoverride --no-note 2>&1)
wait_for_file "$LANE_HOME/codexoverride.done"
grep -Fq 'original worker settings are unknown; using caller environment' <<<"$legacy_output" || fail "legacy resume omitted settings warning"
assert_eq "$expected_override" "$(<"$LANE_CAPTURE/codex.args")" "legacy codex environment fallback"
for key in name repo worktree brief pid started_at started_epoch worker; do
  grep -q "\"$key\"" "$LANE_HOME/codexargs.json" || fail "metadata omitted $key"
done

echo "test: a codex worker billed to CODEX_API_KEY starts only under the day's API cap"
LANE_CODEX_SESSIONS="$TEST_TMP/codex-sessions"
LLMX_USAGE_LOG="$TEST_TMP/llmx-usage.jsonl"
export LANE_CODEX_SESSIONS LLMX_USAGE_LOG
: >"$LLMX_USAGE_LOG"
# One API call of 250k uncached Sol input and 150k output ($2.00, under the 272k long-prompt rate), the same call's
# repeated token_count, and a plan call (Codex window).
python3 - "$LANE_CODEX_SESSIONS" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
now = datetime.now(timezone.utc)
folder = Path(sys.argv[1]) / f"{now.astimezone():%Y/%m/%d}"
folder.mkdir(parents=True)
stamp = now.isoformat().replace("+00:00", "Z")
def count(total, rate_limits):
    usage = {"input_tokens": 250_000, "cached_input_tokens": 0, "cache_write_input_tokens": 0, "output_tokens": 150_000}
    return {"timestamp": stamp, "type": "event_msg", "payload": {"type": "token_count", "rate_limits": rate_limits,
            "info": {"last_token_usage": usage, "total_token_usage": {"total_tokens": total}}}}
records = [{"timestamp": stamp, "type": "session_meta", "payload": {"cwd": "/work/apicap-fixture"}},
           {"timestamp": stamp, "type": "turn_context", "payload": {"model": "gpt-6.1-sol"}},
           {"timestamp": stamp, "type": "event_msg", "payload": {"type": "thread_settings_applied",
            "thread_settings": {"service_tier": "default"}}},
           count(1_000_000, None), count(1_000_000, None),
           count(2_000_000, {"limit_id": "codex", "primary": {"used_percent": 50.0}})]
(folder / "rollout-apicap.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
PY
assert_eq "2.00" "$("$ROOT/bin/lane-api-spend" --total)" "API spend counts the API call once and no plan call"
for case in "ultrafast 12.00" "fast 4.00" "flex 1.00"; do
  tier=${case% *}; tier_dir="$TEST_TMP/tier-$tier"; mkdir -p "$tier_dir"
  cp -R "$LANE_CODEX_SESSIONS/." "$tier_dir/"
  find "$tier_dir" -name 'rollout-*.jsonl' -exec sed -i.bak "s/\"service_tier\": \"default\"/\"service_tier\": \"$tier\"/" {} +
  find "$tier_dir" -name '*.bak' -delete
  assert_eq "${case#* }" "$(LANE_CODEX_SESSIONS="$tier_dir" "$ROOT/bin/lane-api-spend" --total)" "API spend prices the $tier tier"
done
for tier in priority none; do
  tier_dir="$TEST_TMP/tier-$tier"; mkdir -p "$tier_dir"; cp -R "$LANE_CODEX_SESSIONS/." "$tier_dir/"
  if [ "$tier" = none ]; then
    find "$tier_dir" -name 'rollout-*.jsonl' -exec sed -i.bak '/thread_settings_applied/d' {} +
  else
    find "$tier_dir" -name 'rollout-*.jsonl' -exec sed -i.bak 's/"service_tier": "default"/"service_tier": "priority"/' {} +
  fi
  find "$tier_dir" -name '*.bak' -delete
  rc=0; LANE_CODEX_SESSIONS="$tier_dir" "$ROOT/bin/lane-api-spend" --total >/dev/null 2>&1 || rc=$?
  assert_eq "3" "$rc" "an API call at tier $tier has no price, so the cap refuses"
done
if cap_output=$(CODEX_API_KEY=test-key LANE_CODEX_API_DAILY_USD=2 "$LANE" run apicap --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree 2>&1); then
  fail "run started a codex worker billed to CODEX_API_KEY at the day's cap"
fi
grep -Fq 'at or over LANE_CODEX_API_DAILY_USD=$2' <<<"$cap_output" || fail "cap refusal omitted its reason: $cap_output"
[ ! -e "$LANE_HOME/apicap.json" ] || fail "a refused run left lane metadata"
under_output=$(CODEX_API_KEY=test-key LANE_CODEX_API_DAILY_USD=3 "$LANE" run apicap2 --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree)
wait_for_file "$LANE_HOME/apicap2.done"
grep -Fxq 'lane: OpenAI API spend today $2.00 of $3' <<<"$under_output" || fail "run under the cap omitted the spend: $under_output"
if CODEX_API_KEY=test-key LANE_CODEX_API_DAILY_USD=1.5 "$LANE" resume apicap2 --no-note >/dev/null 2>&1; then
  fail "resume started a codex worker billed to CODEX_API_KEY past the day's cap"
fi
"$LANE" resume apicap2 --no-note >/dev/null
wait_for_file "$LANE_HOME/apicap2.done"
unset LANE_CODEX_SESSIONS LLMX_USAGE_LOG

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
expected_claude=$(printf '%s\n' -p --model opus --effort high --output-format stream-json --verbose "Do the fake task.")
assert_eq "$expected_claude" "$(<"$LANE_CAPTURE/claude.args")" "claude arguments"
assert_eq "$REPO_REAL" "$(<"$LANE_CAPTURE/claude.cwd")" "claude cwd"
assert_eq "opus" "$(worker_setting "$LANE_HOME/claudeargs.json" claude_model)" "recorded default claude model"
assert_eq "high" "$(worker_setting "$LANE_HOME/claudeargs.json" claude_effort)" "recorded default claude effort"

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

echo "test: claude resume continues the conversation only when asked"
grep -Fxq -- --continue "$LANE_CAPTURE/claude.args" && fail "a plain resume must start a new session"
LANE_CLAUDE_CONTINUE=1 "$LANE" resume claudeoverride --no-note >/dev/null
wait_for_file "$LANE_HOME/claudeoverride.done"
grep -Fxq -- --continue "$LANE_CAPTURE/claude.args" || fail "LANE_CLAUDE_CONTINUE=1 must pass --continue on resume"
LANE_CLAUDE_CONTINUE=1 "$LANE" run claudefresh --repo "$REPO" --brief "$BRIEF" --worker claude --no-worktree >/dev/null
wait_for_file "$LANE_HOME/claudefresh.done"
grep -Fxq -- --continue "$LANE_CAPTURE/claude.args" && fail "a first run has no conversation to continue"

echo "test: claude worker passes LANE_CLAUDE_ADD_DIRS as --add-dir and keeps them on resume"
claudedirs_output=$(LANE_CLAUDE_ADD_DIRS="$TEST_TMP/reviews:$TEST_TMP/extra root:" "$LANE" run claudedirs --repo "$REPO" --brief "$BRIEF" --worker claude --no-worktree)
wait_for_file "$LANE_HOME/claudedirs.done"
expected_claude_dirs=$(printf '%s\n' -p --model opus --effort high --add-dir "$TEST_TMP/reviews" --add-dir "$TEST_TMP/extra root" --output-format stream-json --verbose "Do the fake task.")
assert_eq "$expected_claude_dirs" "$(<"$LANE_CAPTURE/claude.args")" "claude add-dir arguments"
grep -Fxq "lane: settings claude_model=opus claude_effort=high add_dirs=$TEST_TMP/reviews:$TEST_TMP/extra root" <<<"$claudedirs_output" || fail "run omitted claude add_dirs"
assert_eq "$TEST_TMP/reviews:$TEST_TMP/extra root" "$(worker_setting "$LANE_HOME/claudedirs.json" claude_add_dirs)" "recorded claude add dirs"
"$LANE" resume claudedirs --no-note >/dev/null
wait_for_file "$LANE_HOME/claudedirs.done"
assert_eq "$expected_claude_dirs" "$(<"$LANE_CAPTURE/claude.args")" "resumed claude add-dir arguments"

echo "test: opencode worker scrubs the env, writes its guard, resumes a transport error and logs usage"
export DEEPSEEK_API_KEY_METERED="must-not-leak" LANE_OPENCODE_RETRY_SLEEP=0 LANE_OPENCODE_PROVIDER_HOST=""
touch "$LANE_CAPTURE/opencode-transport-once"
"$LANE" run ocargs --repo "$REPO" --brief "$BRIEF" --worker opencode --keep-checkout >/dev/null
wait_for_file "$LANE_HOME/ocargs.done"
unset DEEPSEEK_API_KEY_METERED
OC_WORKTREE="$REPO_REAL/.claude/worktrees/codex-ocargs"
assert_eq "EXIT=0" "$(<"$LANE_HOME/ocargs.done")" "opencode marker after one transport resume"
assert_eq "$OC_WORKTREE" "$(<"$LANE_CAPTURE/opencode.cwd")" "opencode cwd"
# LANE_OPENCODE_MODEL is unset, so the model is lane-opencode's own default: bin/lane passes and records none.
oc_default=$(sed -n 's/^model=\${LANE_OPENCODE_MODEL:-\(.*\)}$/\1/p' "$ROOT/bin/lane-opencode")
[ -n "$oc_default" ] || fail "lane-opencode names no default model"
expected_oc=$(printf '%s\n' run --standalone --auto --format json --thinking -m "$oc_default" --title ocargs)
assert_eq "$expected_oc" "$(head -10 "$LANE_CAPTURE/opencode.args.0")" "opencode arguments"
grep -Fxq "lane-opencode: model $oc_default" "$LANE_HOME/ocargs.log" || fail "opencode log does not name its model"
sed -n 11p "$LANE_CAPTURE/opencode.args.0" | grep -Fxq "Do the fake task." || fail "opencode prompt lacks the brief"
grep -Fq "do not stage, commit, merge, stash or switch branches" "$LANE_CAPTURE/opencode.args.0" || fail "opencode prompt lacks the git contract"
assert_eq "ses_fake" "$(arg_after --session "$LANE_CAPTURE/opencode.args.1")" "transport resume continues the session"
grep -Fq "ended on a transport error, a dropped connection or a provider at capacity" "$LANE_CAPTURE/opencode.args.1" ||
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
required += [{"action": "shell", "resource": kill, "effect": "deny"}
             for kill in ("*pkill*", "*killall*", "*xargs*kill", "kill *$*", "kill *`*")]
required.append({"action": "shell", "resource": "kill $!", "effect": "allow"})
sys.exit(0 if all(rule in rules for rule in required) else 1)
PY
python3 - "$oc_guard" <<'PY' || fail "opencode guard misjudges a kill by pattern, a recorded-PID kill or a listing"
import json
import re
import sys

# OpenCode 2.2.5's shell check, read from its binary: each simple command and each command substitution is a resource
# of its own (each list below is what its scanner returns for the command), the last rule whose action and resource
# match decides a resource, and one denied resource refuses the call. Its matcher reads backslashes as `/`, turns `*`
# into `.*` and `?` into `.`, makes a trailing ` *` optional and matches across newlines.
def matches(text, pattern):
    regex = re.sub(r"[.+^${}()|[\]\\]", lambda m: "\\" + m.group(0), pattern.replace("\\", "/"))
    regex = regex.replace("*", ".*").replace("?", ".")
    if regex.endswith(" .*"):
        regex = regex[:-3] + "( .*)?"
    return re.fullmatch(regex, text.replace("\\", "/"), re.S) is not None


rules = json.load(open(sys.argv[1]))["permissions"]


def refused(resources):
    decided = [[rule for rule in rules if matches("shell", rule["action"]) and matches(resource, rule["resource"])]
               for resource in resources]
    return any(found and found[-1]["effect"] == "deny" for found in decided)


kills = {
    "pgrep -f x | xargs kill": ["pgrep -f x", "xargs kill"],
    "kill $(pgrep -f x)": ["kill $(pgrep -f x)", "pgrep -f x"],
    "kill `pgrep -f x`": ["kill `pgrep -f x`", "pgrep -f x"],
    "for p in $(pgrep x); do kill -9 $p; done": ["pgrep x", "kill -9 $p"],
    "pids=$(pgrep -f x); kill $pids": ["pgrep -f x", "kill $pids"],
    "kill ${=pids}": ["kill ${=pids}"],
    "pgrep -f x | while read p; do kill $p; done": ["pgrep -f x", "read p", "kill $p"],
    "kill $(ps aux | grep '[s]erver' | awk '{print $2}')":
        ["kill $(ps aux | grep '[s]erver' | awk '{print $2}')", "ps aux", "grep '[s]erver'", "awk '{print $2}'"],
    "sh -c 'pgrep x | xargs kill'": ["sh -c 'pgrep x | xargs kill'"],
    "pkill -f 'a|b'": ["pkill -f 'a|b'"],
    "killall sleep": ["killall sleep"],
    "kill -9 -1": ["kill -9 -1"],
}
allowed = {
    "pgrep -fl 'takes2' | ~/Projects/skills/bin/redact-env | cut -c1-180":
        ["pgrep -fl 'takes2'", "~/Projects/skills/bin/redact-env", "cut -c1-180"],
    "sleep 30 & kill $!": ["sleep 30", "kill $!"],
    'kill -TERM "$!"': ['kill -TERM "$!"'],
    'kill -0 "$pid" 2>/dev/null': ['kill -0 "$pid" 2>/dev/null'],
    "kill -TERM -- -4425": ["kill -TERM -- -4425"],
    "rg -l kill src | xargs grep -l skills": ["rg -l kill src", "xargs grep -l skills"],
    "python3 - <<'EOF'\n# a kill proc fires after $x\nEOF": ["python3 - <<'EOF'\n# a kill proc fires after $x\nEOF"],
}
wrong = [command for command, resources in kills.items() if not refused(resources)]
wrong += [command for command, resources in allowed.items() if refused(resources)]
for command in wrong:
    print(f"misjudged: {command!r}", file=sys.stderr)
sys.exit(1 if wrong else 0)
PY
assert_eq "" "$(git -C "$OC_WORKTREE" status --porcelain)" "opencode guard is excluded from git status"
grep -Fxq "lane-opencode: usage steps=1 input=100 output=20 reasoning=7 cache_read=50 cache_write=0 cost_list=0.0100" \
  "$LANE_HOME/ocargs.log" || fail "opencode usage line missing"
assert_eq "" "$(worker_setting "$LANE_HOME/ocargs.json" opencode_model)" "bin/lane records no opencode model of its own"

echo "test: an exhausted opencode balance exits 86 without a retry"
touch "$LANE_CAPTURE/opencode-quota"
"$LANE" run ocquota --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocquota.done"
rm "$LANE_CAPTURE/opencode-quota"
unset LANE_OPENCODE_RETRY_SLEEP LANE_OPENCODE_PROVIDER_HOST
assert_eq "EXIT=86" "$(<"$LANE_HOME/ocquota.done")" "quota marker"
grep -Fq "do not retry" "$LANE_HOME/ocquota.log" || fail "quota stop message missing"
[ "$(find "$LANE_CAPTURE" -name 'opencode.args.*' | wc -l | tr -d ' ')" = 3 ] || fail "quota run retried"

echo "test: a balance error logged before the step_start it follows still exits 86 without a retry"
export LANE_OPENCODE_RETRY_SLEEP=0 LANE_OPENCODE_PROVIDER_HOST=""
touch "$LANE_CAPTURE/opencode-quota-late"
"$LANE" run ocquotalate --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocquotalate.done"
rm "$LANE_CAPTURE/opencode-quota-late"
unset LANE_OPENCODE_RETRY_SLEEP LANE_OPENCODE_PROVIDER_HOST
assert_eq "EXIT=86" "$(<"$LANE_HOME/ocquotalate.done")" "out-of-order quota marker"
[ "$(find "$LANE_CAPTURE" -name 'opencode.args.*' | wc -l | tr -d ' ')" = 4 ] || fail "out-of-order quota run retried"

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

echo "test: an opencode turn that ends on a background command resumes in the foreground, twice at most"
export LANE_OPENCODE_RETRY_SLEEP=0 LANE_OPENCODE_PROVIDER_HOST=""
rm -f "$LANE_CAPTURE"/opencode.args.*
echo 1 >"$LANE_CAPTURE/opencode-background"
"$LANE" run ocbg --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocbg.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/ocbg.done")" "opencode marker after a background resume"
grep -Fq "This run is headless" "$LANE_CAPTURE/opencode.args.0" || fail "opencode prompt lacks the headless note"
assert_eq "ses_fake" "$(arg_after --session "$LANE_CAPTURE/opencode.args.1")" "a background resume continues the session"
grep -Fq "Your turn ended after you started a shell command in the background" "$LANE_CAPTURE/opencode.args.1" ||
  fail "a background resume lacks its prompt"
rm -f "$LANE_CAPTURE"/opencode.args.*
echo forever >"$LANE_CAPTURE/opencode-background"
"$LANE" run ocbg2 --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocbg2.done"
rm "$LANE_CAPTURE/opencode-background"
unset LANE_OPENCODE_RETRY_SLEEP LANE_OPENCODE_PROVIDER_HOST
assert_eq "EXIT=87" "$(<"$LANE_HOME/ocbg2.done")" "a worker that keeps backgrounding stops with 87"
[ "$(find "$LANE_CAPTURE" -name 'opencode.args.*' | wc -l | tr -d ' ')" = 3 ] || fail "background resumes passed their cap"
grep -Fq "[DEGRADED] the worker ended its turn on a background command again" "$LANE_HOME/ocbg2.log" ||
  fail "the background cap is not loud"

echo "test: a LithosAI transport resume waits for the provider's host"
export LANE_OPENCODE_RETRY_SLEEP=0
rm -f "$LANE_CAPTURE/curl.urls"
touch "$LANE_CAPTURE/opencode-transport-once"
LANE_OPENCODE_MODEL=lithosai/deepseek-ai/DeepSeek-V4.1-Flash \
  "$LANE" run ocdns --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocdns.done"
unset LANE_OPENCODE_RETRY_SLEEP
assert_eq "EXIT=0" "$(<"$LANE_HOME/ocdns.done")" "LithosAI lane after one transport resume"
assert_eq "https://api.lithosai.cloud/" "$(<"$LANE_CAPTURE/curl.urls")" "LithosAI resume probes its host"

echo "test: a provider at capacity is retried in its session, a LithosAI tier steps down, and the wait cap exits 85"
export LANE_OPENCODE_RETRY_SLEEP=0 LANE_OPENCODE_PROVIDER_HOST="" LANE_OPENCODE_OVERLOAD_FLOOR=1 LANE_OPENCODE_OVERLOAD_CAP=3
rm -f "$LANE_CAPTURE"/opencode.args.*
echo 2 >"$LANE_CAPTURE/opencode-ratelimit"
LANE_OPENCODE_MODEL=lithosai/deepseek-ai/DeepSeek-V4.1-Flash-ultra \
  "$LANE" run ocbusy --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocbusy.done" 600
assert_eq "EXIT=0" "$(<"$LANE_HOME/ocbusy.done")" "opencode marker after two capacity refusals"
assert_eq "lithosai/deepseek-ai/DeepSeek-V4.1-Flash-ultra" "$(worker_setting "$LANE_HOME/ocbusy.json" opencode_model)" \
  "recorded opencode model override"
assert_eq "ses_fake" "$(arg_after --session "$LANE_CAPTURE/opencode.args.1")" "a capacity retry continues the session"
grep -Fq "or a provider at capacity" "$LANE_CAPTURE/opencode.args.1" || fail "a capacity retry lacks the resume prompt"
grep -Fq "Do the fake task." "$LANE_CAPTURE/opencode.args.1" || fail "a retry before any finished step lost the task"
grep -Fq "retry 1 in 2s" "$LANE_HOME/ocbusy.log" || fail "a capacity retry did not wait out retryAfterMs"
assert_eq "lithosai/deepseek-ai/DeepSeek-V4.1-Flash-ultra" "$(arg_after -m "$LANE_CAPTURE/opencode.args.1")" \
  "one refusal keeps the tier"
grep -Fq "[DEGRADED] tier ultra→fast" "$LANE_HOME/ocbusy.log" || fail "the tier step-down is not loud"
assert_eq "lithosai/deepseek-ai/DeepSeek-V4.1-Flash-fast" "$(arg_after -m "$LANE_CAPTURE/opencode.args.2")" \
  "two refusals in a row step the tier down"
[ ! -e "$LANE_CAPTURE/opencode.args.3" ] || fail "the capacity run went on after its success"
echo 2 >"$LANE_CAPTURE/opencode-ratelimit"
touch "$LANE_CAPTURE/opencode-ratelimit-progress"
LANE_OPENCODE_OVERLOAD_CAP=2 LANE_OPENCODE_MODEL=lithosai/deepseek-ai/DeepSeek-V4.1-Flash \
  "$LANE" run ocspell --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocspell.done" 600
rm "$LANE_CAPTURE/opencode-ratelimit-progress"
assert_eq "EXIT=0" "$(<"$LANE_HOME/ocspell.done")" "refusals with finished steps between them each get the whole cap"
rm -f "$LANE_CAPTURE"/opencode.args.*
echo forever >"$LANE_CAPTURE/opencode-ratelimit"
LANE_OPENCODE_MODEL=lithosai/deepseek-ai/DeepSeek-V4.1-Flash \
  "$LANE" run ocfull --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/ocfull.done" 600
rm "$LANE_CAPTURE/opencode-ratelimit"
unset LANE_OPENCODE_RETRY_SLEEP LANE_OPENCODE_PROVIDER_HOST LANE_OPENCODE_OVERLOAD_FLOOR LANE_OPENCODE_OVERLOAD_CAP
assert_eq "EXIT=85" "$(<"$LANE_HOME/ocfull.done")" "capacity marker once the wait cap is reached"
grep -Fq "STOPPED: the provider is still at capacity" "$LANE_HOME/ocfull.log" || fail "capacity stop message missing"
assert_eq "ses_fake" "$(arg_after --session "$LANE_CAPTURE/opencode.args.1")" "the capped run retried in its session"
[ ! -e "$LANE_CAPTURE/opencode.args.2" ] || fail "capacity retries ran past the cap"
export LANE_OPENCODE_RETRY_SLEEP=0 LANE_OPENCODE_PROVIDER_HOST="" LANE_OPENCODE_OVERLOAD_FLOOR=1 LANE_OPENCODE_OVERLOAD_CAP=3
rm -f "$LANE_CAPTURE"/opencode.args.*
echo 1 >"$LANE_CAPTURE/opencode-ratelimit"
touch "$LANE_CAPTURE/opencode-crash-once"
"$LANE" run occrash --repo "$REPO" --brief "$BRIEF" --worker opencode --no-worktree >/dev/null
wait_for_file "$LANE_HOME/occrash.done" 600
rm -f "$LANE_CAPTURE/opencode-ratelimit" "$LANE_CAPTURE/opencode-crash-once"
unset LANE_OPENCODE_RETRY_SLEEP LANE_OPENCODE_PROVIDER_HOST LANE_OPENCODE_OVERLOAD_FLOOR LANE_OPENCODE_OVERLOAD_CAP
assert_eq "EXIT=1" "$(<"$LANE_HOME/occrash.done")" "a retry that dies before any event is not a refusal"
grep -Fq "attempt 1 rc=1 last=error:empty" "$LANE_HOME/occrash.log" || fail "the crash took the previous refusal's verdict"

echo "test: worker failures still produce an exit marker"
CODEX_FAKE_RC=7 "$LANE" run failure --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/failure.done"
assert_eq "EXIT=7" "$(<"$LANE_HOME/failure.done")" "failure marker"
assert_eq "DONE:7" "$(state_for failure)" "failed worker state"

echo "test: a launch refuses while another launch of its name holds the lock, and takes a stale lock"
# On 2026-11-07 two launches of one name raced: the first supervisor deleted the prompt file the second needed, the
# second exited 125 with no marker and an empty log, and the metadata named the dead one.
mkdir "$LANE_HOME/.launch-locked.lock"
printf '%s\n' "$$" >"$LANE_HOME/.launch-locked.lock/pid"
if locked_output=$("$LANE" run locked --repo "$REPO" --brief "$BRIEF" --worker fake --no-worktree 2>&1); then
  fail "a launch ran while another launch of its name held the lock"
fi
grep -Fq "another launch of locked holds $LANE_HOME/.launch-locked.lock (pid $$)" <<<"$locked_output" ||
  fail "the refused launch did not name the lock and its holder: $locked_output"
for leftover in locked.json locked.log locked.prompt locked.supervisor; do
  [ ! -e "$LANE_HOME/$leftover" ] || fail "the refused launch wrote $leftover"
done
(exit 0) &
dead_pid=$!
wait "$dead_pid"
printf '%s\n' "$dead_pid" >"$LANE_HOME/.launch-locked.lock/pid"
"$LANE" run locked --repo "$REPO" --brief "$BRIEF" --worker fake --no-worktree >/dev/null
wait_for_file "$LANE_HOME/locked.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/locked.done")" "launch that took a stale lock"
[ ! -e "$LANE_HOME/.launch-locked.lock" ] || fail "the launch kept its name's lock after it recorded the lane"

echo "test: a launch takes a lock whose holder's pid now names a later process"
# A live pid kept a dead launcher's lock while the process that reused the pid lived. FAKE_BIN's ps dates every process
# to 2026-08-27, so the live pid below started after this pid file was written and cannot have written it.
mkdir "$LANE_HOME/.launch-reused.lock"
printf '%s\n' "$$" >"$LANE_HOME/.launch-reused.lock/pid"
touch -t 202601010000 "$LANE_HOME/.launch-reused.lock/pid"
"$LANE" run reused --repo "$REPO" --brief "$BRIEF" --worker fake --no-worktree >/dev/null ||
  fail "a launch refused a lock whose pid a later process reused"
wait_for_file "$LANE_HOME/reused.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/reused.done")" "launch that took a lock from a reused pid"
[ ! -e "$LANE_HOME/.launch-reused.lock" ] || fail "the launch kept the reused lock after it recorded the lane"

echo "test: a supervisor that cannot read its prompt or enter its checkout logs why and writes EXIT=125"
# Its stdout and stderr go nowhere until the worker starts, so both exits left an empty log and no marker.
awk "/^  supervisor_script='\$/{body=1; next} body && /^  '\$/{exit} body" "$LANE" >"$TEST_TMP/supervisor.sh"
[ -s "$TEST_TMP/supervisor.sh" ] || fail "could not cut the supervisor script out of $LANE"
printf 'prompt' >"$TEST_TMP/start.prompt"
for start_case in prompt checkout; do
  cp "$TEST_TMP/supervisor.sh" "$TEST_TMP/start-$start_case.sh"
  start_prompt="$TEST_TMP/start.prompt"
  start_dir="$TEST_TMP"
  if [ "$start_case" = prompt ]; then start_prompt="$TEST_TMP/no-such.prompt"; else start_dir="$TEST_TMP/no-such-dir"; fi
  start_rc=0
  bash -c '. "$0"' "$TEST_TMP/start-$start_case.sh" "$TEST_TMP/start-$start_case.log" "$TEST_TMP/start-$start_case.done" \
    fake "$start_prompt" "$BRIEF" "$start_dir" false "$TEST_TMP/start-$start_case.state" </dev/null >/dev/null 2>&1 ||
    start_rc=$?
  assert_eq "125" "$start_rc" "supervisor exit when it cannot start ($start_case)"
  assert_file "$TEST_TMP/start-$start_case.done"
  assert_eq "EXIT=125" "$(<"$TEST_TMP/start-$start_case.done")" "supervisor marker when it cannot start ($start_case)"
  [ ! -e "$TEST_TMP/start-$start_case.sh" ] || fail "the supervisor left its script file ($start_case)"
done
grep -Fq "lane: the supervisor could not read its prompt file $TEST_TMP/no-such.prompt; exit 125" \
  "$TEST_TMP/start-prompt.log" || fail "the supervisor did not log its unreadable prompt"
grep -Fq "lane: the supervisor could not enter $TEST_TMP/no-such-dir; exit 125" "$TEST_TMP/start-checkout.log" ||
  fail "the supervisor did not log its missing checkout"

echo "test: a codex model at capacity is waited out, then codex continues"
rm -f "$LANE_CAPTURE/codex.calls"
CODEX_FAKE_CAPACITY=1 LANE_CODEX_CAPACITY_RETRY_S=0 "$LANE" run capacity --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/capacity.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/capacity.done")" "the lane outlasted a capacity error"
assert_eq "2" "$(<"$LANE_CAPTURE/codex.calls")" "codex started again after the capacity error"
grep -Fq "A provider capacity error stopped your previous attempt" "$LANE_CAPTURE/codex.args" || fail "the second start lacks the note to continue"

echo "test: a codex model that stays at capacity exits 85"
rm -f "$LANE_CAPTURE/codex.calls"
CODEX_FAKE_CAPACITY=99 LANE_CODEX_CAPACITY_RETRY_S=0 LANE_CODEX_CAPACITY_WAIT_S=0 "$LANE" run capacitygone --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/capacitygone.done"
assert_eq "EXIT=85" "$(<"$LANE_HOME/capacitygone.done")" "capacity that stays exits 85"
rm -f "$LANE_CAPTURE/codex.calls"

echo "test: a reader that closes early cannot abort a resume half-done"
# Before the fix, SIGPIPE killed resume after it archived the log and before it removed the old marker or launched.
"$LANE" resume failure --no-note | head -1 >/dev/null
wait_for_file "$LANE_HOME/failure.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/failure.done")" "resume relaunched despite a closed reader"

echo "test: a reader that closes early cannot abort a run half-done"
# Before the fix, git worktree add exited 141 on the closed pipe after it had made the branch, and run died under set -e.
"$LANE" run closedrun --repo "$REPO" --brief "$BRIEF" --worker fake 2>&1 | head -1 >/dev/null
wait_for_file "$LANE_HOME/closedrun.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/closedrun.done")" "run launched despite a closed reader"

echo "test: run reports RUNNING and creates its isolated worktree"
run_output=$(LANE_FAKE_HOLD="$TEST_TMP/release-first" "$LANE" run first --repo "$REPO" --brief "$BRIEF" --worker fake --keep-checkout)
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

echo "test: state prints one lane's ls state as JSON, NONE for a lane with no record"
first_pid=$(json_value "$LANE_HOME/first.json" pid)
first_started_epoch=$(json_value "$LANE_HOME/first.json" started_epoch)
assert_eq "{\"name\": \"first\", \"state\": \"DONE:0\", \"pid\": $first_pid, \"started_epoch\": $first_started_epoch}" \
  "$("$LANE" state first)" "state of a finished lane"
assert_eq '{"name": "nosuchlane", "state": "NONE", "pid": null, "started_epoch": null}' "$("$LANE" state nosuchlane)" \
  "state of an unknown lane"
if "$LANE" state first extra >/dev/null 2>&1; then fail "state accepted two names"; fi

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
LANE_NICE= "$LANE" run hang --repo "$REPO" --brief "$BRIEF" --worker fake-hang >/dev/null
hang_metadata="$LANE_HOME/hang.json"
hang_pid=$(json_value "$hang_metadata" pid)
hang_started_epoch=$(json_value "$hang_metadata" started_epoch)
case "$hang_started_epoch" in "" | *[!0-9]*) fail "worker metadata omitted started_epoch" ;; esac
kill -0 -- "-$hang_pid" 2>/dev/null || fail "real worker process group is not alive"
# /bin/ps: FAKE_BIN's ps answers with a start time whatever -o asks for.
own_nice=$(/bin/ps -o nice= -p $$ | tr -d ' ')
assert_eq "$((own_nice + 10 > 20 ? 20 : own_nice + 10))" "$(/bin/ps -o nice= -p "$hang_pid" | tr -d ' ')" \
  "a worker runs 10 nicer than lane by default"
# 2026-11-07: a `pkill -f` pattern matched "failed" in a comment of the supervisor script, which bash -c carried in
# every supervisor's arguments with the whole prompt, and killed every lane supervisor on the Mac.
wait_for_absent "$LANE_HOME/hang.supervisor"
wait_for_absent "$LANE_HOME/hang.prompt"
hang_args=$(/bin/ps -o args= -p "$hang_pid" | "$ROOT/bin/redact-env")
[ -n "$hang_args" ] || fail "no arguments for supervisor $hang_pid"
for word in retire_out capacity_delay failed "Do the fake task"; do
  case "$hang_args" in *"$word"*) fail "the supervisor's arguments carry script or prompt text: $word" ;; esac
done
set_started_epoch "$hang_metadata" "$((hang_started_epoch + 1))"
assert_eq "DEAD" "$(state_for hang)" "forged worker identity"
assert_eq "\"DEAD\"" "$("$LANE" state hang | python3 -c 'import json, sys; print(json.dumps(json.load(sys.stdin)["state"]))')" \
  "state's forged worker identity"
kill -0 -- "-$hang_pid" 2>/dev/null || fail "forged identity check signalled the real worker"
set_started_epoch "$hang_metadata" "$hang_started_epoch"
assert_eq "RUNNING" "$(state_for hang)" "real worker identity"
assert_eq "{\"name\": \"hang\", \"state\": \"RUNNING\", \"pid\": $hang_pid, \"started_epoch\": $hang_started_epoch}" \
  "$("$LANE" state hang)" "state of a running lane"
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

echo "test: stop reaches a group that a command under the worker leads"
# 2026-11-07: a lane's `timeout 2400 ... ratchet.py sweep` led its own group (timeout(1) setpgid()s) and ran on
# after `lane stop`.
LANE_FAKE_ESCAPE="$TEST_TMP/escaped.pid" "$LANE" run escape --repo "$REPO" --brief "$BRIEF" --worker fake-hang --no-worktree >/dev/null
wait_for_file "$TEST_TMP/escaped.pid" 300
escaped_pid=$(<"$TEST_TMP/escaped.pid")
ESCAPED_PID=$escaped_pid
attempts=0
while [ "$(/bin/ps -o pgid= -p "$escaped_pid" | tr -d ' ')" != "$escaped_pid" ] && [ "$attempts" -lt 100 ]; do
  sleep 0.1
  attempts=$((attempts + 1))
done
assert_eq "$escaped_pid" "$(/bin/ps -o pgid= -p "$escaped_pid" | tr -d ' ')" "the fake command leads its own group"
[ "$escaped_pid" != "$(json_value "$LANE_HOME/escape.json" pid)" ] || fail "the fake command is the worker itself"
"$LANE" stop escape >"$TEST_TMP/escape-stop.out"
grep -Fq "lane: signalled process group $escaped_pid, which a command under the worker leads" "$TEST_TMP/escape-stop.out" ||
  fail "stop did not name the escaped group"
attempts=0
while kill -0 "$escaped_pid" 2>/dev/null && [ "$attempts" -lt 50 ]; do
  sleep 0.1
  attempts=$((attempts + 1))
done
kill -0 "$escaped_pid" 2>/dev/null && fail "stop left running the group that a command under the worker leads"
ESCAPED_PID=""

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
assert_eq "Do the fake task." "$(head -1 "$LANE_HOME/first.log")" "no-note prompt"
grep -Fq "$BRIEF_REAL" "$LANE_HOME/first.log" && fail "no-note prompt names the brief path"
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

echo "test: a resume refused by its name's launch lock leaves the lane running and its note unclaimed"
# The resume claimed its note and stopped the lane before launch_worker took the lock, so the refusal left it DEAD.
LANE_FAKE_HOLD="$TEST_TMP/release-lockedresume" "$LANE" resume first --no-note >/dev/null
lockedresume_pid=$(json_value "$LANE_HOME/first.json" pid)
mkdir "$LANE_HOME/.launch-first.lock"
printf '%s\n' "$$" >"$LANE_HOME/.launch-first.lock/pid"
printf '%s\n' 'Note for the refused resume.' >"$TEST_TMP/lockednote.txt"
if lockedresume_output=$("$LANE" resume first --note "$TEST_TMP/lockednote.txt" 2>&1); then
  fail "a resume ran while another launch of its name held the lock"
fi
grep -Fq "another launch of first holds $LANE_HOME/.launch-first.lock (pid $$)" <<<"$lockedresume_output" ||
  fail "the refused resume did not name the lock and its holder: $lockedresume_output"
assert_eq "RUNNING" "$(state_for first)" "a lane whose resume was refused"
assert_eq "$lockedresume_pid" "$(json_value "$LANE_HOME/first.json" pid)" "the refused resume's lane pid"
assert_no_file "$LANE_HOME/first.resume-note.md"
assert_no_file "$LANE_HOME/first.resume-note.consumed-4.md"
rm "$LANE_HOME/.launch-first.lock/pid"
rmdir "$LANE_HOME/.launch-first.lock"
touch "$TEST_TMP/release-lockedresume"
wait_for_file "$LANE_HOME/first.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/first.done")" "the held lane after the refused resume"

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

echo "test: ls lists every lane once in metadata order, across row batches, and fails loud on bad metadata"
expected_names=""
for metadata in "$LANE_HOME"/*.json; do
  expected_names+="$(basename "$metadata" .json)"$'\n'
done
[ "$(printf '%s' "$expected_names" | wc -l)" -gt 8 ] || fail "too few lanes to cross an ls row batch"
assert_eq "$(printf '%s' "$expected_names")" "$("$LANE" ls | tail -n +2 | awk '{ print $1 }')" "ls rows"
printf '%s\n' '{"name": "broken"}' >"$LANE_HOME/broken.json"
if ls_error=$("$LANE" ls 2>&1 >/dev/null); then fail "ls accepted metadata without a pid"; fi
grep -Fq "invalid metadata: $LANE_HOME/broken.json" <<<"$ls_error" || fail "ls did not name the bad metadata: $ls_error"
rm "$LANE_HOME/broken.json"

echo "test: review attaches the lane's cache result, not an unchanged tracked report made newest by mtime"
"$LANE" run rvcache --repo "$REPO" --brief "$BRIEF" --worker fake --keep-checkout >/dev/null
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
"$LANE" run rvown --repo "$REPO" --brief "$BRIEF" --worker fake --keep-checkout >/dev/null
wait_for_file "$LANE_HOME/rvown.done"
RVOWN_WT="$REPO_REAL/.claude/worktrees/codex-rvown"
mkdir -p "$RVOWN_WT/docs/audit/topic"
printf '%s\n' mine >"$RVOWN_WT/docs/audit/topic/new-report.md"
LLMX_CAPTURE_NAME=rvown "$LANE" review rvown --out "$TEST_TMP/rvown.md" >/dev/null
grep -Fxq "$RVOWN_WT/docs/audit/topic/new-report.md" "$LANE_CAPTURE/rvown.args" || fail "review omitted the lane's own report"

echo "test: review patch diffs against the checkout base and names commits made after it"
"$LANE" run rvcommit --repo "$REPO" --brief "$BRIEF" --worker fake --keep-checkout >/dev/null
wait_for_file "$LANE_HOME/rvcommit.done"
RVCOMMIT_WT="$REPO_REAL/.claude/worktrees/codex-rvcommit"
printf '%s\n' committed-lane-sentinel >"$RVCOMMIT_WT/committed.txt"
git -C "$RVCOMMIT_WT" add committed.txt
git -C "$RVCOMMIT_WT" -c user.email=t@t -c user.name=t commit -q -m "[wip] Auto-checkpoint lane work"
rvcommit_stderr="$TEST_TMP/rvcommit.stderr"
LLMX_CAPTURE_NAME=rvcommit "$LANE" review rvcommit --out "$TEST_TMP/rvcommit.md" >/dev/null 2>"$rvcommit_stderr"
grep -Fq '+committed-lane-sentinel' "$LANE_HOME/rvcommit.patch" || fail "review patch dropped the committed lane change"
grep -Fq '[wip] Auto-checkpoint lane work' "$LANE_HOME/rvcommit.patch" || fail "patch header did not name the commit after base"
grep -Fq '[wip] Auto-checkpoint lane work' "$rvcommit_stderr" || fail "stderr did not name the commit after base"

echo "test: review without a recorded checkout base fails loud"
"$LANE" run rvnobase --repo "$REPO" --brief "$BRIEF" --worker fake --keep-checkout >/dev/null
wait_for_file "$LANE_HOME/rvnobase.done"
python3 -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d.pop("checkout_base",None); json.dump(d,open(p,"w"))' "$LANE_HOME/rvnobase.json"
if LLMX_CAPTURE_NAME=rvnobase "$LANE" review rvnobase --out "$TEST_TMP/rvnobase.md" >/dev/null 2>"$TEST_TMP/rvnobase.stderr"; then
  fail "review without a checkout base succeeded"
fi
grep -Fq 'no recorded checkout base' "$TEST_TMP/rvnobase.stderr" || fail "missing-base failure did not name the cause"

echo "test: review with no report fails loud in header and prompt"
"$LANE" run rvnone --repo "$REPO" --brief "$BRIEF" --worker fake --keep-checkout >/dev/null
wait_for_file "$LANE_HOME/rvnone.done"
rv_stdout=$(LLMX_CAPTURE_NAME=rvnone "$LANE" review rvnone --out "$TEST_TMP/rvnone.md")
grep -Fxq '# no lane report found' "$LANE_HOME/rvnone.patch" || fail "patch header omitted no-report note"
grep -Fq 'No lane report was found' "$LANE_CAPTURE/rvnone.args" || fail "prompt omitted no-report sentence"
assert_eq "2" "$(grep -c '^-f$' "$LANE_CAPTURE/rvnone.args")" "no-report file arguments (patch + brief)"
grep -Fxq "lane: report: none" <<<"$rv_stdout" || fail "review did not print report: none"

echo "test: a finished worktree lane is harvested, then its worktree and branch are removed"
LANE_FAKE_HOLD="$TEST_TMP/release-retire1" "$LANE" run retire1 --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
RETIRE_WT="$REPO_REAL/.claude/worktrees/codex-retire1"
printf '%s\n' "lane edit" >>"$RETIRE_WT/tracked.txt"
mkdir -p "$RETIRE_WT/.claude/cache"
printf '%s\n' "**Verdict:** DONE" >"$RETIRE_WT/.claude/cache/retire1-result.md"
# A directory a valid CACHEDIR.TAG marks (cargo's target/) is rederivable and skipped; a wrong signature is no tag.
mkdir -p "$REPO_REAL/.git/info" "$RETIRE_WT/target/debug" "$RETIRE_WT/wrongtag"
printf '%s\n' "/target/" "/wrongtag/" >>"$REPO_REAL/.git/info/exclude"
printf '%s\n' "Signature: 8a477f597d28d172789f06886806bc55" "# cargo" >"$RETIRE_WT/target/CACHEDIR.TAG"
printf '%s\n' "build output" >"$RETIRE_WT/target/debug/app"
printf '%s\n' "Signature: 00000000000000000000000000000000" >"$RETIRE_WT/wrongtag/CACHEDIR.TAG"
printf '%s\n' "lane notes" >"$RETIRE_WT/wrongtag/notes.txt"
# A target dir cargo built into without tagging it (it existed before cargo ran) still holds cargo's
# .rustc_info.json; arena's env-waste-rb1 refused at the 1 GiB cap on such a 2 GiB target/ (2026-11-07).
mkdir -p "$RETIRE_WT/untagged-target/debug"
printf '%s\n' "/untagged-target/" >>"$REPO_REAL/.git/info/exclude"
printf '%s\n' '{"rustc_fingerprint":1,"outputs":{}}' >"$RETIRE_WT/untagged-target/.rustc_info.json"
printf '%s\n' "build output" >"$RETIRE_WT/untagged-target/debug/app"
touch "$TEST_TMP/release-retire1"
wait_for_file "$LANE_HOME/retire1.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/retire1.done")" "retired lane marker"
grep -q '^CHECKOUT=retired ' "$LANE_HOME/retire1.checkout-state" || fail "retire1 was not retired: $(<"$LANE_HOME/retire1.checkout-state")"
[ ! -e "$RETIRE_WT" ] || fail "retired worktree still exists"
git -C "$REPO" show-ref --verify --quiet refs/heads/codex/retire1 && fail "retired lane left its branch"
RETIRE_HARVEST=$(sed -n '1s/^CHECKOUT=retired //p' "$LANE_HOME/retire1.checkout-state")
grep -Fq '+lane edit' "$RETIRE_HARVEST/lane.patch" || fail "harvest patch lacks the lane's edit"
assert_eq "**Verdict:** DONE" "$(<"$RETIRE_HARVEST/cache/retire1-result.md")" "harvested result"
gzip -dc "$RETIRE_HARVEST/run.log.gz" | grep -Fxq hi || fail "harvest lacks the lane log"
assert_file "$RETIRE_HARVEST/brief.md"
[ ! -e "$RETIRE_HARVEST/ignored/target" ] || fail "harvest copied a CACHEDIR.TAG cache"
[ ! -e "$RETIRE_HARVEST/ignored/untagged-target" ] || fail "harvest copied an untagged cargo target dir"
assert_eq "lane notes" "$(<"$RETIRE_HARVEST/ignored/wrongtag/notes.txt")" "a wrong-signature tag is harvested"
python3 - "$RETIRE_HARVEST/MANIFEST.json" <<'PY'
import json
import sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
assert sorted(manifest["tagged_caches_skipped"]) == ["target", "untagged-target"], manifest["tagged_caches_skipped"]
# The harvest says what ran and how it ended once a reap removes the ledger and the marker.
assert manifest["exit_code"] == 0, manifest["exit_code"]
assert "lane.json" in manifest["files"], sorted(manifest["files"])
PY
cmp -s "$LANE_HOME/retire1.json" "$RETIRE_HARVEST/lane.json" || fail "the harvest's lane.json is not the ledger"
assert_eq "ret" "$(dirty_for retire1)" "ls marks a retired lane"
# The patch reproduces the lane's tree on the base it was cut from.
git -C "$REPO" worktree add -q --detach "$TEST_TMP/replay" HEAD
git -C "$TEST_TMP/replay" apply --binary "$RETIRE_HARVEST/lane.patch"
grep -Fxq "lane edit" "$TEST_TMP/replay/tracked.txt" || fail "harvest patch does not replay the edit"
git -C "$REPO" worktree remove --force "$TEST_TMP/replay"

echo "test: a retired lane reviews from its harvest and refuses resume"
LLMX_CAPTURE_NAME=retire1 "$LANE" review retire1 --out "$TEST_TMP/retire1.md" >/dev/null
grep -Fq '# harvest: ' "$LANE_HOME/retire1.patch" || fail "harvest review patch lacks its header"
grep -Fq '+lane edit' "$LANE_HOME/retire1.patch" || fail "harvest review patch lacks the edit"
grep -Fxq "$RETIRE_HARVEST/cache/retire1-result.md" "$LANE_CAPTURE/retire1.args" || fail "harvest review omitted the result"
if resume_error=$("$LANE" resume retire1 --no-note 2>&1); then fail "resume accepted a retired lane"; fi
grep -Fq "was retired" <<<"$resume_error" || fail "resume did not name the retirement: $resume_error"
reap_output=$("$LANE" reap retire1 --force)
grep -Fq "harvests stay in" <<<"$reap_output" || fail "reap of a retired lane did not finish"
assert_no_file "$LANE_HOME/retire1.json"
[ -d "$RETIRE_HARVEST" ] || fail "reap removed the harvest"

echo "test: a failed lane keeps its worktree"
LANE_FAKE_HOLD="$TEST_TMP/release-retirefail" "$LANE" run retirefail --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
printf '%s\n' "unfinished" >>"$REPO_REAL/.claude/worktrees/codex-retirefail/tracked.txt"
python3 - "$LANE_HOME/retirefail.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["checkout"] == "worktree" and data["keep_checkout"] is False and len(data["checkout_base"]) == 40, data
PY
"$LANE" stop retirefail >/dev/null
[ -d "$REPO_REAL/.claude/worktrees/codex-retirefail" ] || fail "a stopped lane lost its worktree"
reap_output=$("$LANE" reap retirefail --force)
grep -q '^CHECKOUT=retired ' <<<"$reap_output" || fail "reap of a stopped lane did not harvest it"
grep -Fq '+unfinished' "$(latest_harvest_of retirefail)/lane.patch" || fail "stopped lane's harvest lacks its edit"
python3 - "$(latest_harvest_of retirefail)" <<'PY'
import json
import sys
from pathlib import Path
harvest = Path(sys.argv[1])
assert json.loads((harvest / "MANIFEST.json").read_text())["exit_code"] is None, "a stopped lane has no exit code"
assert json.loads((harvest / "lane.json").read_text())["name"] == "retirefail"
PY
assert_file "$(latest_harvest_of retirefail)/run.log.gz"
[ ! -e "$REPO_REAL/.claude/worktrees/codex-retirefail" ] || fail "reap left the stopped lane's worktree"

echo "test: a locked worktree is kept, with no harvest, until it is unlocked"
LANE_FAKE_HOLD="$TEST_TMP/release-retirelock" "$LANE" run retirelock --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
printf '%s\n' "unfinished" >>"$REPO_REAL/.claude/worktrees/codex-retirelock/tracked.txt"
"$LANE" stop retirelock >/dev/null
git -C "$REPO_REAL" worktree lock --reason "a hand job" "$REPO_REAL/.claude/worktrees/codex-retirelock"
reap_output=$("$LANE" reap retirelock --force 2>&1) || true
grep -Fq 'CHECKOUT=kept locked: a hand job' <<<"$reap_output" || fail "reap of a locked worktree did not name the lock: $reap_output"
[ -z "$(latest_harvest_of retirelock 2>/dev/null)" ] || fail "a locked worktree was harvested"
[ -d "$REPO_REAL/.claude/worktrees/codex-retirelock" ] || fail "a locked worktree was removed"
git -C "$REPO_REAL" worktree unlock "$REPO_REAL/.claude/worktrees/codex-retirelock"
reap_output=$("$LANE" reap retirelock --force)
grep -q '^CHECKOUT=retired ' <<<"$reap_output" || fail "reap after the unlock did not harvest: $reap_output"
grep -Fq '+unfinished' "$(latest_harvest_of retirelock)/lane.patch" || fail "the unlocked lane's harvest lacks its edit"

echo "test: a process inside the checkout keeps it"
LANE_RETIRE_SETTLE_S=1 LANE_FAKE_HOLD="$TEST_TMP/release-retirebusy" \
  "$LANE" run retirebusy --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
(cd "$REPO_REAL/.claude/worktrees/codex-retirebusy" && exec sleep 60) &
BUSY_PID=$!
touch "$TEST_TMP/release-retirebusy"
wait_for_file "$LANE_HOME/retirebusy.done" 300
grep -q "^CHECKOUT=kept busy: pid $BUSY_PID (sleep: cwd)" "$LANE_HOME/retirebusy.checkout-state" ||
  fail "busy checkout was not kept: $(<"$LANE_HOME/retirebusy.checkout-state")"
[ -d "$REPO_REAL/.claude/worktrees/codex-retirebusy" ] || fail "busy checkout was removed"
kill "$BUSY_PID"
wait "$BUSY_PID" 2>/dev/null || true
"$LANE" reap retirebusy --force >/dev/null
python3 - "$(latest_harvest_of retirebusy)" <<'PY'
import json
import sys
from pathlib import Path
harvest = Path(sys.argv[1])
assert json.loads((harvest / "MANIFEST.json").read_text())["exit_code"] == 0, "a reaped DONE:0 lane says exit 0"
assert json.loads((harvest / "lane.json").read_text())["name"] == "retirebusy"
PY

echo "test: a reap of a kept checkout its newest harvest already holds writes no second harvest"
# arena's autoland snapshots a --keep-checkout lane with lane-retire's harvest function and keeps the
# checkout; a later reap of the unchanged checkout wrote a byte-identical second stamp, which autoland
# took for new work (three reaped superseded lanes restarted two rebase lanes, 2026-11-08).
LANE_FAKE_HOLD="$TEST_TMP/release-retiresnap" "$LANE" run retiresnap --repo "$REPO" --brief "$BRIEF" --worker fake \
  --keep-checkout >/dev/null
SNAP_WT="$REPO_REAL/.claude/worktrees/codex-retiresnap"
printf '%s\n' "snapshot edit" >>"$SNAP_WT/tracked.txt"
mkdir -p "$SNAP_WT/.claude/cache"
printf '%s\n' "**Verdict:** done" >"$SNAP_WT/.claude/cache/retiresnap-result.md"
touch "$TEST_TMP/release-retiresnap"
wait_for_file "$LANE_HOME/retiresnap.done"
grep -q '^CHECKOUT=kept launched with --keep-checkout' "$LANE_HOME/retiresnap.checkout-state" ||
  fail "the kept lane was not kept: $(<"$LANE_HOME/retiresnap.checkout-state")"
snapshot_kept() {
  python3 - "$(dirname "$LANE")/lane-retire" "$1" "$SNAP_WT" "$REPO_REAL" "$LANE_HOME" <<'PY'
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
api = runpy.run_path(sys.argv[1], run_name="lane_retire_snapshot")
# As arena's autoland.snapshot_kept builds them, from the lane's ledger.
meta = json.loads((Path(sys.argv[5]) / f"{sys.argv[2]}.json").read_text())
args = SimpleNamespace(name=sys.argv[2], mode="worktree", checkout=sys.argv[3], repo=sys.argv[4],
                       base=meta.get("checkout_base") or meta.get("base", ""), branch=meta.get("branch", ""),
                       harvest_root=sys.argv[5], allow_root=[], log="", brief="", exit_code=0,
                       keep="snapshot", reap=False, meta="", done="")
print(api["harvest"](args, Path(sys.argv[3]))[0])
PY
}
SNAP_FIRST=$(snapshot_kept retiresnap)
[ -d "$SNAP_FIRST" ] || fail "the snapshot wrote no harvest: $SNAP_FIRST"
assert_eq "$SNAP_FIRST" "$(snapshot_kept retiresnap)" "an unchanged checkout's second snapshot"
printf '%s\n' "**Verdict:** done, rewritten" >"$SNAP_WT/.claude/cache/retiresnap-result.md"
SNAP_SECOND=$(snapshot_kept retiresnap)
[ "$SNAP_SECOND" != "$SNAP_FIRST" ] || fail "a changed result file reused the earlier harvest"
reap_output=$("$LANE" reap retiresnap --force 2>&1)
grep -Fxq "CHECKOUT=retired $SNAP_SECOND" <<<"$reap_output" || fail "the reap did not retire into the newest harvest: $reap_output"
assert_eq "2" "$(find "$LANE_HOME/retiresnap.harvest" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" "harvests after the reap"
[ ! -e "$SNAP_WT" ] || fail "the reaped checkout still exists"

echo "test: a reader of a moment inside the checkout does not keep it"
LANE_RETIRE_SETTLE_S=60 LANE_FAKE_HOLD="$TEST_TMP/release-retireread" \
  "$LANE" run retireread --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
(cd "$REPO_REAL/.claude/worktrees/codex-retireread" && exec sleep 4) &
READ_PID=$!
touch "$TEST_TMP/release-retireread"
wait_for_file "$LANE_HOME/retireread.done" 900
grep -q '^CHECKOUT=retired ' "$LANE_HOME/retireread.checkout-state" ||
  fail "a passing reader kept the checkout: $(<"$LANE_HOME/retireread.checkout-state")"
wait "$READ_PID" 2>/dev/null || true
"$LANE" reap retireread --force >/dev/null

echo "test: an unmerged path with a conflict marker keeps the checkout and is named; a resolved one is staged"
LANE_FAKE_HOLD="$TEST_TMP/release-retireumg" "$LANE" run retireumg --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
UMG_WT="$REPO_REAL/.claude/worktrees/codex-retireumg"
printf '<<<<<<< ours\nmine\n=======\ntheirs\n>>>>>>> theirs\n' > "$UMG_WT/conflicted.txt"
printf 'resolved\n=======\n' > "$UMG_WT/resolved.txt"
for umg_path in conflicted.txt resolved.txt; do
  umg_blob=$(git -C "$UMG_WT" hash-object -w "$UMG_WT/$umg_path")
  printf '100644 %s 1\t%s\n100644 %s 2\t%s\n100644 %s 3\t%s\n' \
    "$umg_blob" "$umg_path" "$umg_blob" "$umg_path" "$umg_blob" "$umg_path" | git -C "$UMG_WT" update-index --index-info
  [ "$(git -C "$UMG_WT" status --porcelain=v1 -- "$umg_path" | cut -c1-2)" = UU ] || fail "$umg_path is not unmerged"
done
touch "$TEST_TMP/release-retireumg"
wait_for_file "$LANE_HOME/retireumg.done"
grep -Fxq "CHECKOUT=kept unmerged paths (resolve each, then git add it): conflicted.txt" \
  "$LANE_HOME/retireumg.checkout-state" ||
  fail "the marked path alone was not named: $(<"$LANE_HOME/retireumg.checkout-state")"
[ -d "$UMG_WT" ] || fail "an unmerged checkout was removed"
[ "$(git -C "$UMG_WT" status --porcelain=v1 -- resolved.txt | cut -c1-2)" = "A " ] || fail "the resolved path was not staged"
printf 'resolved\n' > "$UMG_WT/conflicted.txt"
"$LANE" reap retireumg --force >/dev/null
grep -q '^+++ b/conflicted.txt' "$(latest_harvest_of retireumg)/lane.patch" || fail "the harvest lost the fixed conflict"
grep -q '^+++ b/resolved.txt' "$(latest_harvest_of retireumg)/lane.patch" || fail "the harvest lost the staged path"

echo "test: a change staged, then reverted in the file, is no change"
LANE_FAKE_HOLD="$TEST_TMP/release-retirestg" "$LANE" run retirestg --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
STG_WT="$REPO_REAL/.claude/worktrees/codex-retirestg"
cp "$STG_WT/tracked.txt" "$TEST_TMP/tracked-retirestg"
printf 'staged\n' >> "$STG_WT/tracked.txt"
git -C "$STG_WT" add tracked.txt
cp "$TEST_TMP/tracked-retirestg" "$STG_WT/tracked.txt"
printf 'kept\n' > "$STG_WT/stg-new.txt"
[ "$(git -C "$STG_WT" status --porcelain=v1 -- tracked.txt | cut -c1-2)" = MM ] || fail "the fixture is not staged, then reverted"
touch "$TEST_TMP/release-retirestg"
wait_for_file "$LANE_HOME/retirestg.done"
grep -q '^CHECKOUT=retired ' "$LANE_HOME/retirestg.checkout-state" ||
  fail "a staged, then reverted path kept the checkout: $(<"$LANE_HOME/retirestg.checkout-state")"
grep -q 'stg-new.txt' "$(latest_harvest_of retirestg)/lane.patch" || fail "the harvest lost the lane's new file"
if grep -q 'tracked.txt' "$(latest_harvest_of retirestg)/lane.patch"; then fail "the harvest carried an index-only change"; fi

echo "test: a detached HEAD or a merge commit keeps the worktree and its branch"
LANE_FAKE_HOLD="$TEST_TMP/release-retiredet" "$LANE" run retiredet --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
DET_WT="$REPO_REAL/.claude/worktrees/codex-retiredet"
git -C "$DET_WT" commit -q --allow-empty -m "on the branch"
git -C "$DET_WT" -c advice.detachedHead=false checkout -q --detach HEAD~1
touch "$TEST_TMP/release-retiredet"
wait_for_file "$LANE_HOME/retiredet.done"
grep -Fq "CHECKOUT=kept HEAD is detached, not refs/heads/codex/retiredet" "$LANE_HOME/retiredet.checkout-state" ||
  fail "a detached HEAD was retired: $(<"$LANE_HOME/retiredet.checkout-state")"
[ -d "$DET_WT" ] || fail "a detached checkout was removed"
git -C "$REPO" show-ref --verify --quiet refs/heads/codex/retiredet || fail "a detached checkout lost its branch"
git -C "$DET_WT" switch -q codex/retiredet
side=$(git -C "$DET_WT" commit-tree "HEAD^{tree}" -p HEAD -m side)
merge=$(git -C "$DET_WT" commit-tree "HEAD^{tree}" -p HEAD -p "$side" -m merge)
git -C "$DET_WT" update-ref refs/heads/codex/retiredet "$merge"
if reap_output=$("$LANE" reap retiredet --force 2>&1); then fail "reap retired a lane with a merge commit"; fi
grep -Fq "merge commits since the lane base" <<<"$reap_output" || fail "merge keep reason missing: $reap_output"
[ -d "$DET_WT" ] || fail "a merged checkout was removed"
git -C "$DET_WT" update-ref refs/heads/codex/retiredet HEAD~2
"$LANE" reap retiredet --force >/dev/null
[ ! -e "$DET_WT" ] || fail "reap left the restored checkout"

echo "test: a repo checkout hook builds, seeds, rechecks and retires its lanes' checkouts"
HOOK="$TEST_TMP/lane-checkout-hook"
cat >"$HOOK" <<'EOF'
#!/usr/bin/env bash
# Test hook: a plain clone at the base, the seeds applied, two ignored inputs provided, settings in
# .git/lane-checkout.json.
set -eu
if [ "$1" = --verify ]; then
  printf '%s\n' "${LANE_NOTE:-}" >"$LANE_CAPTURE/hook.verify-note"
  [ "$(cat "$2/.git/lane-main-base")" = "$3" ] || { echo "hook: cut from another base, not $3" >&2; exit 87; }
  exit 0
fi
git clone -q --no-local --no-checkout "$LANE_REPO" "$1"
git -C "$1" -c advice.detachedHead=false checkout -q --detach "$2"
printf '%s\n' "$2" >"$1/.git/lane-main-base"
mkdir -p "$1/.claude/cache" "$1/.git/info" "$1/inputs"
if [ -n "$LANE_SEED_PATCH" ]; then git -C "$1" apply --binary "$LANE_SEED_PATCH"; fi
while IFS= read -r seed; do
  if [ -n "$seed" ]; then cp "$seed" "$1/.claude/cache/"; fi
done <<<"$LANE_SEED_FILES"
printf '%s\n' "/inputs/" >>"$1/.git/info/exclude"
printf '%s\n' "input the lane leaves alone" >"$1/inputs/same.txt"
printf '%s\n' "input the lane edits" >"$1/inputs/edited.txt"
same=$(shasum -a 256 "$1/inputs/same.txt" | cut -d' ' -f1)
edited=$(shasum -a 256 "$1/inputs/edited.txt" | cut -d' ' -f1)
printf '{"env": {"HOOK_TEST_VAR": "from-hook"}, "provided": {"inputs/same.txt": "%s", "inputs/edited.txt": "%s"}, "opencode_permissions": [{"action": "shell", "resource": "*hook-denied*", "effect": "deny"}]}\n' \
  "$same" "$edited" >"$1/.git/lane-checkout.json"
EOF
chmod +x "$HOOK"
git -C "$REPO" config lane.checkout "$HOOK"
if "$LANE" run hookinline --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null 2>&1; then
  fail "a codex lane ran --no-worktree in a repo with a checkout hook"
fi
LANE_FAKE_HOLD="$TEST_TMP/release-hook1" "$LANE" run hook1 --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
HOOK1="$LANE_HOME/checkouts/hook1"
assert_eq "hook" "$(json_value "$LANE_HOME/hook1.json" checkout)" "recorded checkout mode"
assert_eq "$(git -C "$HOOK1" rev-parse HEAD)" "$(<"$HOOK1/.git/lane-checkout-base")" "lane-owned checkout base"
printf '%s\n' "hook edit" >>"$HOOK1/tracked.txt"
printf '%s\n' "hook notes" >"$HOOK1/.claude/cache/hook1-notes.md"
printf '%s\n' "lane change" >>"$HOOK1/inputs/edited.txt"
touch "$TEST_TMP/release-hook1"
wait_for_file "$LANE_HOME/hook1.done"
grep -q '^CHECKOUT=retired ' "$LANE_HOME/hook1.checkout-state" || fail "hook checkout was not retired: $(<"$LANE_HOME/hook1.checkout-state")"
[ ! -e "$HOOK1" ] || fail "retired hook checkout still exists"
HOOK1_HARVEST=$(latest_harvest_of hook1)
grep -Fq '+hook edit' "$HOOK1_HARVEST/lane.patch" || fail "hook harvest lacks the edit"
# A provided input the lane left alone is named in MANIFEST.json, not copied; one it edited is its work.
assert_no_file "$HOOK1_HARVEST/ignored/inputs/same.txt"
grep -Fxq "lane change" "$HOOK1_HARVEST/ignored/inputs/edited.txt" || fail "harvest lost the lane's edit of an input"
python3 - "$HOOK1_HARVEST/MANIFEST.json" <<'PY' || fail "MANIFEST does not name the unchanged input"
import json
import sys
unchanged = json.load(open(sys.argv[1], encoding="utf-8"))["provided_unchanged"]
sys.exit(0 if list(unchanged) == ["inputs/same.txt"] and len(unchanged["inputs/same.txt"]) == 64 else 1)
PY

echo "test: seeds start a new hook lane from a harvest, and a kept checkout survives its exit"
LANE_FAKE_HOLD="$TEST_TMP/release-hook2" "$LANE" run hook2 --repo "$REPO" --brief "$BRIEF" --worker fake --keep-checkout \
  --seed-patch "$HOOK1_HARVEST/lane.patch" --seed-file "$HOOK1_HARVEST/cache/hook1-notes.md" >/dev/null
HOOK2="$LANE_HOME/checkouts/hook2"
grep -Fxq "hook edit" "$HOOK2/tracked.txt" || fail "seed patch was not applied"
assert_eq "hook notes" "$(<"$HOOK2/.claude/cache/hook1-notes.md")" "seed file"
touch "$TEST_TMP/release-hook2"
wait_for_file "$LANE_HOME/hook2.done"
grep -q '^CHECKOUT=kept launched with --keep-checkout' "$LANE_HOME/hook2.checkout-state" || fail "kept checkout state"
[ -d "$HOOK2" ] || fail "--keep-checkout lost the checkout"
if "$LANE" run hook2 --repo "$REPO" --brief "$BRIEF" --worker fake --seed-patch "$HOOK1_HARVEST/lane.patch" >/dev/null 2>&1; then
  fail "seeds were applied to an existing checkout"
fi
if "$LANE" run hook2 --repo "$REPO" --brief "$BRIEF" --worker fake --base HEAD~0 --keep-checkout >/dev/null 2>&1; then
  : # same base: the hook accepts the reuse
else
  fail "the hook refused a reuse at the same base"
fi
wait_for_file "$LANE_HOME/hook2.done"
git -C "$REPO" commit -q --allow-empty -m "moved main"
if "$LANE" run hook2 --repo "$REPO" --brief "$BRIEF" --worker fake --base HEAD >/dev/null 2>&1; then
  fail "the hook accepted a reuse at a different base"
fi
"$LANE" reap hook2 --force >/dev/null
[ ! -e "$HOOK2" ] || fail "reap left the hook checkout"

echo "test: an opencode lane in a hook checkout gets the hook's env and guard rules"
"$LANE" run ochook --repo "$REPO" --brief "$BRIEF" --worker opencode --keep-checkout >/dev/null
wait_for_file "$LANE_HOME/ochook.done"
grep -Fxq "HOOK_TEST_VAR=from-hook" "$LANE_CAPTURE/opencode.env" || fail "opencode did not get the hook's env"
python3 - "$LANE_HOME/checkouts/ochook/.opencode/opencode.json" "$REPO_REAL" <<'PY' || fail "hook guard rules missing"
import json
import sys

rules = json.load(open(sys.argv[1]))["permissions"]
required = [
    {"action": "shell", "resource": "*hook-denied*", "effect": "deny"},
    {"action": "edit", "resource": ".git/lane-checkout.json", "effect": "deny"},
    {"action": "external_directory", "resource": sys.argv[2] + "/**", "effect": "deny"},
]
sys.exit(0 if all(rule in rules for rule in required) else 1)
PY
printf '%s\n' "Revise the fake task." >"$LANE_HOME/ochook.resume-note.md"
rm -f "$LANE_CAPTURE/hook.verify-note"
LANE_OPENCODE_RETRY_SLEEP=0 "$LANE" resume ochook >/dev/null
wait_for_file "$LANE_HOME/ochook.done"
assert_eq "$LANE_HOME/ochook.resume-note.md" "$(<"$LANE_CAPTURE/hook.verify-note")" "the hook checks the lane's own resume note"
"$LANE" reap ochook --force >/dev/null
git -C "$REPO" config --unset lane.checkout
"$LANE" run legacywt --repo "$REPO" --brief "$BRIEF" --worker codex --keep-checkout >/dev/null
wait_for_file "$LANE_HOME/legacywt.done"
git -C "$REPO" config lane.checkout "$HOOK"
if resume_error=$("$LANE" resume legacywt --no-note 2>&1); then fail "a pre-hook codex lane resumed unfiltered"; fi
grep -Fq "declares a checkout hook" <<<"$resume_error" || fail "pre-hook resume refusal unnamed: $resume_error"
git -C "$REPO" config --unset lane.checkout
"$LANE" reap legacywt --force >/dev/null

echo "test: lane archive lists, then moves an old finished lane to the SSD sha256-checked, and leaves the rest"
LANE_FAKE_HOLD="$TEST_TMP/release-arch1" "$LANE" run arch1 --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
"$LANE" run arch1.b --repo "$REPO" --brief "$BRIEF" --worker fake --no-worktree >/dev/null
"$LANE" run archkeep --repo "$REPO" --brief "$BRIEF" --worker fake --no-worktree >/dev/null
"$LANE" run archco --repo "$REPO" --brief "$BRIEF" --worker fake --keep-checkout >/dev/null
"$LANE" run archbound --repo "$REPO" --brief "$BRIEF" --worker fake --no-worktree >/dev/null
"$LANE" run archlive --repo "$REPO" --brief "$BRIEF" --worker fake-hang --no-worktree >/dev/null
printf '%s\n' "archived edit" >>"$REPO_REAL/.claude/worktrees/codex-arch1/tracked.txt"
touch "$TEST_TMP/release-arch1"
for name in arch1 arch1.b archkeep archco archbound; do wait_for_file "$LANE_HOME/$name.done"; done
wait_group_exit arch1
grep -q '^CHECKOUT=retired ' "$LANE_HOME/arch1.checkout-state" || fail "arch1 was not retired: $(<"$LANE_HOME/arch1.checkout-state")"
printf '%s\n' "a stalled run" >"$LANE_HOME/arch1.stalled-1.log"
printf '%s\n' "a consumed note" >"$LANE_HOME/arch1.resume-note.consumed-1.md"
touch "$LANE_HOME/archkeep.KEEP"
printf '%s\n' "EXIT=0" >"$LANE_HOME/archlive.done"
printf '%s\n' "left by a reaped lane" >"$LANE_HOME/zzgone.stalled-1.log"
ARCH1_ENTRIES=$(cd "$LANE_HOME" && find . -maxdepth 1 -name 'arch1.*' ! -name 'arch1.b.*' | sed 's|^\./||' | sort)
assert_eq "arch1.checkout-state arch1.done arch1.harvest arch1.json arch1.log arch1.resume-note.consumed-1.md arch1.stalled-1.log" \
  "$(printf '%s\n' "$ARCH1_ENTRIES" | tr '\n' ' ' | sed 's/ $//')" "arch1's entries"
while IFS= read -r entry; do age_paths 20 "$LANE_HOME/$entry"; done <<<"$ARCH1_ENTRIES"
age_paths 20 "$LANE_HOME"/archkeep.* "$LANE_HOME"/archco.* "$LANE_HOME"/archlive.*
ARCH1_LOG_SHA=$(shasum -a 256 <"$LANE_HOME/arch1.stalled-1.log" | cut -d' ' -f1)
dry=$("$LANE" archive)
grep -Eq '^ARCHIVE  arch1  done [0-9-]{10}  [0-9]+ files  ' <<<"$dry" || fail "the dry run did not list arch1: $dry"
grep -Fxq "SKIP     archkeep  archkeep.KEEP keeps it" <<<"$dry" || fail "the KEEP lane was not skipped: $dry"
grep -Fq "SKIP     archco  lane reap archco --force first: its checkout $REPO_REAL/.claude/worktrees/codex-archco remains" \
  <<<"$dry" || fail "the lane with a checkout was not skipped: $dry"
grep -Eq '^SKIP     archlive  process group [0-9]+ exists$' <<<"$dry" || fail "the live lane was not skipped: $dry"
grep -Fxq "NO-LANE  zzgone.stalled-1.log" <<<"$dry" || fail "the dry run did not list the file of no lane: $dry"
if grep -Eq 'arch1\.b|archbound' <<<"$dry"; then fail "the dry run listed a fresh lane: $dry"; fi
assert_file "$LANE_HOME/arch1.json"
[ ! -e "$LANE_ARCHIVE_VOLUME/lane-archive" ] || fail "the dry run wrote to the volume"

echo "test: an absent SSD, one that is not a mount point and one under the disk floor move nothing"
if out=$(LANE_ARCHIVE_VOLUME="$ARCHIVE_BASE/no-ssd" "$LANE" archive --apply 2>&1); then fail "archived to an absent volume"; else rc=$?; fi
assert_eq 75 "$rc" "absent volume exit"
grep -Fq "[DEGRADED] lane-archive: $ARCHIVE_BASE/no-ssd is absent; moved nothing (1 lanes" <<<"$out" || fail "absent volume: $out"
if out=$(LANE_ARCHIVE_REQUIRE_MOUNT=1 "$LANE" archive --apply 2>&1); then fail "archived to a plain directory"; else rc=$?; fi
assert_eq 75 "$rc" "unmounted volume exit"
grep -Fq "[DEGRADED] lane-archive: $LANE_ARCHIVE_VOLUME is not a mount point" <<<"$out" || fail "unmounted volume: $out"
if out=$(DISK_FLOOR_GIB=100000000 "$LANE" archive --apply 2>&1); then fail "archived under the disk floor"; else rc=$?; fi
assert_eq 75 "$rc" "disk floor exit"
grep -Fq "[DEGRADED] lane-archive: DISK LOW: " <<<"$out" || fail "disk floor: $out"
assert_eq "" "$(ls -A "$LANE_ARCHIVE_VOLUME/lane-archive")" "volume after the refused passes"
while IFS= read -r entry; do [ -e "$LANE_HOME/$entry" ] || fail "a refused pass moved $entry"; done <<<"$ARCH1_ENTRIES"

applied=$(DISK_FLOOR_GIB=0 "$LANE" archive --apply)
ARCH1_DIR=$(sed -n 's/^ARCHIVED arch1 -> \(.*\)  [0-9]* files, .*/\1/p' <<<"$applied")
[ -n "$ARCH1_DIR" ] && [ -f "$ARCH1_DIR/MANIFEST.json" ] || fail "arch1 was not archived: $applied"
while IFS= read -r entry; do [ ! -e "$LANE_HOME/$entry" ] || fail "an archived source stayed: $entry"; done <<<"$ARCH1_ENTRIES"
for entry in arch1.b.json arch1.b.log arch1.b.done archkeep.json archco.json archlive.json archbound.json zzgone.stalled-1.log; do
  assert_file "$LANE_HOME/$entry"
done
[ -d "$REPO_REAL/.claude/worktrees/codex-archco" ] || fail "the archive pass touched a checkout"
python3 - "$ARCH1_DIR" "$ARCH1_LOG_SHA" <<'PY' || fail "the archive does not verify against its manifest"
import gzip
import hashlib
import json
import os
import sys

root, log_sha = sys.argv[1:]
manifest = json.load(open(os.path.join(root, "MANIFEST.json"), encoding="utf-8"))
entries = manifest["entries"]
assert manifest["lane"]["name"] == "arch1", manifest["lane"]
assert not any(path.startswith("arch1.b.") for path in entries), sorted(entries)
assert entries["arch1.stalled-1.log"]["sha256"] == log_sha, entries["arch1.stalled-1.log"]
assert entries["arch1.stalled-1.log"]["archived_as"] == "arch1.stalled-1.log.gz"
assert any(path.startswith("arch1.harvest/") and path.endswith("/lane.patch") for path in entries), sorted(entries)
checked = 0
for path, item in entries.items():
    if item["type"] == "file":
        packed = "archived_as" in item
        with (gzip.open if packed else open)(os.path.join(root, item.get("archived_as", path)), "rb") as handle:
            assert hashlib.sha256(handle.read()).hexdigest() == item["sha256"], path
        checked += 1
assert checked >= 8, checked
PY
assert_eq "$ARCH1_DIR" "$(awk -F'\t' '$1 == "arch1" { print $2 }' "$LANE_HOME/.archived.tsv")" "index entry"

echo "test: an archived lane names its archive, and lane unarchive restores it"
if out=$("$LANE" resume arch1 --no-note 2>&1); then fail "resume accepted an archived lane"; fi
grep -Fq "arch1 was archived to $ARCH1_DIR; lane unarchive arch1 restores it" <<<"$out" || fail "resume did not name the archive: $out"
if out=$("$LANE" review arch1 2>&1); then fail "review accepted an archived lane"; fi
grep -Fq "arch1 was archived to $ARCH1_DIR" <<<"$out" || fail "review did not name the archive: $out"
out=$("$LANE" stop nosuchlane 2>&1) || true
grep -Fq "unknown lane: nosuchlane" <<<"$out" || fail "a lane never archived is not unknown: $out"
DISK_FLOOR_GIB=0 "$LANE" unarchive arch1 >/dev/null
[ ! -e "$ARCH1_DIR" ] || fail "unarchive left the archive"
assert_eq "a stalled run" "$(<"$LANE_HOME/arch1.stalled-1.log")" "restored stalled log"
grep -Fq '+archived edit' "$(latest_harvest_of arch1)/lane.patch" || fail "the restored harvest lacks the edit"
assert_eq "DONE:0" "$(state_for arch1)" "restored lane state"
assert_eq "" "$(awk -F'\t' '$1 == "arch1"' "$LANE_HOME/.archived.tsv")" "index after unarchive"
python3 - "$LANE_HOME/arch1.done" "$LANE_HOME/arch1.stalled-1.log" <<'PY' || fail "unarchive did not restart the clock or keep the mtimes"
import os
import sys
import time

now = time.time()
sys.exit(0 if now - os.stat(sys.argv[1]).st_mtime < 3600 and now - os.stat(sys.argv[2]).st_mtime > 19 * 86400 else 1)
PY

echo "test: the pass after a retire archives old lanes, from the worker's exit path and from reap"
age_paths 20 "$LANE_HOME"/archbound.*
DISK_FLOOR_GIB=0 "$LANE" run archexit --repo "$REPO" --brief "$BRIEF" --worker fake >/dev/null
wait_for_file "$LANE_HOME/archexit.done"
wait_group_exit archexit
grep -q '^ARCHIVED archbound -> ' "$LANE_HOME/.archive.log" || fail "the exit path's pass did not archive archbound"
assert_no_file "$LANE_HOME/archbound.json"
age_paths 20 "$LANE_HOME"/arch1.b.*
reap_output=$(DISK_FLOOR_GIB=0 "$LANE" reap archco --force)
grep -Fq "lane: archive pass: lane-archive " <<<"$reap_output" || fail "reap ran no archive pass: $reap_output"
grep -q '^ARCHIVED arch1\.b -> ' "$LANE_HOME/.archive.log" || fail "reap's pass did not archive arch1.b"
assert_no_file "$LANE_HOME/arch1.b.json"
assert_file "$LANE_HOME/arch1.json"
rm -f "$LANE_HOME/archlive.done"
"$LANE" stop archlive >/dev/null

echo "test: a repo's lane.diskFloorGib sets its disk floor, and DISK_FLOOR_GIB still overrides it"
FLOOR_REPO="$TEST_TMP/floorrepo"
mkdir -p "$FLOOR_REPO"
git -C "$FLOOR_REPO" init -q
git -C "$FLOOR_REPO" config user.email lane-test@example.invalid
git -C "$FLOOR_REPO" config user.name "Lane Test"
printf '%s\n' base >"$FLOOR_REPO/tracked.txt"
git -C "$FLOOR_REPO" add tracked.txt
git -C "$FLOOR_REPO" commit -qm "floor base"
git -C "$FLOOR_REPO" config lane.diskFloorGib 100000000
if out=$(env -u DISK_FLOOR_GIB "$LANE" run floorhigh --repo "$FLOOR_REPO" --brief "$BRIEF" --worker fake 2>&1); then
  fail "ran under the repo's disk floor"
fi
grep -Fq "under the 100000000 GiB floor" <<<"$out" || fail "repo disk floor: $out"
assert_no_file "$LANE_HOME/floorhigh.json"
DISK_FLOOR_GIB=0 "$LANE" run floorenv --repo "$FLOOR_REPO" --brief "$BRIEF" --worker fake >/dev/null
wait_for_file "$LANE_HOME/floorenv.done" 300

echo "test: lane.maxRunning makes a run wait for a slot, and 0 holds every run"
CAP_REPO="$TEST_TMP/caprepo"
mkdir -p "$CAP_REPO"
git -C "$CAP_REPO" init -q
git -C "$CAP_REPO" config user.email lane-test@example.invalid
git -C "$CAP_REPO" config user.name "Lane Test"
printf '%s\n' base >"$CAP_REPO/tracked.txt"
git -C "$CAP_REPO" add tracked.txt
git -C "$CAP_REPO" commit -qm "cap base"
git -C "$CAP_REPO" config lane.maxRunning 1
"$LANE" run capa --repo "$CAP_REPO" --brief "$BRIEF" --worker fake-hang >/dev/null
DISK_FLOOR_GIB=0 LANE_SLOT_POLL_S=1 "$LANE" run capb --repo "$CAP_REPO" --brief "$BRIEF" --worker fake \
  >"$TEST_TMP/capb.out" 2>&1 &
CAP_WAIT_PID=$!
wait_for_text "$TEST_TMP/capb.out" "has 1 live lanes and caps them at 1 (lane.maxRunning); capb waits for a slot"
assert_no_file "$LANE_HOME/capb.json"
assert_eq "1 1" "$("$LANE" slots --repo "$CAP_REPO")" "slots at the cap"
assert_eq "0 none" "$("$LANE" slots --repo "$REPO")" "slots of a repo without a cap"
DISK_FLOOR_GIB=0 LANE_MAX_RUNNING=none "$LANE" run capfree --repo "$CAP_REPO" --brief "$BRIEF" --worker fake >/dev/null
wait_for_file "$LANE_HOME/capfree.done" 300
git -C "$CAP_REPO" config lane.maxRunning 0
wait_for_text "$TEST_TMP/capb.out" "holds new lanes (lane.maxRunning 0); capb waits"
"$LANE" stop capa >/dev/null
sleep 3
assert_no_file "$LANE_HOME/capb.json"
assert_eq "0 0" "$("$LANE" slots --repo "$CAP_REPO")" "slots while held"
git -C "$CAP_REPO" config lane.maxRunning 1
wait "$CAP_WAIT_PID" || fail "the held run failed: $(cat "$TEST_TMP/capb.out")"
CAP_WAIT_PID=""
grep -Fq "capb takes a slot after" "$TEST_TMP/capb.out" || fail "the held run did not say it took a slot"
wait_for_file "$LANE_HOME/capb.done" 300
assert_eq "" "$(find "$LANE_HOME" -maxdepth 1 -name '.slot-*' -print)" "a run left its slot lock"
git -C "$CAP_REPO" config lane.maxRunning many
if "$LANE" run capbad --repo "$CAP_REPO" --brief "$BRIEF" --worker fake 2>"$TEST_TMP/capbad.err"; then
  fail "a cap that is not a number started a lane"
fi
grep -Fq "lane.maxRunning must be a whole number or none, not many" "$TEST_TMP/capbad.err" \
  || fail "a bad cap gave no reason: $(cat "$TEST_TMP/capbad.err")"
assert_no_file "$LANE_HOME/capbad.json"

echo "test: LANE_NICE sets how much nicer the worker runs, and a bad value refuses before anything changes"
LANE_NICE=0 "$LANE" run nice0 --repo "$REPO" --brief "$BRIEF" --worker fake-hang --no-worktree >/dev/null
assert_eq "$own_nice" "$(/bin/ps -o nice= -p "$(json_value "$LANE_HOME/nice0.json" pid)" | tr -d ' ')" \
  "LANE_NICE=0 keeps lane's priority"
"$LANE" stop nice0 >/dev/null
for bad_nice in 21 -1 many; do
  if LANE_NICE="$bad_nice" "$LANE" run nicebad --repo "$REPO" --brief "$BRIEF" --worker fake 2>"$TEST_TMP/nicebad.err"; then
    fail "LANE_NICE=$bad_nice started a lane"
  fi
  grep -Fq "LANE_NICE must be a whole number from 0 to 20, not $bad_nice" "$TEST_TMP/nicebad.err" \
    || fail "LANE_NICE=$bad_nice gave no reason: $(cat "$TEST_TMP/nicebad.err")"
  assert_no_file "$LANE_HOME/nicebad.json"
  [ ! -e "$REPO/.claude/worktrees/codex-nicebad" ] || fail "LANE_NICE=$bad_nice left a worktree"
done

echo "PASS: lane lifecycle"
