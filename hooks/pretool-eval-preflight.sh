#!/bin/bash
# pretool-eval-preflight.sh — PreToolUse:Bash gate for eval runs.
#
# Goal: stop the recurring "ran the eval, trusted the aggregate, committed a wrong
#   verdict, operator had to say 'check the traces'" failure (2026-06-13 phenome,
#   2026-06-14 composer — both overturned post-hoc). Forces a conscious confirm of
#   the eval pre-flight + trace-audit pre-commitments BEFORE the run script fires.
# blast_radius: shared (eval skill domain) — piloted in the evals project first.
# Verifier: the eval-skill Phase 4.5 trace-audit gate + this ack artifact.
#
# Mechanism: fires ONLY when the command runs an eval-runner script (run*/judge*/
#   dispatch-arm) whose directory contains an EXPERIMENT.md (= a real eval). If no
#   <evaldir>/.preflight-ack exists, BLOCK (exit 2) with the checklist. The agent
#   confirms by writing the ack (a per-item artifact, auditable). One confirm per
#   eval dir; subsequent runs pass. Fails OPEN on any ambiguity (conservative).

INPUT=$(cat)

CMD=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | .command // ""' 2>/dev/null || true)
ENV_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[ -z "$CMD" ] && exit 0

# Resolve the eval dir + whether this is an eval run. Conservative: must match an
# eval-runner script name AND that script's dir must contain EXPERIMENT.md.
EVAL_DIR=$(CMD="$CMD" ENV_CWD="$ENV_CWD" python3 - <<'PY' 2>/dev/null || true
import os, re, shlex
cmd = os.environ.get("CMD", "")
cwd = os.environ.get("ENV_CWD") or os.getcwd()

# Honor an explicit `cd <dir> && ...` prefix when resolving relative script paths.
m = re.search(r'\bcd\s+([^\s&;|]+)', cmd)
if m:
    cand = os.path.expanduser(m.group(1))
    cwd = cand if os.path.isabs(cand) else os.path.normpath(os.path.join(cwd, cand))

try:
    toks = shlex.split(cmd)
except ValueError:
    toks = cmd.split()

# Eval-runner script names (the dispatch/scoring entry points).
RUNNER = re.compile(r'(^|/)(run[\w-]*|judge[\w-]*|score|dispatch-arm|dispatch-cursor-arm)\.(py|sh)$')
for t in toks:
    if RUNNER.search(t):
        d = os.path.dirname(t)
        d = os.path.expanduser(d) if d else cwd
        if not os.path.isabs(d):
            d = os.path.normpath(os.path.join(cwd, d))
        if os.path.isfile(os.path.join(d, "EXPERIMENT.md")):
            print(d)
            break
PY
)

# Not an identifiable eval run → fail open.
[ -z "$EVAL_DIR" ] && exit 0
[ -d "$EVAL_DIR" ] || exit 0

# Already confirmed for this eval → pass.
[ -f "$EVAL_DIR/.preflight-ack" ] && exit 0

cat >&2 <<EOF
EVAL PRE-FLIGHT — confirm before running '$EVAL_DIR'.
Recurring failure this prevents: trust the aggregate, skip the traces, commit a wrong verdict.
Think through each (then write the ack to proceed):

  DESIGN
   1. Construct + CONSUMER named? (what decision this settles, who consumes the verdict)
   2. Prior art checked (Phase 0 dedup — not already run)?
   3. Decision rule + prediction PRE-REGISTERED before results exist?
   4. Confounds: do compared conditions differ in >=2 ways? If yes you can't attribute — name them.
   5. STATS: N+power (MDE for the gap you need, ~1000 items for 3pp) · SE+n on every decision number
      (CLT, NOT Bernoulli on F1/partial/judge) · compare PAIRED on the same items · >=2 seeds, NO
      single-run headline · clustered SE if items are grouped · discrimination probe separates good/bad?
   6. Judges (if any): blind to identity, neutral-family, GOLD_INVALID escape, NOT leading-phrased?
   7. Gold validity: does the gold honor the task's OWN contract (drop/keep rules)? Absence != negative.
   8. No gold leak: the SUT prompt can't see gold-only fields.

  TRACE-AUDIT PRE-COMMIT (you commit NOW — enforced at verdict by eval-skill Phase 4.5)
   9. Read EVERY outlier trace + >=1 trace/arm before averaging/concluding. A 0/perfect score or a
      tiny/empty output is a TRIGGER to read, not a data point.
  10. Confirm every arm appears in the OUTPUT tables (hardcoded model lists silently drop new arms).
  11. Report distribution/range + inter-judge agreement — never launder one judge's number into a verdict.
  12. Traces persisted for re-audit.

To proceed, record your answers and confirm:
  cat > "$EVAL_DIR/.preflight-ack" <<'ACK'
  preflight confirmed <date> — <one line per non-obvious item, esp. confounds (4) + gold validity (7)>
  ACK
(One confirm per eval dir. Genuinely consider each — the ack is auditable in git/review.)
EOF
exit 2
