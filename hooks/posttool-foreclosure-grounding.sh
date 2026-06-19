#!/bin/bash
# PostToolUse hook (Write|Edit) — GROUND foreclosure/finality verdicts before they drive decisions.
# Transferable fix for the proxy-as-truth class (epistemic #8): a feasibility/foreclosure verdict
# ("dead end", "infeasible", "tapped out", "over on all three", "no lever") drawn from a PROXY
# (projection / README / prior summary) when the PRINCIPAL (source code, a measured row) was cheap
# and available — and not reconciled against recorded facts that contradicted it.
# Origin: 2026-06-19 hutter — "fx3-repro is a dead end" was projection-grounded; a 5-min source read
# (fx3-src == fx2-src byte-identical) overturned it. Cost ~€13 + ~2 days. The narrow fix is "read
# source"; THIS is the transferable architecture: fire on the WRITE of finality language to a
# decision surface (so it can't be skimmed past like an hourly self-question), demand the principal
# check or a downgrade.
#
# Fires ONLY when NEWLY-ADDED text (Edit new_string / Write content) contains strong finality
# language AND the target is a decision surface. Advisory only (exit 0), NEVER blocks. Fail-safe:
# any error → silent exit 0. Cross-project by design (the class is project-independent).
set -o pipefail 2>/dev/null
INPUT=$(cat)

# --- file_path + the ADDED text (not the whole file → fires on NEW verdicts, not pre-existing) ---
EXTRACT=$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin); ti=d.get("tool_input",{})
    print(ti.get("file_path",""))
    print("\x1e")  # record sep
    print((ti.get("new_string","") or "") + "\n" + (ti.get("content","") or ""))
except Exception:
    pass
' 2>/dev/null) || exit 0
[ -z "$EXTRACT" ] && exit 0
FPATH=$(printf '%s' "$EXTRACT" | sed -n '1p')
ADDED=$(printf '%s' "$EXTRACT" | sed '1,/\x1e/d')

# --- decision-surface filter (where strategic verdicts land; generic across projects) ---
printf '%s' "$FPATH" | grep -qiE '(\.claude/(checkpoint|.*-ack)|results/|decisions-pending/|proposals-pending/|findings|/(LEVERS|MEMORY|IDEAS|STRATEGY|PRIZES)\.md)' || exit 0

# --- strong finality / foreclosure language (kept tight to limit false positives) ---
printf '%s' "$ADDED" | grep -qiE 'dead[ -]?end|infeasible|\bimpossible\b|tapped[ -]?out|ruled out|not winnable|won.t work|no (viable |real )?(lever|path)|over on all|can.?t be (done|won|beaten|closed)|genuinely (dead|stuck)|no way (to|forward)' || exit 0

MSG="⚠ FORECLOSURE VERDICT written to a decision surface (${FPATH##*/}). Before it drives a decision (pivot/abandon/stop): is it grounded in the PRINCIPAL check — source file:line or a measured ledger row — or a PROXY (projection/README/prior summary)? Does it CONTRADICT any recorded lever? Cite the principal source, or downgrade to a pre-registered probe. (proxy-as-truth #8; 2026-06-19 fx3 'dead end' was projection-grounded — a 5-min source read overturned it.) For a consequential verdict: route through /critique (repo premise-scout falsifies premises) or a fresh-eyes-review grounding pass."
SAFE_MSG=$(printf '%s' "$MSG" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null)
[ -n "$SAFE_MSG" ] && echo "{\"additionalContext\": ${SAFE_MSG}}"
exit 0
