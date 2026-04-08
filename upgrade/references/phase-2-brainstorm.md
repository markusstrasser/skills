<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Phase 2: Brainstorm (~15% of effort)

Invoke `/brainstorm` with the full inventory as context.

**Critical:** Include the existing_concepts.txt in the brainstorm prompt:

```
"The following features ALREADY EXIST — do not propose them:
[paste existing_concepts.txt or inventory summary]
Existing frontier IDs already used (do not reuse):
/tmp/novel_expansion_existing_ids.txt

What's genuinely MISSING that would add new biological/analytical insight?"
```

Use the brainstorm skill's perturbation axes:
- **Denial cascade:** forbid the dominant paradigms from initial generation
- **Domain forcing:** pick 3 distant domains (insurance, materials science, ATC)
- **Constraint inversion:** "what if we had family data?", "what if compute were free?"

**Output:** Disposition table with EXPLORE/PARK/REJECT for every extracted idea.
