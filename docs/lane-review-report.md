**Verdict:** DONE — all five Resume Note #2 findings are fixed and verified.
- Files: `bin/lane`, `tests/test_lane.sh`, `README.md`, `docs/lane-cli-report.md`, this report.
- Tests: 10 pre-feature; 18 at resume baseline; 19 final; `bash tests/test_lane.sh` passes on Bash 3.2.
- Pre-fix controls: `POSITIVE-CONTROL-FAIL: forged started_epoch=1 reported RUNNING`; `POSITIVE-CONTROL-FAIL: resume note claim line 827 occurs after launch line 821`.
- Patch control: `POSITIVE-CONTROL-FAIL: git diff HEAD omitted untracked review-new.txt`.
- Example: `bin/lane review auth-fix`.
- Example: `bin/lane review auth-fix --model gpt-5.6 --effort high --focus /tmp/review-axes.txt --out /tmp/auth-fix.review.md --bg`.
- Example: `bin/lane resume auth-fix --note /tmp/auth-fix-resume.md`.
- Example: `bin/lane resume auth-fix --no-note`.

## Delivered

- Worker metadata records `started_epoch`, derived portably from `ps -o
  lstart=`. List, stop, resume, reap, and dispatch overlap checks require both
  the recorded process group and matching process start time. Legacy empty
  epochs fall back to the process-group check with a warning.
- `lane review` builds `$LANE_HOME/<name>.patch` from the recorded worktree's
  tracked diff plus safe untracked text-file hunks. It does not stage files or
  mutate the index. Binary and files larger than 1 MB are skipped; symlinks,
  FIFOs, sockets, and device files are reported without being opened.
- The newest recursive `docs/audit/**/*-report.md`, or an explicit report passed
  through `--focus`, is attached as a second `-f` and omitted from untracked
  patch hunks. A non-report focus file is appended to the fixed correctness
  prompt as review axes.
- Foreground and `nohup` background dispatches use `llmx -o`; background reviews
  print their PID, output path, and atomic `.review.done` marker path. Review
  identity also stores its process start time, and an atomic per-lane directory
  lock rejects overlap until the wrapper exits.
- `lane ls` reports `REVIEW` as `-`, `RUNNING`, or `DONE:<rc>` using the review
  PID plus start time.
- Resume notes live at `$LANE_HOME/<name>.resume-note.md` and atomically move to
  `$LANE_HOME/<name>.resume-note.consumed-<n>.md` before prompt construction or
  launch. There is no global-note fallback. `--no-note` is explicit.

## Verification

- `bash tests/test_lane.sh`: PASS, 19 named cases.
- `/bin/bash -n bin/lane tests/test_lane.sh`: PASS.
- `shfmt -i 2 -ci -d bin/lane tests/test_lane.sh`: PASS.
- `git diff --check -- bin/lane tests/test_lane.sh README.md docs/lane-cli-report.md docs/lane-review-report.md`: PASS.
- Negative grep for the exact global `$LANE_HOME/resume-note.md` reference in
  `bin/lane`: PASS (absent).
- `shellcheck`: unavailable in this environment.

The fake `llmx` assertions cover the two `-f` inputs, `-o`, model, effort,
timeout, focus prompt, foreground stdout behavior, review start identity,
atomic overlap locking, and both `EXIT=0` and `EXIT=9` marker propagation.
Patch assertions cover tracked, untracked, binary, oversized, broken-symlink,
FIFO, separate-report, and unchanged-index behavior. Worker assertions forge a
wrong start epoch while the real process group remains alive, restore the real
identity as a positive control, and exercise the warning fallback for legacy
empty epochs. Tests use a deterministic `ps` fake because this managed sandbox
denies real `ps`; the suite exercises both the BSD/macOS `date -j -f` path and
the GNU/Linux `date -d` fallback.

The supplied gpt-5.6 cosign findings were validated against source before
implementation. The local code-review scout could not run inside this managed
worktree because its cache/artifact paths are outside the writable roots; that
transport limitation was not treated as review evidence. Manual call-site
validation and the deterministic suite found no remaining defect.

## Documentation edits

- `bin/lane:12,15`: command usage for `review` and resume-note options; the same
  file contains process identity, review locking/patch safety, and
  claim-before-launch semantics.
- `README.md:104-122`: public Lane CLI workflow, liveness identity, review lock,
  and exact examples.
- `docs/lane-cli-report.md:3-10`: lifecycle report updated for the verified
  review, liveness, and resume behavior.

No commit was made; the parent owns landing this diff.
