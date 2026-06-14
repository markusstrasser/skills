#!/bin/bash
# spirit_audit.sh — run the spirit-audit lens (lenses/spirit-audit.md) adversarially over a
# work-product, using a DIFFERENT-lineage model (Cursor Composer 2.5, a measured literal-contract-
# follower) so the auditor doesn't share the author's blind spots. General: works on any artifact
# judged against a contract — eval traces, a backtest, a pipeline gate, a benchmark, a research memo.
#
# Usage:
#   spirit_audit.sh <contract_file> <artifact_file>...        # audit -> stdout
#   spirit_audit.sh -o out.md <contract_file> <artifact>...   # audit -> file
#   For many artifacts, run several in parallel:  for a in dir/*; do spirit_audit.sh -o "$a.audit" spec "$a" & done; wait
#
# The <contract_file> states what the artifact claims to measure/establish and the rules it must
# honor (the "spirit"). The artifacts are the traces/results/outputs to audit against it.
set -u
OUT=""
[ "${1:-}" = "-o" ] && { OUT="$2"; shift 2; }
[ "$#" -lt 2 ] && { echo "usage: spirit_audit.sh [-o out.md] <contract_file> <artifact_file>..." >&2; exit 2; }
CONTRACT="$1"; shift
[ -f "$CONTRACT" ] || { echo "contract file not found: $CONTRACT" >&2; exit 2; }

PROMPT='You are an ADVERSARIAL integrity auditor. The CONTRACT below states what this work-product claims to measure/establish and the rules it must honor. The ARTIFACTS are what actually happened. Find where the LETTER of the contract is satisfied but its SPIRIT is subverted. Hunt for these 7 classes, quoting the EXACT trace/line for each:
1. DEGENERATE-PASS — scores/passes via trivial/empty/boilerplate output or refusing to commit, not real substance.
2. INVALID-REFERENCE — the gold/spec/baseline itself violates the contract, is wrong, or leaks the answer; a "failure" against it may be CORRECT.
3. FAILURE-SCORED-AS-RESULT — a transport/process error (empty, errored, partial, timeout) recorded as a legitimate low score, indistinguishable from real underperformance.
4. CONFOUND — compared conditions differ in MORE THAN ONE way; the effect is attributed to one.
5. UNRELIABLE-ADJUDICATOR — single / non-blind / same-lineage judge, or judges disagree but one number is reported as truth.
6. SATURATED-ITEM — every subject passes (or fails); no discriminative signal, yet counted as if it discriminates.
7. LEAKAGE — the subject could see information it should not (gold-only fields, the answer named in the prompt/brief).
For EACH finding: quote the trace, label it [1-7], name WHO/what benefits, rate severity HIGH/MED/LOW, and give the cheapest confirming check. Separate disclosed tradeoffs (letter-honest) from real violations. End with what you verified CLEAN and a one-line bottom line: is the headline conclusion safe, or letter-true / spirit-false? Be skeptical and concrete — vague suspicion is noise. Rank most-severe first.'

CTX=$(mktemp)
trap 'rm -f "$CTX"' EXIT
printf '===== CONTRACT (the intent + rules to honor) =====\n' >> "$CTX"
head -c 45000 "$CONTRACT" >> "$CTX"
for f in "$@"; do
  [ -f "$f" ] && { printf '\n\n===== ARTIFACT: %s =====\n' "$f" >> "$CTX"; head -c 45000 "$f" >> "$CTX"; }
done

if [ -n "$OUT" ]; then
  timeout 600 llmx chat -p cursor -m composer-2.5 -f "$CTX" -o "$OUT" "$PROMPT"
  echo "spirit-audit -> $OUT"
else
  timeout 600 llmx chat -p cursor -m composer-2.5 -f "$CTX" "$PROMPT"
fi
