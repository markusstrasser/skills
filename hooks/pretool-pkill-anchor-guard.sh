#!/usr/bin/env bash
# pretool-pkill-anchor-guard.sh — PreToolUse(Bash) hook.
# Gov-ID: hook:pkill-anchor-guard
# goal: `pkill -f <substring-pattern>` against a multi-job tree can match a
#       process the caller never intended — `*forkDC*` matched the unrelated
#       `forkDCH`, killing a healthy training client; an earlier same-day
#       pkill matched a concurrent canary. `-f` matches the pattern against
#       the FULL command line by SUBSTRING unless the pattern is anchored
#       (a `/` path segment, `^`, or paired with `-x` for a whole-string
#       match) — ~/.claude/rules/wakeup-cadence.md "pkill discipline for job
#       trees" (2026-07-12, two same-day incidents).
# verifier: skills/hooks/test_bash_dispatch.py (native port lives there)
# blast_radius: shared
#
# ADVISORY ONLY — never blocks. `pkill -f` is sometimes exactly the right
# tool; the guard's job is to make the caller run `pgrep -fl` first and read
# every match before anything dies, matching the rule's own prescribed order
# (pgrep preview is the kill's probe-before-action).
#
# Shape: same shlex-segment-scan pattern as pretool-git-add-all-guard.sh /
# pretool-git-stash-guard.sh — split on shell separators so a pkill buried in
# a compound command (`cd x && pkill -f foo`) is still caught, extract the
# -f pattern argument, and classify it anchored/unanchored.
#
# NOTE: no `trap 'exit 0' ERR` — this hook never exits nonzero on purpose
# (advisory-only), so there is no exit-2 path an ERR trap could swallow; kept
# absent anyway for parity with the other guards' documented reasoning.

INPUT=$(cat)

python3 - "$INPUT" <<'PY'
import sys, json, re, shlex

try:
    data = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)

cmd = (data.get("tool_input", {}) or {}).get("command", "")
if not cmd or "pkill" not in cmd:
    sys.exit(0)

segments = re.split(r"&&|\|\||;|\||\n", cmd)


def find_pkill_f_patterns(seg: str):
    """Yield (pattern, has_dash_x) for every `pkill ... -f <pattern>` call
    in this segment. Returns nothing for segments with no pkill -f."""
    seg = seg.strip()
    try:
        parts = shlex.split(seg)
    except ValueError:
        return
    i = 0
    while i < len(parts):
        tok = parts[i].rsplit("/", 1)[-1]  # basename: /usr/bin/pkill -> pkill
        if tok != "pkill":
            i += 1
            continue
        # Found a pkill invocation starting at i — scan its args until the
        # next shell-level token boundary (segments are already split on
        # &&/||/|/;\n so this just means "rest of this segment's tokens").
        args = parts[i + 1:]
        # Standalone "-x" token only — a fuzzy "any flag containing the
        # letter x" check would collide with the -f value-extraction below
        # (bundled "-fx" is ambiguous: -f with value "x", or -f plus -x?);
        # advisory-only stakes mean under-detecting bundled -x just costs a
        # nudge that could have been skipped, never a wrongly-skipped block.
        has_dash_x = "-x" in args
        pattern = None
        j = 0
        while j < len(args):
            a = args[j]
            # Only accept the NEXT token as -f's value if it doesn't itself
            # look like a flag (`pkill -f -x pattern` is a pathological
            # ordering; safer to find no pattern than to misread "-x" as one).
            if a == "-f":
                if j + 1 < len(args) and not args[j + 1].startswith("-"):
                    pattern = args[j + 1]
                j += 2
                continue
            if a.startswith("-f") and len(a) > 2 and not a.startswith("--"):
                pattern = a[2:]
                j += 1
                continue
            if a == "--full":  # GNU-style long form some pkill builds accept
                if j + 1 < len(args) and not args[j + 1].startswith("-"):
                    pattern = args[j + 1]
                j += 2
                continue
            j += 1
        if pattern is not None:
            yield pattern, has_dash_x
        break  # one pkill call per segment is the common/expected shape


def is_anchored(pattern: str, has_dash_x: bool) -> bool:
    if has_dash_x:
        return True  # -x forces a whole-string match — substring risk moot
    if pattern.startswith("^"):
        return True
    if "/" in pattern:
        return True  # a real path segment narrows well past a bare process name
    return False


hits = []
for seg in segments:
    for pattern, has_dash_x in find_pkill_f_patterns(seg):
        if not is_anchored(pattern, has_dash_x):
            hits.append(pattern)

if not hits:
    sys.exit(0)

pat_list = ", ".join(f"'{p}'" for p in hits)
msg = (
    f"ADVISORY: pkill -f pattern(s) [{pat_list}] look unanchored (no `/` path segment, "
    "no leading `^`, no paired `-x`) — `-f` matches by SUBSTRING against the full command "
    "line. Run `pgrep -fl '<pattern>'` FIRST and read every match before killing anything; "
    "anchor to a unique token (full path, `^`, or `-x`) once you've confirmed the match set. "
    "(wakeup-cadence.md pkill discipline — 2 same-day incidents 2026-07-12, one killed a "
    "healthy training client via `*forkDC*` matching the unrelated `forkDCH`.)"
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}))
sys.exit(0)
PY
exit 0
