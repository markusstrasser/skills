#!/usr/bin/env bash
# pretool-dataset-probe-first.sh — Warn on bulk data downloads without a prior probe.
# PreToolUse:Bash hook. Advisory only (exit 0, never exit 2).
#
# Triggers on curl/wget of URLs that look like bulk data files (>10MB likely).
# Suggests:
#   1. Check local SSD corpus first
#   2. curl -I (HEAD) to verify size/liveness
#   3. Use /data-acquisition skill for the probe→stage→register pattern
trap 'exit 0' ERR

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Only flag curl/wget downloads. Skip HEAD-only (-I), already-have-output (-o file exists).
echo "$CMD" | grep -qE '\b(curl|wget)\b' || exit 0

# Skip if it's clearly a HEAD/probe (-I, --head, -sS without output redirect, size check)
echo "$CMD" | grep -qE '\-I\b|--head\b' && exit 0

# Only flag if there's a likely-bulk file extension or known data host in the URL
DATA_EXTS='\.(zip|tar|tar\.gz|tgz|dta|sav|sas7bdat|parquet|csv\.gz|dat|dta\.zip|xlsx\.zip)\b'
DATA_HOSTS='(www2\.census\.gov|meps\.ahrq\.gov|psidonline\.isr\.umich\.edu|simba\.isr\.umich\.edu|nces\.ed\.gov|ipums\.org|bls\.gov/.*data|stlouisfed\.org/fred)'

if echo "$CMD" | grep -qE "$DATA_EXTS|$DATA_HOSTS"; then
    # Check if a probe or local check appeared in recent history (best-effort)
    cat <<EOF >&2
[dataset-probe-first] Bulk data download detected.

Before downloading, confirm:
  1. Not already local:    ls sources/*/data/external/stage3/ | grep -i <dataset>
                           ls /Volumes/SSK1TB/corpus/           | grep -i <source>
  2. URL is live + sized:  curl -sS -I -L '<url>' | grep -E 'HTTP|Content-Length'
  3. Codebook alongside:   fetch matching .pdf/.txt codebook in same pass
  4. Register after stage: /dataset-register <topic> <dataset-id>

See the /data-acquisition skill for the canonical pattern.
(This is advisory — proceed if you've already probed.)
EOF
    # Log trigger for hook-roi tracking
    if command -v "$HOME/Projects/skills/hooks/hook-trigger-log.sh" >/dev/null 2>&1; then
        echo "dataset-probe-first" | "$HOME/Projects/skills/hooks/hook-trigger-log.sh" 2>/dev/null || true
    fi
fi

exit 0
