#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
LANE="$ROOT/bin/lane"
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/lane-test.XXXXXX")
export LANE_HOME="$TEST_TMP/lanes"
REPO="$TEST_TMP/repo"
BRIEF="$TEST_TMP/brief.md"
FAKE_BIN="$TEST_TMP/bin"
LANE_CAPTURE="$TEST_TMP/capture"
export LANE_CAPTURE
UNRELATED_PID=""

cleanup() {
  local name
  for name in first hang inline codexargs claudeargs failure; do
    if [ -f "$LANE_HOME/$name.json" ]; then
      "$LANE" stop "$name" >/dev/null 2>&1 || true
    fi
  done
  if [ -n "$UNRELATED_PID" ]; then
    kill "$UNRELATED_PID" >/dev/null 2>&1 || true
  fi
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

state_for() {
  local name="$1"
  shift
  "$LANE" ls "$@" | awk -v wanted="$name" '$1 == wanted { print $2 }'
}

dirty_for() {
  local name="$1"
  "$LANE" ls | awk -v wanted="$name" '$1 == wanted { print $5 }'
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
chmod +x "$FAKE_BIN/codex" "$FAKE_BIN/claude"
export PATH="$FAKE_BIN:$PATH"

echo "test: codex and claude worker commands match the dispatch contract"
"$LANE" run codexargs --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/codexargs.done"
expected_codex=$(printf '%s\n' \
  exec \
  -m \
  gpt-5.6-sol \
  -s \
  workspace-write \
  --skip-git-repo-check \
  "Do the task in $BRIEF_REAL.")
assert_eq "$expected_codex" "$(<"$LANE_CAPTURE/codex.args")" "codex arguments"
assert_eq "$REPO_REAL" "$(<"$LANE_CAPTURE/codex.cwd")" "codex cwd"
for key in name repo worktree brief pid started_at worker; do
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
expected_claude=$(printf '%s\n' -p --model claude-opus-4-8 "Do the fake task.")
assert_eq "$expected_claude" "$(<"$LANE_CAPTURE/claude.args")" "claude arguments"
assert_eq "$REPO_REAL" "$(<"$LANE_CAPTURE/claude.cwd")" "claude cwd"

echo "test: worker failures still produce an exit marker"
CODEX_FAKE_RC=7 "$LANE" run failure --repo "$REPO" --brief "$BRIEF" --worker codex --no-worktree >/dev/null
wait_for_file "$LANE_HOME/failure.done"
assert_eq "EXIT=7" "$(<"$LANE_HOME/failure.done")" "failure marker"
assert_eq "DONE:7" "$(state_for failure)" "failed worker state"

echo "test: run reports RUNNING and creates its isolated worktree"
run_output=$("$LANE" run first --repo "$REPO" --brief "$BRIEF" --worker fake)
grep -q '^watch: while ' <<<"$run_output" || fail "run did not print a watch loop"
assert_eq "RUNNING" "$(state_for first)" "initial state"
[ -d "$REPO/.claude/worktrees/codex-first" ] || fail "worktree was not created"
assert_eq "codex/first" "$(git -C "$REPO/.claude/worktrees/codex-first" branch --show-current)" "worktree branch"
printf '%s\n' scratch >"$REPO/.claude/worktrees/codex-first/scratch.txt"
assert_eq "1" "$(dirty_for first)" "worktree dirty count"

echo "test: completion marker and DONE state"
wait_for_file "$LANE_HOME/first.done"
assert_eq "EXIT=0" "$(<"$LANE_HOME/first.done")" "completion marker"
assert_eq "DONE:0" "$(state_for first)" "completed state"

echo "test: zero-minute stall threshold and exact stop archive"
"$LANE" run hang --repo "$REPO" --brief "$BRIEF" --worker fake-hang >/dev/null
sleep 2
assert_eq "STALLED" "$(state_for hang --stall-min 0)" "stalled state"
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

echo "test: resume note is created and prepended"
"$LANE" resume first >/dev/null
wait_for_file "$LANE_HOME/first.done"
assert_file "$LANE_HOME/resume-note.md"
assert_eq \
  "Start with git status and git diff in the worktree. Keep sound edits, finish the task, and write the report." \
  "$(head -1 "$LANE_HOME/first.log")" \
  "resume prompt prefix"
grep -q '^hi$' "$LANE_HOME/first.log" || fail "resumed fake worker did not finish"

echo "test: reap is inspect-only without --force, then removes the lane"
sleep 0.2
reap_output=$("$LANE" reap first)
grep -q '^lane: git diff --stat' <<<"$reap_output" || fail "reap did not print diff stat"
grep -q '^scratch.txt$' <<<"$reap_output" || fail "reap did not list untracked files"
[ -d "$REPO/.claude/worktrees/codex-first" ] || fail "non-forced reap removed worktree"
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

echo "PASS: lane lifecycle"
