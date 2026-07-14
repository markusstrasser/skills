#!/usr/bin/env bash
# pre-commit-no-large-binaries.sh — Reject PDFs, large binaries, and large
# TEXT files (jsonl/csv/etc.) that don't belong in git.
#
# Rationale:
#   - PDFs in git: rejected universally. Canonical store is ~/Projects/corpus/.
#   - Other large binary blobs (.docx, .pptx, .xlsx, .zip, .tar, .tar.gz,
#     .tgz) are almost always a mistake; tracked over a small threshold.
#   - Any file (incl. large TEXT — .jsonl/.csv/.parquet/derived logs) over the
#     generic limit: almost always regenerable data that bloats the pack. This
#     rule was added after intel's *_work_queue.csv / claim_graph_imports.jsonl
#     (9.5–21 MB each, 45 tracked versions ≈ 367 MB) grew the pack daily, unseen
#     by the binaries-only guard (2026-07-14, storage-dossier).
#
# Install:
#   ln -sf ~/Projects/skills/hooks/pre-commit-no-large-binaries.sh \
#          .git/hooks/pre-commit
#
# Bypass (genuine cases like a tiny test fixture, or a real large asset):
#   GIT_ALLOW_BINARIES=1 git commit ...
#
# Size thresholds:
#   Any file (incl. text): > 5 MB (5242880 bytes) — the generic bloat guard
#   PDF: > 1 KB (1024 bytes) — anything larger than a stub
#   Other binaries: > 100 KB (102400 bytes)
#
# Exit codes:
#   0 — no offending files staged
#   1 — at least one offending file staged

set -e

if [[ -n "${GIT_ALLOW_BINARIES:-}" ]]; then
  echo "[pre-commit no-large-binaries] GIT_ALLOW_BINARIES set — skipping" >&2
  exit 0
fi

GENERIC_LARGE_LIMIT=5242880   # 5 MB — catches large regenerable text/data
PDF_LIMIT=1024
BIG_BINARY_LIMIT=102400

staged=$(git diff --cached --name-only --diff-filter=ACMR)
[[ -z "$staged" ]] && exit 0

violations=()

while IFS= read -r path; do
  [[ -z "$path" ]] && continue

  # Size of the staged blob (not the working-tree file).
  size=$(git cat-file -s ":$path" 2>/dev/null || echo 0)
  [[ "$size" -eq 0 ]] && continue

  # Generic large-file guard FIRST — catches large text (jsonl/csv/…) that the
  # type-specific rules below miss. One violation per file (continue after).
  if (( size > GENERIC_LARGE_LIMIT )); then
    violations+=("LARGE $size B  $path")
    continue
  fi

  # PDFs — strict 1KB threshold.
  case "$path" in
    *.pdf|*.PDF)
      if (( size > PDF_LIMIT )); then
        violations+=("PDF  $size B  $path")
      fi
      continue
      ;;
  esac

  # Other binary archives — 100KB threshold.
  case "$path" in
    *.docx|*.DOCX|*.pptx|*.PPTX|*.xlsx|*.XLSX|*.zip|*.ZIP|*.tar|*.TAR|*.tar.gz|*.TAR.GZ|*.tgz|*.TGZ)
      if (( size > BIG_BINARY_LIMIT )); then
        violations+=("BIN  $size B  $path")
      fi
      ;;
  esac
done <<< "$staged"

if (( ${#violations[@]} > 0 )); then
  echo "" >&2
  echo "[pre-commit no-large-binaries] BLOCKED — large binary files staged:" >&2
  echo "" >&2
  for v in "${violations[@]}"; do
    echo "  $v" >&2
  done
  echo "" >&2
  echo "Large/binary data does not belong in git — gitignore it and store the" >&2
  echo "generator + source instead. PDFs -> ~/Projects/corpus/. Large text/data" >&2
  echo "(LARGE rows) is almost always a regenerable derivative (index, log, dump)." >&2
  echo "" >&2
  echo "If this is a genuine exception (tiny test fixture, real large asset), override:" >&2
  echo "  GIT_ALLOW_BINARIES=1 git commit ..." >&2
  echo "" >&2
  exit 1
fi

exit 0
