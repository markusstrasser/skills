# Spirit-Audit Lens (letter-vs-spirit integrity)

Use when the object is a **work-product judged against a stated contract** — an eval verdict, a
backtest/thesis, a pipeline gate, a benchmark, a research claim, a review. Find where the
**letter** is satisfied but the **spirit** (the intent behind the contract) is subverted. This is
an adversarial integrity pass, not a quality rating.

1. **State the contract.** What does the artifact claim to measure/establish, and which rules must
   it honor (drop-rules, blinding, representativeness, ownership, first-dispatch)? That intent is
   the "spirit." Write it in one or two sentences before looking at results.
2. **Scan for the 7 violation classes** — for each, ask "is the letter met while this is subverted?"
   and **quote the exact trace/line**:
   - **Degenerate-pass** — scores well via trivial/empty/boilerplate output or refusing to commit, not substance.
   - **Invalid reference** — the gold/spec/baseline itself violates the contract, is wrong, or leaks the answer → a "failure" against it may be *correct* (the diekstra case).
   - **Failure-scored-as-result** — a transport/process error (empty, errored, partial, timeout) recorded as a legitimate low score, indistinguishable from real underperformance.
   - **Confound** — compared conditions differ in >1 way (model × prompt × transport × config); the effect is attributed to one.
   - **Unreliable adjudicator** — single / non-blind / same-lineage judge; or judges disagree but one number is reported as truth.
   - **Saturated item** — every subject passes (or fails); no discriminative signal, yet counted as if it discriminates.
   - **Leakage** — the subject could see information it shouldn't (gold-only fields, the answer named in the prompt/brief).
3. **For each hit:** name who/what benefits, rate severity, and state the cheapest check that confirms or refutes it.
4. **Separate disclosed tradeoffs from violations.** A limitation acknowledged in the contract (e.g. "public-lifted, contamination disclosed") is letter-honest; flag it only if a downstream decision reads through the disclosure.

Output:
- ranked violations: `class · evidence quote · beneficiary · severity · confirming check`
- what you verified **clean** (so it isn't re-investigated)
- bottom line: is the artifact's headline conclusion safe, or letter-true / spirit-false?

**Dispatch note (the strong form):** run this adversarially via a **different-lineage** model — a
same-lineage auditor shares the blind spots. `scripts/spirit_audit.sh <contract> <artifact>…` fans
out Cursor Composer 2.5 (third-lineage, measured literal-contract-follower) over the artifacts; or
invoke `/critique` with the `composer` axis. Cross-domain examples: an intel thesis (alpha confounded
with beta? lookahead leakage?), a genomics gate (a command-green gate masking a real regression?),
a research memo (cherry-picked evidence = degenerate-pass).
