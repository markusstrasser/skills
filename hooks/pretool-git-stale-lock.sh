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

now=$(date +%s)

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
