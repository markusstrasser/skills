#!/bin/bash
# PostToolUse:Edit|Write — run pyright on edited Python files (advisory)
# Fails open: any error → exit 0 (no output = hook passes)
trap 'exit 0' ERR
INPUT=$(cat)
FILE=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')
[[ "$FILE" != *.py ]] && exit 0
[[ ! -f "$FILE" ]] && exit 0

PYSCRIPT=$(mktemp)
trap 'rm -f "$PYSCRIPT"; exit 0' EXIT ERR
cat > "$PYSCRIPT" << 'PYEOF'
import sys, json
data = json.load(sys.stdin)
diags = data.get('generalDiagnostics', [])
errors = [d for d in diags if d.get('severity') == 'error']
if errors:
    lines = []
    for e in errors[:5]:
        r = e.get('range', {}).get('start', {})
        msg = e.get('message', '').split('\n')[0]
        lines.append(f"  L{r.get('line', 0) + 1}: {msg}")
    summary = f"Pyright: {len(errors)} error(s):\n" + "\n".join(lines)
    print(json.dumps({"additionalContext": summary}))
PYEOF

pyright --outputjson "$FILE" 2>/dev/null | python3 "$PYSCRIPT" 2>/dev/null
exit 0
