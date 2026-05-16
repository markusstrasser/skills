#!/usr/bin/env bash
# posttool-reception-payload-llm.sh — Advisory LLM check on reception/annotations writes.
#
# Hybrid hook: lexical filter first (cheap), Haiku call only on survivors.
#
#   1. Fire on Write|Edit only when path matches src/lib/data/.+(reception|relations|annotations|notes)\.ts$
#   2. Diff the new file against HEAD; extract `note:` / `body:` / `title:` strings added or modified
#   3. If <2 entries changed → exit (regex layer already covers these, LLM adds no value)
#   4. Otherwise: call Haiku via Anthropic API asking "which of these notes is restatement vs payload?"
#   5. Print restatement candidates as advisory warnings, exit 0
#
# Cost: ~$0.001 per fire (Haiku, ~2K input + ~500 output tokens). Fires only on
# substantive reception edits — a few times per editing session, not per keystroke.
#
# Requires: ANTHROPIC_API_KEY in env. Falls back to silent exit if missing.

set -u
trap 'exit 0' ERR

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null)
[[ -z "$FILE_PATH" ]] && exit 0
[[ ! -f "$FILE_PATH" ]] && exit 0

# Path gate — only reception/annotations data files.
case "$FILE_PATH" in
  */src/lib/data/*/reception.ts|\
  */src/lib/data/*/relations.ts|\
  */src/lib/data/*/annotations.ts|\
  */src/lib/data/*/notes.ts) ;;
  *) exit 0 ;;
esac

# Opt-out marker.
grep -q '// reception-payload-llm:skip' "$FILE_PATH" 2>/dev/null && exit 0

# Need API key. Silent exit if missing — don't fail open with a warning, that's noisy.
[[ -z "${ANTHROPIC_API_KEY:-}" ]] && exit 0

# Diff against HEAD: get added/modified lines that look like `note:` / `body:` strings.
CHANGED=$(python3 - "$FILE_PATH" <<'PY' 2>/dev/null
import subprocess, re, sys
from pathlib import Path
path = sys.argv[1]
# Get git root and relative path
try:
    root = subprocess.check_output(["git", "-C", str(Path(path).parent), "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL).decode().strip()
    rel = str(Path(path).resolve().relative_to(root))
except Exception:
    sys.exit(0)
# Diff against HEAD
try:
    diff = subprocess.check_output(
        ["git", "-C", root, "diff", "HEAD", "--", rel],
        stderr=subprocess.DEVNULL,
    ).decode("utf-8", errors="replace")
except Exception:
    sys.exit(0)
# Extract added lines that contain a note/body/title field with quoted prose.
hits = []
field_re = re.compile(r"^\+\s*(note|body|title|imageAlt)\s*:\s*['\"]([^'\"]{30,})['\"]")
for line in diff.splitlines():
    m = field_re.match(line)
    if m:
        field, text = m.group(1), m.group(2)
        hits.append(f"{field}: {text}")
# Cap at 10 entries — anything more is a wholesale rewrite, not a focused edit.
print("\n".join(hits[:10]))
PY
)

# Less than 2 entries changed → skip. The cheap lint covers single-line edits.
n_changed=$(echo "$CHANGED" | grep -c '^.\+$' 2>/dev/null || echo 0)
[[ "$n_changed" -lt 2 ]] && exit 0

# Call Haiku via direct HTTPS to the messages endpoint.
RESPONSE=$(python3 - <<PY 2>/dev/null
import os, json, urllib.request, sys

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    sys.exit(0)

entries = """$CHANGED"""

prompt = f"""You are reviewing reception notes for a primary-text reader (Shakespeare, Bible, etc.). Each entry sits next to a painting or video clip. A good note adds payload the reader cannot see — date, artist, source-text moment depicted, staging history, technical detail. A bad note is restatement — it describes what's in the image or says something abstract about the work.

For each entry below, judge: payload (adds info) | restatement (says what's already visible) | unclear (depends on the actual image, can't tell from text alone).

Output ONLY a JSON array of objects with shape {{"i": <0-based index>, "verdict": "payload" | "restatement" | "unclear", "why": "<6-word reason>"}}. Skip entries you'd verdict 'payload' — only emit restatement and unclear. If all are payload, output [].

Entries:
{entries}
"""

req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 800,
        "messages": [{"role": "user", "content": prompt}],
    }).encode(),
    headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    },
)
try:
    with urllib.request.urlopen(req, timeout=12) as resp:
        body = json.loads(resp.read())
    content = body.get("content", [])
    text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
    # Extract the JSON array — model sometimes wraps in prose.
    import re as _re
    m = _re.search(r"\[\s*(?:\{.*?\}\s*,?\s*)*\]", text, _re.DOTALL)
    if not m:
        sys.exit(0)
    parsed = json.loads(m.group(0))
    if not parsed:
        sys.exit(0)
    lines = entries.split("\n")
    for finding in parsed:
        i = finding.get("i")
        verdict = finding.get("verdict")
        why = finding.get("why", "")
        if not isinstance(i, int) or i < 0 or i >= len(lines):
            continue
        if verdict not in ("restatement", "unclear"):
            continue
        excerpt = lines[i][:80]
        print(f"{verdict.upper()}: {excerpt!r} — {why}")
except Exception:
    sys.exit(0)
PY
)

if [[ -n "$RESPONSE" ]]; then
  ~/Projects/skills/hooks/hook-trigger-log.sh reception-payload-llm advise "$FILE_PATH" > /dev/null 2>&1 || true
  echo "" >&2
  echo "Reception payload check ($(basename "$FILE_PATH")) — Haiku semantic review:" >&2
  while IFS= read -r line; do
    [[ -n "$line" ]] && echo "  ! $line" >&2
  done <<< "$RESPONSE"
  echo "  (Advisory. Quote sentence, propose concrete fix, author decides per feedback_slop_words_are_signals.md.)" >&2
  echo "  (silence per-file with // reception-payload-llm:skip)" >&2
fi

exit 0
