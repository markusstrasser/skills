#!/usr/bin/env bash
# pretool-git-stale-lock.sh — clear a git lock file that no process holds.
#
# Deploy as a PreToolUse hook on Bash. Exit 0 always: this never blocks a command,
# it only removes garbage that would otherwise make every later git write fail.
#
# Why it exists (genomics, 2026-09-17): a zero-byte `.git/index.lock` left at 14:57:56
# by a git that died mid-commit blocked EVERY commit in the checkout for 8 h 25 m. It was
# found only when a six-commit landing died at its first commit with the ordinary message
# "Another git process seems to be running in this repository, or the lock file may be
# stale" — the same text live contention produces, so the standing advice (sleep and
# retry) would have failed forever. Nothing surfaces a stale lock until something needs
# to commit, and a landing that applies a patch before committing leaves the worktree
# dirty when it fails.
#
# Staleness test is possession, not age: a live `git` holds its lock file OPEN from
# O_CREAT|O_EXCL until the rename, so `lsof` on the path is exact. A lock with no holder
# cannot be in use by anyone. The age floor below only closes the microscopic window
# between another process's creat() and our lsof scan; a genuine stale lock is minutes to
# hours old, so the floor never delays a real cleanup.
#
# CORRECTION 2026-09-24 (measured, git 2.54): "a live git holds its lock OPEN" is false
# during a hook phase. `git commit -a` and `git commit --only` write index.lock, CLOSE
# it, run pre-commit/commit-msg, and rename it only after the hooks return; lsof finds no
# holder the whole time. Deleting it then kills the commit with "repository has been
# updated, but unable to write new index file" and leaves the index behind HEAD. So a
# second test was added below: nothing is removed while a git process runs inside one of
# this repo's worktrees. In both recorded incidents the git that left the lock was dead
# (heli: no git process at all), so they still clear; a busy repo only defers cleanup to
# the next git command.
#
# Fails open on every error (missing lsof, unreadable dir, odd paths): a hook must never
# be the reason a command cannot run.

trap 'exit 0' ERR
set -u

MIN_AGE_SECONDS="${GIT_STALE_LOCK_MIN_AGE_SECONDS:-30}"
RECEIPTS="${GIT_STALE_LOCK_RECEIPTS:-$HOME/.cache/git-stale-lock/removed.jsonl}"

# Drain the harness's JSON payload (unused here) so the writer never sees EPIPE.
# Skipped when stdin is a terminal so a manual run does not block.
[ -t 0 ] || cat >/dev/null 2>&1 || true

command -v lsof >/dev/null 2>&1 || exit 0

git_dir=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
[ -n "$git_dir" ] || exit 0
[ -d "$git_dir" ] || exit 0
# Absolute, so each receipt names its repo: at a repo top level rev-parse prints a bare
# ".git", and receipts read ".git/index.lock" with no way to tell which repo it was.
git_dir=$(cd "$git_dir" 2>/dev/null && pwd -P) || exit 0

now=$(date +%s)

# True while any git process has its cwd inside this repo: a worktree (main or linked)
# or the git dir. Such a process may own a closed lock mid-hook (see CORRECTION above).
# Computed once, and only when a lock would otherwise be removed, so the common no-lock
# run never pays for it. A git that is alive but whose cwd cannot be read counts as
# busy; one that exited between pgrep and lsof does not.
busy=""
repo_git_busy() {
  if [ -z "$busy" ]; then
    busy=no
    local roots pid cwd root
    roots=$(
      printf '%s\n' "$git_dir"
      git worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p' |
        while IFS= read -r wt; do (cd "$wt" 2>/dev/null && pwd -P); done
    )
    for pid in $(pgrep -x git 2>/dev/null); do
      cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)
      if [ -z "$cwd" ]; then
        if kill -0 "$pid" 2>/dev/null; then busy=yes; break; fi
        continue
      fi
      while IFS= read -r root; do
        [ -n "$root" ] || continue
        case "$cwd/" in "$root"/*) busy=yes ;; esac
      done <<ROOTS
$roots
ROOTS
      if [ "$busy" = yes ]; then break; fi
    done
  fi
  [ "$busy" = yes ]
}

# Locks that block a commit. Ref locks are included because a dead git leaves them the
# same way and they refuse a commit just as hard as index.lock, with a different message.
candidates=$(
  {
    printf '%s\n' "$git_dir/index.lock" "$git_dir/HEAD.lock" "$git_dir/config.lock"
    # Per-worktree index locks; a lane that died mid-commit strands one of these.
    find "$git_dir/worktrees" -maxdepth 2 -name 'index.lock' 2>/dev/null
    find "$git_dir/refs" -name '*.lock' 2>/dev/null
  } 2>/dev/null
)

removed_any=0
while IFS= read -r lock; do
  [ -n "$lock" ] || continue
  [ -f "$lock" ] || continue

  # A process holding the lock open means a real git is mid-operation: leave it alone.
  holders=$(lsof -t -- "$lock" 2>/dev/null || true)
  if [ -n "$holders" ]; then
    continue
  fi

  mtime=$(stat -f %m "$lock" 2>/dev/null || stat -c %Y "$lock" 2>/dev/null || echo "")
  [ -n "$mtime" ] || continue
  age=$(( now - mtime ))
  [ "$age" -ge "$MIN_AGE_SECONDS" ] || continue

  # No holder is not enough: a git in a hook phase keeps its lock closed. Leave every
  # lock alone while a git runs in this repo; the next git command retries.
  if repo_git_busy; then
    break
  fi

  size=$(stat -f %z "$lock" 2>/dev/null || stat -c %s "$lock" 2>/dev/null || echo "?")
  if rm -f "$lock" 2>/dev/null; then
    removed_any=1
    mkdir -p "$(dirname "$RECEIPTS")" 2>/dev/null || true
    printf '{"ts":"%s","lock":"%s","age_seconds":%s,"size_bytes":"%s","holders":"none"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$lock" "$age" "$size" >>"$RECEIPTS" 2>/dev/null || true
    echo "git-stale-lock: removed $lock (unheld, age ${age}s, ${size} bytes)" >&2
  fi
done <<EOF
$candidates
EOF

exit 0
