#!/bin/bash
# PostToolUse:Edit|Write — run pyright on edited Python files (advisory).
# Emits ONLY errors newly introduced by the current edit, by diffing
# against a per-file baseline cached in ~/.cache/claude-pyright-baseline/.
#
# Rationale: pre-existing errors aren't actionable in the current edit
# context — the model can't tell which errors it just caused vs which
# were already there. Diff mode cuts noise ~80% and surfaces real
# regressions cleanly.
#
# First-run-per-file: emits all errors (no baseline to diff against),
# then the baseline is primed. Subsequent runs are deltas.
#
# Fails open: any internal error → exit 0 (silent pass, never blocks).
trap 'exit 0' ERR
INPUT=$(cat)
FILE=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')
[[ "$FILE" != *.py ]] && exit 0
[[ ! -f "$FILE" ]] && exit 0

CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/claude-pyright-baseline"
mkdir -p "$CACHE_DIR" 2>/dev/null || exit 0
KEY=$(printf '%s' "$FILE" | shasum | cut -c1-40)
BASELINE="$CACHE_DIR/$KEY.json"

PYSCRIPT=$(mktemp)
trap 'rm -f "$PYSCRIPT"; exit 0' EXIT ERR
cat > "$PYSCRIPT" << 'PYEOF'
import json
import os
import sys

baseline_path = os.environ.get("BASELINE", "")

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

diags = data.get("generalDiagnostics", [])
def fingerprint(d):
    rng = d.get("range", {}).get("start", {})
    return (
        rng.get("line", 0),
        rng.get("character", 0),
        d.get("message", "").split("\n")[0],
        d.get("rule", ""),
    )

current_errors = [d for d in diags if d.get("severity") == "error"]
current_fps = {fingerprint(d): d for d in current_errors}

baseline_fps = set()
have_baseline = False
if baseline_path and os.path.isfile(baseline_path):
    try:
        with open(baseline_path) as f:
            baseline_fps = {tuple(t) for t in json.load(f)}
        have_baseline = True
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        baseline_fps = set()
        have_baseline = False

if baseline_path:
    try:
        with open(baseline_path, "w") as f:
            json.dump(list(current_fps.keys()), f)
    except OSError:
        pass

if not have_baseline:
    show = current_errors
    header = f"Pyright: {len(show)} error(s) (baseline-primed)"
else:
    new_fps = set(current_fps) - baseline_fps
    show = [current_fps[fp] for fp in current_fps if fp in new_fps]
    if not show:
        sys.exit(0)
    header = f"Pyright: {len(show)} new error(s) (vs cached baseline)"

if not show:
    sys.exit(0)

lines = []
for e in show[:5]:
    r = e.get("range", {}).get("start", {})
    msg = e.get("message", "").split("\n")[0]
    lines.append(f"  L{r.get('line', 0) + 1}: {msg}")
if len(show) > 5:
    lines.append(f"  ... ({len(show) - 5} more)")
summary = header + ":\n" + "\n".join(lines)
print(json.dumps({"additionalContext": summary}))
PYEOF

BASELINE="$BASELINE" pyright --outputjson "$FILE" 2>/dev/null | BASELINE="$BASELINE" python3 "$PYSCRIPT" 2>/dev/null
exit 0
