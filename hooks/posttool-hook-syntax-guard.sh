#!/usr/bin/env bash
# posttool-hook-syntax-guard.sh — EDIT-TIME syntax gate for hook scripts.
#
# Companion to validate-changed-hooks.sh (the COMMIT gate). That gate validates
# STAGED content, but a hook executes from the WORKING TREE the instant it is
# saved — before any commit. So an Edit/Write that introduces a parse error into
# a shared hook is fail-CLOSED and blocks tool handling across EVERY session,
# with no gate between the edit and the breakage. (Lived it 2026-06-28: a prose
# apostrophe inside a `python3 -c '...'` body in pretool-f16-midwrite-crawl-guard.sh
# closed the shell quote → bash parsed the python as shell → "syntax error near (`('"
# → ALL Bash blocked until fixed. The commit gate never fired; the break was never
# committed.) This hook closes that window: it fires on PostToolUse:Edit|Write and
# syntax-checks the just-written working-tree file, surfacing the break on the very
# edit that caused it.
#
# Fail-open by construction: not a hook path / unknown kind / our own error → exit 0.
# Only a genuine parse failure of a recognized hook script emits exit 2.

INPUT="${CLAUDE_TOOL_INPUT:-$(cat)}"

# Cheap prefilter: skip the python spawn unless the edit plausibly touches a hook.
case "$INPUT" in
    *hooks/*) ;;
    *) exit 0 ;;
esac

HOOKGUARD_INPUT="$INPUT" python3 <<'PYEOF'
import os, sys, json, re, shutil, subprocess

try:
    data = json.loads(os.environ.get("HOOKGUARD_INPUT") or "{}")
except Exception:
    sys.exit(0)

fp = (data.get("tool_input") or {}).get("file_path") or ""
if not fp or not os.path.isfile(fp):
    sys.exit(0)

# Only hook scripts: under a hooks/ , .claude/hooks/ , or .githooks/ directory.
if not re.search(r"(^|/)(\.githooks|hooks|\.claude/hooks)/", fp):
    sys.exit(0)

low = fp.lower()
kind = None
if low.endswith((".sh", ".bash")):
    kind = "sh"
elif low.endswith(".zsh"):
    kind = "zsh"
elif low.endswith(".py"):
    kind = "py"
else:
    try:
        with open(fp, encoding="utf-8", errors="replace") as fh:
            first = fh.readline()
    except Exception:
        sys.exit(0)
    if "python" in first:
        kind = "py"
    elif "zsh" in first:
        kind = "zsh"
    elif "bash" in first or "sh" in first:
        kind = "sh"
if kind is None:
    sys.exit(0)


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return r.returncode, (r.stderr or r.stdout or "")
    except Exception:
        return 0, ""  # fail-open: never block on our own failure


rc, err = 0, ""
if kind == "sh":
    rc, err = run(["bash", "-n", fp])
elif kind == "zsh":
    # bash -n false-blocks valid zsh; skip if zsh absent rather than misfire.
    if shutil.which("zsh"):
        rc, err = run(["zsh", "-n", fp])
    else:
        sys.exit(0)
elif kind == "py":
    rc, err = run([sys.executable, "-c",
                   "import sys; compile(open(sys.argv[1]).read(), sys.argv[1], 'exec')", fp])

if rc != 0:
    lines = "".join("    " + ln + "\n" for ln in err.strip().splitlines()[:8])
    sys.stderr.write(
        "BLOCKED (hook-syntax): the hook you just edited does NOT parse:\n"
        "  " + fp + "\n" + lines +
        "A hook runs from the WORKING TREE the instant it is saved — a parse error here is\n"
        "fail-CLOSED and blocks tool handling across EVERY session until fixed. Fix it NOW\n"
        "before any other action. For a `python3 -c '...'` body, a prose apostrophe closes the\n"
        "shell quote — prefer a quoted heredoc:  python3 <<'PYEOF' ... PYEOF\n"
    )
    sys.exit(2)
sys.exit(0)
PYEOF
