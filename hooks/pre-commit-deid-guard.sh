#!/usr/bin/env bash
# pre-commit-deid-guard.sh — fail-closed de-identification gate for research/memo commits.
#
# WHY: in the substrate→genomics dogfood bug-hunt, de-identified memos must refer to
# subjects as "subject-A/B/C/D", NEVER by name or sample-ID. A *manual* grep before each
# commit was the only guard — and it was defeated THREE TIMES in one session (2026-06-29)
# by the auto-`[wip]` checkpoint (stop-uncommitted-warn.sh), which commits in-flight memos
# between agent-return and the manual scan. Real PHI (a clinical condition, an age, a
# genotype, neuropsychiatric PRS) entered git history before it could be scrubbed.
# Per the CLAUDE.md pair-rule, a recurring discipline failure guarded by a manual check
# wants a HOOK. The auto-checkpoint commits with a bare `git commit` (no --no-verify,
# verified), so a git-native pre-commit hook is the ONE place that covers every commit
# path — manual, tool-issued, AND the checkpoint.
#
# SCOPE (deliberately NAME-scoped, never value-scoped — see the steward proposal
# 2026-06-29-deid-precommit-hook.md): blocking generic genotype/percentile PATTERNS
# (rs\d+, \d+\.\dth) is iatrogenic — rs12913832 and "21.6th" are legitimate general
# science. The clean, low-false-positive signal is a SUBJECT'S NAME / SAMPLE-ID inside a
# de-identified memo (which should say "the subject"). Fail-closed is the safe direction:
# a false block costs one DEID_GATE_OFF=1; a false allow is an irreversible privacy harm.
#
# OPT-IN: self-skips unless <repo-root>/.deid-guard.env exists (mirrors
# pre-commit-protected-paths.sh reading .precommit-guards.env). So agent-infra / intel /
# other dispatcher repos are unaffected until they drop a config. Substrate ships one.
#
# Config (.deid-guard.env, shell-sourced at repo root):
#   DEID_TOKEN_RE='syn2sr|syn3sr|jw|markus'         # alternation; matched word-bounded, case-insensitive
#   DEID_PATH_RE='docs/research/kg-verification/|bughunt|hand-?off'   # ERE on staged path
#
# Exit: 0 pass / skip · 1 BLOCK (subject token found in a scoped staged file).
# Bypass: DEID_GATE_OFF=1 (single-commit escape) or the chain-wide GIT_ALLOW_GUARD_BYPASS=1.
# Fails OPEN on its own internal errors — a broken de-id hook must never block ALL commits.

set -uo pipefail
trap 'exit 0' ERR   # fail-open on unexpected error; the explicit `exit 1` below is the only block

[ "${DEID_GATE_OFF:-0}" = "1" ] && exit 0
[ "${GIT_ALLOW_GUARD_BYPASS:-0}" = "1" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
CFG="$REPO_ROOT/.deid-guard.env"
[ -f "$CFG" ] || exit 0   # opt-in: no config → not a de-id-guarded repo → skip

# Defaults (overridden by the sourced config)
DEID_TOKEN_RE='syn2sr|syn3sr|jw|markus'
DEID_PATH_RE='docs/research/kg-verification/|bughunt|hand-?off'
# shellcheck disable=SC1090
. "$CFG" 2>/dev/null || exit 0
[ -n "$DEID_TOKEN_RE" ] || exit 0

# Staged, non-deleted files only.
HITS=""
while IFS= read -r f; do
    [ -n "$f" ] || continue
    printf '%s\n' "$f" | grep -qE "$DEID_PATH_RE" || continue
    # Grep the STAGED blob (exactly what enters history), word-bounded, case-insensitive.
    # Print ONLY file:line:token — never the surrounding line (it may carry the value we
    # are protecting; echoing it would re-leak into terminal/logs).
    while IFS=: read -r lineno _; do
        [ -n "$lineno" ] || continue
        tok="$(git show ":$f" 2>/dev/null | sed -n "${lineno}p" \
              | grep -iowE "$DEID_TOKEN_RE" | head -1)"
        HITS="${HITS}  ${f}:${lineno}: subject token <${tok:-?}>"$'\n'
    done < <(git show ":$f" 2>/dev/null | grep -inwE "$DEID_TOKEN_RE" | cut -d: -f1 | sort -un | sed 's/$/:/')
done < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)

if [ -n "$HITS" ]; then
    {
        echo "BLOCKED (de-id gate): a subject name / sample-ID appears in a staged research/memo file."
        echo "These artifacts must refer to subjects as subject-A/B/C/D — never by name or sample-ID."
        printf '%s' "$HITS"
        echo "Scrub the identifier(s) (replace with subject-X / 'the subject'), re-stage, recommit."
        echo "If this is a genuine non-subject use, bypass once: DEID_GATE_OFF=1 git commit ..."
    } >&2
    ~/Projects/skills/hooks/hook-trigger-log.sh "deid-guard" "block" "$(printf '%s' "$HITS" | tr '\n' ';' | cut -c1-120)" 2>/dev/null || true
    exit 1
fi
exit 0
