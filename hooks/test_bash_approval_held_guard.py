#!/usr/bin/env python3
"""Both-polarity tests for pretool_bash_approval_held_guard.

ZSH_FIRES / RM_FIRES hold commands Claude Code held for approval (the hung lane calls and the
2026-10-27 probes, 2.1.310 / 2.1.311); the CLEAN lists hold probed forms that ran, plus
literal spellings the shell never expands. A false block costs a rewrite on every such
command, so the clean side must stay clean.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pretool_bash_approval_held_guard import offending, reason  # noqa: E402

# ---------------------------------------------------------------- zsh flag groups: MUST FIRE
ZSH_FIRES = [
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

# ---------------------------------------------------------------- zsh flag groups: MUST NOT FIRE
ZSH_CLEAN = [
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

# ---------------------------------------------------------------- recursive rm: MUST FIRE
RM_FIRES = [
    # probe 1: denied
    ('P="/abs/deep/rmprobe"; for dir in a b; do if test -d "$P/$dir"; then chmod -R u+w "$P/$dir" '
     '&& rm -rf "$P/$dir"; echo "$dir rc=$?"; fi; done', "rm_var"),
    # 1b: the hung negatives-panels call, 2026-10-27 06:55
    ('P="$TMPDIR/pt-negatives-panels"; for dir in allnew ctxround newfail fixround cpsrschema; do '
     'if test -d "$P/$dir"; then chmod -R u+w "$P/$dir" && rm -rf "$P/$dir"; echo "$dir rc=$?"; '
     'fi; done; du -sh "$P" | tail -1; ls "$P" | wc -l', "rm_var"),
    ('rm -rf "$X/"', "rm_var"),
    ('rm -rf "$X"/*', "rm_var"),
    ("rm -rf $(cat list)", "rm_cmdsub"),
    ('rm -rf "$HOME/x"', "rm_var"),
    ('rm -rf -- "$P/$dir"', "rm_var"),
    # held in the 14-day history (Claude Code 2.1.311 denial texts)
    ("rm -rf $D/30000/inputs $D/*/before/projection", "rm_var"),
    ("P=/tmp/caddsv2-aria-probe; rm -rf $P/dl $P/*.log", "rm_var"),
    ("rm -f $I/*.patch", "rm_var"),
    ('for n in a b; do rm -- "$P/$n.patch"; done', "rm_var"),
    ('O=/Users/x/.cache/lanes; for n in a b; do D="$O/$n"; rm -rf "${D:?}"; done', "rm_var"),
    ('for n in a b; do C=$OCL/$n/genomics; rm -rf "$C"; done', "rm_var"),
    ("rm -rf /Volumes/2TBPNY/iqdiff-scratch-04e42bf9", "rm_mount"),
    ('D=/abs/deep/screens; rm -f "$D"/*" "*.log', "rm_var"),
    ("bash -c 'for n in a b; do rm -rf \"$T/$n\"; done'", "rm_var"),
    # round 2: wrappers, basename rm, rm inside double quotes (Claude Code parses it)
    ('nohup rm -rf "$X/" &', "rm_var"),
    ('nohup rm -rf "$UNSET_PROBE_VAR/" > /dev/null 2>&1', "rm_var"),
    ('env VAR=1 rm -rf "$X/"', "rm_var"),
    ('env -i PATH=/bin VAR=1 rm -rf "$X/"', "rm_var"),
    ('timeout 30 rm -rf "$X/"', "rm_var"),
    ('nice -n 5 exec rm -rf "$X/"', "rm_var"),
    ('/bin/rm -rf "$X/"', "rm_var"),
    ('git commit -m "Clean up; rm -rf $X/y is now guarded" -- f.py', "rm_var"),
    ('echo "step 2; rm -r $D/" > /dev/null', "rm_var"),
]

# ---------------------------------------------------------------- recursive rm: MUST NOT FIRE
RM_CLEAN = [
    # probes 2-11: ran
    ('P="/abs/deep/rmprobe"; for dir in a b; do if test -d "${P:?}/${dir:?}"; then chmod -R u+w '
     '"${P:?}/${dir:?}" && rm -rf "${P:?}/${dir:?}"; echo "$dir rc=$?"; fi; done'),
    'rm -rf /abs/deep/rmprobe/c; echo "rc=$?"',
    'P="/abs/deep/rmprobe"; rm -f "$P/x.txt"; echo rc=$?',
    'cd /abs/deep/rmprobe && dir=a && rm -rf "rel/$dir"; echo rc=$?',
    'T=$(mktemp -d); rm -rf "${T:?}"; echo rc=$?',
    'rm -rf "$TMPDIR/rmprobe-x"; echo rc=$?',
    'dir=b; rm -rf "/abs/deep/rmprobe/deep/$dir"; echo rc=$?',
    'P="/abs/deep/rmprobe/f"; rm -rf "$P/x"; echo rc=$?',
    'rm -f "$UNSET_PROBE_VAR/h.txt"; echo rc=$?',
    'P="$TMPDIR/rmprobe-j"; rm -rf "$P/y"; echo rc=$?',
    # two components below an empty prefix is not top-level
    'rm -rf "$HOME/.cache/x"',
    # literal text
    "cat <<'EOF' > f\nrm -rf \"$P/$dir\"\nEOF",
    "echo 'rm -rf \"$P/$dir\"'",
    'rm -rf /Volumes/2TBPNY/scratch/deep',
    # same history call: the literal-assigned $P/dl target was not held
    "P=/tmp/caddsv2-aria-probe; rm -rf $P/dl",
    'timeout 30 rm -rf /abs/deep/x',
    "python3 - <<'EOF'\ncmd = 'rm -rf \"$P/$d\"'\nEOF",
    "git commit -m 'Clean up; rm -rf $X/y is now guarded' -- f.py",
    'for n in a b; do rm -rf "/abs/deep/$n"; done',
]


def test_zsh_fires():
    for cmd, want in ZSH_FIRES:
        hit = offending(cmd)
        assert hit is not None and hit.kind == "zsh_flag" and hit.excerpt == want, (cmd, hit)


def test_zsh_clean():
    for cmd in ZSH_CLEAN:
        assert offending(cmd) is None, cmd


def test_rm_fires():
    for cmd, kind in RM_FIRES:
        hit = offending(cmd)
        assert hit is not None and hit.kind == kind, (cmd, hit)


def test_rm_clean():
    for cmd in RM_CLEAN:
        assert offending(cmd) is None, (cmd, offending(cmd))


def test_reason_texts():
    from pretool_bash_approval_held_guard import Hit

    assert "xargs -0" in reason(Hit("zsh_flag", "${(f)x}"))
    assert '"${P:?}/${dir:?}"' in reason(Hit("rm_var", '"$P/$dir"'))
    assert "quoted string" in reason(Hit("rm_var", '"$P/$dir"'))
    assert "on its own first" in reason(Hit("rm_cmdsub", "$(cat list)"))
    for kind in ("zsh_flag", "rm_var", "rm_cmdsub"):
        assert "bypass mode" in reason(Hit(kind, "x"))


if __name__ == "__main__":
    for fn in (test_zsh_fires, test_zsh_clean, test_rm_fires, test_rm_clean, test_reason_texts):
        fn()
    print("ok")
