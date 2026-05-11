#!/usr/bin/env bash
# pre-commit-no-large-binaries.sh — Reject PDFs and large binary artefacts.
#
# Rationale:
#   - PDFs in git: rejected universally (see ~/Projects/agent-infra/.claude/
#     plans/2026-05-11-shared-papers-store.md anti-patterns). Canonical store
#     is ~/Projects/papers/.
#   - Other large binary blobs (.docx, .pptx, .xlsx, .zip, .tar, .tar.gz,
#     .tgz) are almost always a mistake; tracked over a small threshold.
#
# Install:
#   ln -sf ~/Projects/skills/hooks/pre-commit-no-large-binaries.sh \
#          .git/hooks/pre-commit
#
# Bypass (genuine cases like a tiny test fixture):
#   GIT_ALLOW_BINARIES=1 git commit ...
#
# Size thresholds:
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
  echo "PDFs do not belong in git. Canonical paper store:" >&2
  echo "  ~/Projects/papers/" >&2
  echo "" >&2
  echo "See ~/Projects/agent-infra/.claude/plans/2026-05-11-shared-papers-store.md" >&2
  echo "(anti-patterns: 'PDF in git. Period.')" >&2
  echo "" >&2
  echo "If this is a genuine exception (tiny test fixture, etc.), override:" >&2
  echo "  GIT_ALLOW_BINARIES=1 git commit ..." >&2
  echo "" >&2
  exit 1
fi

exit 0
