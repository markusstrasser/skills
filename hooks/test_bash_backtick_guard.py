#!/usr/bin/env python3
"""Both-polarity tests for pretool_bash_backtick_guard.

The negative cases matter more than the positive ones here: this guard sits in front of
every Bash call, and a false block on ordinary shell usage is how a guard gets routed
around instead of obeyed.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pretool_bash_backtick_guard import offending_flag  # noqa: E402

# ---------------------------------------------------------------- MUST FIRE (real incidents)
FIRES = [
    # 2026-07-28, verbatim shape of the corrupted phenomena note
    ('uv run python3 loop/phenomena.py add --note "fresh `claude -p` per call, and `--safe-mode` '
     'stripping CLAUDE.md" --game sk48', "--note"),
    # 2026-07-25 incident shape
    ('just backlog edit x --append note="ran `just pack-collision-check` and it passed"', "note="),
    # 2026-07-17 incident shape: Evidence field with two inline CLI names
    ('tool add --evidence "see `foo --bar` and `baz` for the trace"', "--evidence"),
    # git commit message with markdown inline code
    ('git commit -m "fix `--no-ext-diff` handling in the guard" -- a.py', "-m"),
    # odd/unterminated backtick is a bug under every reading
    ('phenomena.py add --note "the flag `--safe-mode is what strips it"', "--note"),
    # --flag=VALUE form
    ('tool --summary="uses `rg --no-ignore` under the hood"', "--summary"),
]

# ---------------------------------------------------------------- MUST NOT FIRE
CLEAN = [
    # SINGLE quotes: literal in every POSIX shell — the recommended fix must not be blocked
    "phenomena.py add --note 'prose with `inline code` is safe here'",
    # no backtick at all
    'git commit -m "ordinary message with no code spans" -- a.py',
    # backtick OUTSIDE any data flag = legacy-but-intentional substitution, not our business
    'echo "today is `date`"',
    "for f in `ls`; do echo $f; done",
    # ESCAPED backtick inside a double-quoted value is literal, not a substitution
    r'tool --note "a literal \` backtick"',
    # $(...) form: explicit intent, and the cat-guard already covers the file case
    'git commit -m "count $(wc -l < f)" -- a.py',
    # data flag present but value has no backtick, while a backtick lives elsewhere
    'tool --note "clean prose" --other "`date`"',
    # heredoc-with-quoted-delimiter: the recommended fix #2 must pass
    "tool add --note \"$(cat <<'EOF'\nprose with `inline code`\nEOF\n)\"",
    # a flag whose NAME merely contains a data-flag substring
    'tool --message-file notes.md && echo "`date`"',
]


def main() -> int:
    bad = []
    for cmd, want_flag in FIRES:
        got = offending_flag(cmd)
        if got is None:
            bad.append(f"FALSE NEGATIVE (should block, {want_flag}): {cmd[:90]}")
    for cmd in CLEAN:
        got = offending_flag(cmd)
        if got is not None:
            bad.append(f"FALSE POSITIVE (blocked on {got}): {cmd[:90]}")
    if bad:
        print("\n".join(bad))
        print(f"\n{len(bad)} failure(s) of {len(FIRES) + len(CLEAN)} cases")
        return 1
    print(f"ok — {len(FIRES)} fire cases, {len(CLEAN)} clean cases, both polarities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
