#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
LANE="$ROOT/bin/lane"
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/lane-test.XXXXXX")
mkdir -p "$TEST_TMP/lanes"
LANE_HOME=$(cd "$TEST_TMP/lanes" && pwd -P)
export LANE_HOME
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
chmod +x "$FAKE_BIN/codex" "$FAKE_BIN/claude" "$FAKE_BIN/ps" "$FAKE_BIN/llmx"
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
assert_eq "2" "$(grep -c '^-f$' "$foreground_args")" "review file arguments"
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
assert_eq "gpt-5.6" "$(arg_after -m "$background_args")" "default review model"
assert_eq "high" "$(arg_after -e "$background_args")" "default review effort"
assert_eq "$LANE_HOME/first.review.md" "$(arg_after -o "$background_args")" "default review output"

echo "test: background review preserves a nonzero llmx exit code"
LLMX_CAPTURE_NAME=background-failure LLMX_FAKE_RC=9 "$LANE" review first --bg >/dev/null
wait_for_file "$LANE_HOME/first.review.done"
wait_for_absent "$LANE_HOME/first.review.lock"
assert_eq "EXIT=9" "$(<"$LANE_HOME/first.review.done")" "failed background review marker"
assert_eq "DONE:9" "$(review_for first)" "failed background review state"

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
