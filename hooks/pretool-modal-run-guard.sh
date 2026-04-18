#!/usr/bin/env bash
# pretool-modal-run-guard.sh — Block invalid Modal launches before the image
# builds. Catches the silent `ephemeral_disk out of bounds` / `gpu + nonpreemptible`
# / other Modal-API-rejected configs that otherwise cost 2-5 min of image-build
# time + a partial image layer on every bad launch.
#
# Runs on PreToolUse:Bash when the command looks like `modal run <script>`.
# Parses the target script with Python AST and validates Modal config.

trap 'exit 0' ERR

INPUT=$(cat)

python3 -c '
import sys, json, re, ast, os

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = data.get("tool_name", "")
if tool != "Bash":
    sys.exit(0)

cmd = data.get("tool_input", {}).get("command", "")
if not cmd:
    sys.exit(0)

# Match `modal run`, `uv run modal run`, `python -m modal run`. Extract the
# first .py file positional argument after `run` / `run::<fn>` / `--detach`.
if not re.search(r"\bmodal\s+run\b", cmd):
    sys.exit(0)

# Simple tokenizer — tolerates ``::fn`` suffix and `--detach` flag.
tokens = cmd.split()
# Find token starting with scripts/ or ending with .py
target = None
for t in tokens:
    tt = t.split("::")[0]  # strip ::function
    if tt.endswith(".py"):
        target = tt
        break

if not target:
    sys.exit(0)

cwd = data.get("cwd", "")
if not os.path.isabs(target):
    target = os.path.join(cwd, target)

if not os.path.isfile(target):
    sys.exit(0)

try:
    src = open(target).read()
    tree = ast.parse(src)
except Exception:
    sys.exit(0)

# Walk the AST for @app.cls(...) / @app.function(...) decorators; collect kwargs.
findings = []

def _kw_value(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        return -node.operand.value
    if isinstance(node, ast.Name):
        return f"<name:{node.id}>"
    return None

for node in ast.walk(tree):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        continue
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        fn = dec.func
        name = ""
        if isinstance(fn, ast.Attribute):
            name = fn.attr
        elif isinstance(fn, ast.Name):
            name = fn.id
        if name not in ("function", "cls"):
            continue

        kwargs = {}
        for kw in dec.keywords:
            if kw.arg is None:
                continue
            kwargs[kw.arg] = _kw_value(kw.value)

        line = dec.lineno

        # Rule 1: ephemeral_disk bounds [524288, 3145728] MiB
        ed = kwargs.get("ephemeral_disk")
        if isinstance(ed, int) and not (524288 <= ed <= 3145728):
            findings.append(
                f"{os.path.basename(target)}:{line} @app.{name} has "
                f"ephemeral_disk={ed} — Modal requires [524288, 3145728] MiB. "
                f"Use ephemeral_disk=524288 (512 GB min)."
            )

        # Rule 2: nonpreemptible=True + gpu=... is invalid (Modal rejects at launch)
        np_val = kwargs.get("nonpreemptible")
        gpu_val = kwargs.get("gpu")
        if np_val is True and gpu_val not in (None, False):
            findings.append(
                f"{os.path.basename(target)}:{line} @app.{name} has "
                f"nonpreemptible=True AND gpu={gpu_val!r} — Modal does not "
                f"support nonpreemptible for GPU functions. Drop one."
            )

if findings:
    out = {
        "decision": "block",
        "reason": "MODAL LAUNCH BLOCKED — invalid config in target script:\n\n"
                  + "\n".join(f"  - {f}" for f in findings)
                  + "\n\nFix in the script, then re-run.",
    }
    print(json.dumps(out))
    sys.exit(0)
' 2>/dev/null

exit 0
