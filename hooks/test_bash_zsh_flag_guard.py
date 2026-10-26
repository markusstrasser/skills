#!/usr/bin/env python3
"""Both-polarity tests for pretool_bash_zsh_flag_guard.

FIRES holds the commands Claude Code 2.1.310 held for approval (the two hung lane calls and
the 2026-10-27 probes); CLEAN holds the probed forms that ran, plus literal spellings the
shell never expands. A false block costs a rewrite on every such command, so the clean side
must stay clean.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pretool_bash_zsh_flag_guard import offending_expansion, reason  # noqa: E402

# ---------------------------------------------------------------- MUST FIRE
FIRES = [
    # 2026-10-27 05:41:47, the hung negatives-panels call (shortened)
    ('P="$TMPDIR/pt"; nodes=$(cat "$P/fail.txt"); env -i PATH="$PATH" uv run python3 -m pytest -q '
     '--basetemp "$P/newfail" ${(f)nodes} >> "$P/log" 2>&1', "${(f)nodes}"),
    # probe: denied
    ('x=$(printf "a\\nb"); print -l ${(f)x}', "${(f)x}"),
    # probe: denied inside double quotes
    ('arr=(a b); echo "${(j:,:)arr}"', "${(j:,:)arr}"),
    # inside $( ... ) within double quotes
    ('echo "$(print -l ${(s:,:)csv})"', "${(s:,:)csv}"),
    # unquoted heredoc bodies expand
    ("cat <<EOF > out.txt\n${(k)assoc}\nEOF", "${(k)assoc}"),
]

# ---------------------------------------------------------------- MUST NOT FIRE
CLEAN = [
    # probe: ran
    'x=$(printf "a\\nb"); print -l ${=x}',
    # probe: ran (quoted-delimiter heredoc body is data)
    "cat <<'EOF' > heredoc-literal.txt\nlines=${(f)x}\nEOF",
    # single quotes are literal
    "echo '${(f)x} is a zsh idiom'",
    "python3 -c 'print(\"${(f)x}\")'",
    # comment
    "ls  # never write ${(f)x} in a lane",
    # ordinary expansions
    'echo "${HOME}/x ${var:-default} ${#arr[@]} ${arr[@]}"',
    # JS template literal written through a quoted heredoc
    "cat <<'JS' > a.js\nconst s = `${(a + b)}`;\nJS",
]


def main() -> int:
    bad = []
    for cmd, want in FIRES:
        got = offending_expansion(cmd)
        if got != want:
            bad.append(f"FIRE case returned {got!r}, want {want!r}: {cmd[:90]!r}")
    for cmd in CLEAN:
        got = offending_expansion(cmd)
        if got is not None:
            bad.append(f"FALSE POSITIVE ({got!r}): {cmd[:90]!r}")
    if "xargs -0" not in reason("${(f)x}"):
        bad.append("reason() lost the rewrite hint")
    if bad:
        print("\n".join(bad))
        print(f"\n{len(bad)} failure(s) of {len(FIRES) + len(CLEAN)} cases")
        return 1
    print(f"ok — {len(FIRES)} fire cases, {len(CLEAN)} clean cases, both polarities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
