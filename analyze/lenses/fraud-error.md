# Fraud-vs-Error Lens

Use when a claim, dataset, poll, paper, audit or account may be fabricated,
falsified or misrepresented, or when someone else's claim says it was. Run
hypotheses-ach for the ranking; this lens supplies the slots and the tests.

The default rival is misreading, not invention. In the operator's own bookmark
fact-checks (2026-10-17 and 10-29, plus the 11-02 election audit; ~71 graded
errors), misreading a real primary record caused about two thirds of them.
Outright fabrication and recycled media together caused about one in six.

1. **Read the record's own noun and rung.** Write the quantity the source
   actually measured ("nonconsensual contact", "flagged", "charged", "imputed")
   and its status rung: allegation < charge < conviction; flag < confirmed <
   ballot cast; "may be as many as" < count. A verdict word may not climb above
   the record's rung.
2. **Expect the vetting funnel.** Match-based flag counts shrink by one to
   three orders of magnitude on verification (Florida 2012: ~180,000 flagged →
   ~2,600 → 85 removed; NJ: DHS 35,152 → ~6,600 registered → ~400 voted). With
   no confirmed-stage count, report the flag count as an upper bound.
3. **Check each attached link separately.** A true anchor event transfers no
   credibility to the motives, steps, totals or causes added to it.
4. **Ask for the raw record, not the summary.** Fabricators aiming to be
   believed copy the consensus, so plausibility and agreement with other
   sources are not evidence that data is real. Wedgewood's fake polls (Oct 2026)
   passed NYT, Silver and DDHQ vetting until FiftyPlusOne requested respondent
   files and found IDs that didn't match the vendor's format. LLM "silicon"
   respondents match the toplines but miss real joint answer profiles
   (arXiv:2610.30900). Expert reviewers sort AI-forged blot and xenograft images
   at chance (50.5%, doi 10.2196/100710). Test at the level the fabricator
   didn't model: IDs, timestamps, joint profiles, image files, instrument logs.
5. **Look for data that is too clean.** Real data carry noise, absences and
   granularity limits. Checks:
   - **GRIM:** a mean of integer data must equal k/N (Brown & Heathers 2016).
   - **Carlisle:** randomized baselines that are too similar or too different
     (Carlisle 2017).
   - **Impossible records:** perfect attendance, entries dated after the
     observation, claims for decedents or people abroad (a death-index join).
   - **Election fingerprints:** a turnout and vote-share cluster near 100/100
     (Klimek 2012). A lopsided vote share alone is not the signature.
   - **Clustering:** unresolvable references concentrate in a few papers and
     problem figures in a few authors, so one hit raises the prior on the rest
     of the same source (PNAS doi 10.1073/pnas.2623869123; Bik 2016).
6. **Find the least-verified input's share.** Fraud and error both concentrate
   where verification is thinnest. One fake poll carried about half of
   Mississippi's average. Ask what share of the conclusion rests on the newest,
   least-tracked or self-reported source.
7. **Separate targeting from prevalence.** "15 of 15 audited were fraud"
   measures the precision of the rule that picked the 15. Prevalence needs a
   random audit sample.
8. **Treat implausibility as a likelihood, not a verdict.** Weight it by that
   channel's base rate of error. Independent, convergent reports of something
   implausible should move you: early HIV case histories were dismissed as
   lies. A single unsourced rate several times its known base rate should not.
   A record system that lacks the field (the IRS has no race field) means any
   split by that field is someone's imputation.
9. **Separate process failure from a falsified outcome.** Unsigned tapes, stale
   rolls and missing images are failures of process. Before calling fraud, find
   an outcome measure that does not pass through the failed record, such as a
   hand count, a death-index join or an independent recount.
10. **Don't grade truth from wording.** Automated verbal deception detection
    tops out near 74% pooled accuracy (95% CI 71–77%, 3,653 models; LLMs
    didn't raise it), and lower out of sample (arXiv:2610.12118). Obfuscated
    prose is a weak prior at most. Spend the effort on records.
11. **Effort is not accuracy.** "A billion tokens" or "a million cases combed"
    says nothing about error rate. Ask for the labeler's hit rate on a
    hand-coded or planted-flaw sample: LLM reviewers caught 17–60% of planted
    flaws (arXiv:2610.31414).

Output:

- the record's noun and rung, against the claim's
- leading account (misreading, process failure, fabrication or real) and top alternative
- the raw-record or outcome-level test that splits them, and whether it was run
- decision impact
