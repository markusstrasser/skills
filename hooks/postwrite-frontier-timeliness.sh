#!/usr/bin/env bash
# postwrite-frontier-timeliness.sh — Advisory hook checking for pre-frontier model citations.
# Deploy as PostToolUse hook on Write|Edit for research files.
#
# When research files cite papers that used pre-frontier models (GPT-3.5, GPT-4,
# Claude 3/3.5, Gemini 1.x) without a staleness disclaimer, emits a warning.
# This addresses a recurring epistemic failure (3rd occurrence, 2026-03-04).
#
# Mode: advisory only (exit 0). Never blocks.
# Paths: only fires on research-adjacent files.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract file path (fast grep, skip Python for non-matching paths)
FPATH=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"//')

[ -z "$FPATH" ] && exit 0

# Only research-adjacent files
echo "$FPATH" | grep -qE 'docs/|analysis/|research/|entities/|briefs/' || exit 0

# Skip non-prose
case "$FPATH" in
    *.py|*.sh|*.json|*.yaml|*.yml|*.toml|*.sql|*.csv) exit 0 ;;
esac

[ ! -f "$FPATH" ] && exit 0

# Check file content with Python
python3 -c '
import sys, re, os

fpath = sys.argv[1]
try:
    with open(fpath) as f:
        content = f.read()
except Exception:
    sys.exit(0)

# Pre-frontier model patterns (word-boundary matched to avoid false positives)
# These are models whose findings do NOT transfer to current frontier
PRE_FRONTIER = [
    r"\bGPT-3\.5\b",
    r"\bGPT-4\b(?!\.6)",          # GPT-4 but not GPT-4.6 (if it existed)
    r"\bGPT-4o\b",
    r"\bGPT-4-turbo\b",
    r"\bClaude 3\b(?!\.\d)",      # Claude 3 but not Claude 3.5
    r"\bClaude 3\.5\b",
    r"\bClaude[ -]Opus 3\b",
    r"\bClaude[ -]Sonnet 3\b",
    r"\bClaude[ -]Haiku 3\b",
    r"\bHaiku 3\.5\b",
    r"\bSonnet 3\.5\b",
    r"\bOpus 3\b",
    r"\bGemini 1\.0\b",
    r"\bGemini 1\.5\b",
    r"\bGemini[ -]Pro\b(?! [23])",  # Gemini Pro without version 2/3
    r"\bPaLM\b",
    r"\bPaLM-2\b",
    r"\bLLaMA[ -]?2\b",
    r"\bLlama[ -]?2\b",
    r"\btext-davinci\b",
    r"\bcode-davinci\b",
    r"\bGPT-3\b(?!\.5)",          # GPT-3 but not GPT-3.5
]

# Staleness disclaimers (any of these near a model mention = OK)
DISCLAIMERS = [
    r"pre-frontier",
    r"validity uncertain",
    r"not tested on current frontier",
    r"may not transfer",
    r"stale",
    r"older model",
    r"pre-frontier evidence",
    r"superseded",
    r"prior generation",
    r"scale-independent",       # Legitimate exception — finding transfers
    r"architecture.independent", # Legitimate exception
    r"not.*current.*model",
]

disclaimer_pattern = re.compile("|".join(DISCLAIMERS), re.IGNORECASE)

# Find pre-frontier model mentions
found_models = []
for pattern in PRE_FRONTIER:
    for match in re.finditer(pattern, content):
        model_name = match.group()
        start = max(0, match.start() - 300)
        end = min(len(content), match.end() + 300)
        context_window = content[start:end]

        # Check if theres a disclaimer nearby
        if not disclaimer_pattern.search(context_window):
            found_models.append(model_name)

if not found_models:
    sys.exit(0)

# Deduplicate
unique_models = sorted(set(found_models))

# Log to hook telemetry
try:
    import subprocess
    subprocess.run(
        [os.path.expanduser("~/Projects/skills/hooks/hook-trigger-log.sh"),
         "frontier-timeliness", "warn",
         f"{os.path.basename(fpath)}: {", ".join(unique_models)}"],
        capture_output=True, timeout=5
    )
except Exception:
    pass

print(f"TIMELINESS WARNING: {os.path.basename(fpath)} cites pre-frontier models "
      f"without staleness disclaimer: {", ".join(unique_models)}", file=sys.stderr)
print("These models findings may not transfer to current frontier (Opus 4.6, GPT-5.4, Gemini 3.1).", file=sys.stderr)
print("Add disclaimer: \"pre-frontier evidence, validity uncertain\" or note \"scale-independent\" if the finding transfers.", file=sys.stderr)
sys.exit(0)
' "$FPATH" 2>&1 >&2

exit 0
