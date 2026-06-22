#!/bin/bash
# pretool-noext-nongit-guard.sh — PreToolUse:Bash hook.
# BLOCK `--no-ext-diff` applied as a FLAG to a NON-git command (rg/grep/sed/awk/find/zoekt/...).
#
# `--no-ext-diff` is a GIT-ONLY flag (auto-injected for git by pretool-git-noext-inject.sh).
# Applied to rg/grep/etc. it is an UNRECOGNIZED FLAG → the tool exits non-zero with NO output →
# with `2>/dev/null` (common in agent search pipelines) this becomes a SILENT FALSE-ZERO:
# "0 hits" for content that plainly exists. The agent then reasons from the false negative.
#
# Evidence (2026-06-22, session 8e90cc06): ~4 `rg --no-ext-diff` false-zeros in one session →
# nearly concluded real genomics code (independence_key, CaseBundle, …) was FABRICATED, and
# propagated wrong "rg is blind in genomics, use zoekt" advice into a subagent brief. rg was never
# blind; the git-only flag erroring under 2>/dev/null was.
#
# Parser: proper shlex (posix, punctuation_chars) so QUOTED strings stay single tokens — the flag
# inside a `git commit -m "...rg --no-ext-diff..."` message or a grep PATTERN is NOT a flag and is
# NOT blocked (the v1 substring parser false-positived on exactly this — its own commit message).
# Deterministic; BLOCKS, never rewrites; fails OPEN on unparseable input.

INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | .command // ""' 2>/dev/null || true)
[ -z "$CMD" ] && exit 0
case "$CMD" in *--no-ext-diff*) : ;; *) exit 0 ;; esac   # fast path: flag absent → no work

HIT=$(printf '%s' "$CMD" | python3 -c "
import sys, re, shlex
cmd = sys.stdin.read()
# Tools that do NOT accept --no-ext-diff (it errors). git is intentionally absent.
NONGIT = {'rg','grep','egrep','fgrep','ag','ack','fd','find','sed','awk','zoekt',
          'cat','head','tail','wc','cut','tr','sort','uniq','ast-grep','sg'}
try:
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    toks = list(lex)
except ValueError:
    sys.exit(0)   # unbalanced quotes / unparseable → fail OPEN (never block on uncertainty)
RESET = {'|','||','&&',';','&','|&','(',')','{','}'}
expect_cmd = True
seg_nongit = False
cur = None
for t in toks:
    if t in RESET:
        expect_cmd = True; seg_nongit = False; continue
    if expect_cmd:
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):   # ENV=val prefix; still expecting the command word
            continue
        cur = t.rsplit('/', 1)[-1]                       # basename, handles /usr/bin/rg
        seg_nongit = cur in NONGIT
        expect_cmd = False
        continue
    if t == '--no-ext-diff' and seg_nongit:             # a STANDALONE flag token on a non-git command
        print(cur); break
" 2>/dev/null || true)

if [ -n "$HIT" ]; then
    echo "BLOCKED: --no-ext-diff is a GIT-ONLY flag, but you applied it to '$HIT'." >&2
    echo "On $HIT it is an UNRECOGNIZED FLAG → the tool errors (exit 2) with no output → with" >&2
    echo "2>/dev/null this is a SILENT FALSE-ZERO (0 hits for content that exists, the worst trap)." >&2
    echo "Fix: drop --no-ext-diff from the '$HIT' command (it is auto-injected for git ONLY)." >&2
    ~/Projects/skills/hooks/hook-trigger-log.sh "noext-nongit-guard" "block" "$HIT" 2>/dev/null || true
    exit 2
fi
exit 0
