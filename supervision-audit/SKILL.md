---
name: supervision-audit
description: "Audit recent sessions for wasted supervision — corrections, boilerplate, rubber stamps — that should be automated. Outputs concrete fixes (hooks, rules, defaults). Run after a work day or after updating goals/constitution/CLAUDE.md."
user-invocable: true
context: fork
argument-hint: "[--days N] [--project PROJECT]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
---

# Supervision Audit

Find where the human had to intervene but shouldn't have. Every correction, boilerplate instruction, and rubber stamp is a candidate for automation.

## When to Run

- End of a work day (default: today's sessions)
- After updating CLAUDE.md (including Constitution section), GOALS.md, or MEMORY.md
- After deploying new hooks or skills (to check if they're working)
- Periodically (weekly) for trend tracking

## Process

### Step 1: Structural Extraction

Run the deterministic classifier on recent transcripts:

```bash
python3 ~/Projects/skills/supervision-audit/scripts/extract_supervision.py $ARGUMENTS --json --output ~/Projects/meta/artifacts/supervision-audit/raw.json
```

Default: `--days 1` (today). Pass `--days 7` for weekly review, `--project intel` to filter.

Read the output and report the headline numbers to the user:
- Total sessions, total user messages
- Wasted supervision % (CORRECTION + BOILERPLATE + RUBBER_STAMP + RE_ORIENT)
- Top sub-patterns by count

### Step 2: Extract Transcripts for Context

For the top 3-5 sessions with the most wasted supervision, extract full transcripts:

```bash
python3 ~/Projects/skills/session-analyst/scripts/extract_transcript.py <project> --sessions 5 --output ~/Projects/meta/artifacts/supervision-audit/transcripts.md
```

### Step 3: LLM Synthesis (Gemini)

Dispatch the raw classification + transcripts to Gemini for deeper pattern analysis:

```bash
llmx -p google -m gemini-3.1-pro-preview -f ~/Projects/meta/artifacts/supervision-audit/raw.json -f ~/Projects/meta/artifacts/supervision-audit/transcripts.md "$(cat <<'PROMPT'
You are analyzing Claude Code sessions for WASTED HUMAN SUPERVISION — places where the user had to intervene but an automated system could have handled it instead.

You have two inputs:
1. A JSON classification of every user message into categories (NEW_AGENCY, CORRECTION, BOILERPLATE, RUBBER_STAMP, RE_ORIENT)
2. Full conversation transcripts for context

For each non-NEW_AGENCY pattern, determine:

1. **Is it genuinely automatable?** Some "corrections" are actually new information. Filter those out.
2. **What's the right fix type?**
   - HOOK: Deterministic shell/Python check (PreToolUse, PostToolUse, Stop)
   - RULE: CLAUDE.md instruction (only if checkable and not already covered)
   - DEFAULT: Change a default behavior (e.g., research depth, commit flow)
   - SKILL: New or modified skill to handle the pattern
   - ARCHITECTURAL: Structural change (new script, registry, checkpoint system)
3. **How many times did it recur?** Single occurrences are noise. 3+ is signal.
4. **What would the fix look like?** Be specific — hook pseudocode, rule text, or architectural sketch.

Output format for each finding:

### [PATTERN_NAME]: [one-line description]
- **Category:** CORRECTION | BOILERPLATE | RUBBER_STAMP | RE_ORIENT
- **Occurrences:** N (across M sessions)
- **Fix type:** HOOK | RULE | DEFAULT | SKILL | ARCHITECTURAL
- **Proposed fix:** [specific implementation — not vague suggestions]
- **Maintenance:** NONE (fire-and-forget) | LOW (occasional tuning) | MEDIUM (ongoing updates)
- **Composability:** Does this fix benefit other projects/skills?
- **Expected reduction:** what % of this pattern would this fix eliminate?

IMPORTANT:
- Do NOT propose fixes for things that are genuinely new agency from the user
- Do NOT propose rules for things that are already in CLAUDE.md (check the transcripts for system context)
- Rank findings by (occurrences × maintenance-adjusted automation potential). Dev time is ~free — rank by ongoing cost, not creation effort
- If nothing is worth fixing, say so — don't fabricate findings

Output ONLY the findings, ranked by priority. No preamble.
PROMPT
)"
```

### Step 4: Review and Act

1. **Read Gemini output critically** — it may hallucinate session details
2. **Cross-check** any specific claims against the raw JSON and transcripts
3. **For each HIGH/MEDIUM priority finding:**
   - If fix is a hook: implement it now (hooks are cheap, deterministic, reversible)
   - If fix is a rule: check it's not already covered, then add to CLAUDE.md
   - If fix is architectural: add to `meta/maintenance-checklist.md` with evidence link
4. **Append summary** to `~/Projects/meta/improvement-log.md`

### Step 5: Trend Report

If `--days 7` or more, compare against previous runs. Check:
- Is wasted supervision % trending down? (good — fixes are working)
- Are new patterns appearing? (expected — old ones get automated, new ones surface)
- Are any RE_ORIENT patterns declining? (checkpoint.md working?)

Report format appended to improvement-log.md:

```markdown
### [YYYY-MM-DD] Supervision Audit
- **Period:** [N days], [M sessions], [K user messages]
- **Wasted:** [X%] (target: <15%)
- **Top patterns:** [list]
- **Fixes deployed:** [list]
- **Status:** [ ] reviewed
```

## Important Constraints

- The extraction script is DETERMINISTIC — no LLM judgment in classification. This means false positives/negatives are consistent and can be tuned by editing the pattern lists.
- The Gemini pass is for SYNTHESIS only — finding non-obvious connections, proposing fixes, filtering noise. The raw data is the source of truth.
- Do not propose fixes that duplicate existing hooks or CLAUDE.md rules. Read the current rules first.
- Fixes must be TESTABLE. "Add a rule that says X" alone is not testable (instructions = 0% reliable). Prefer hooks and architectural changes.

$ARGUMENTS
