<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 3: Cross-Validation (Optional)

For high-stakes projects or when `--thorough` is passed, send a focused summary to GPT-5.4 for second opinion.

```bash
# Only if findings.json has >10 items or user requested thorough mode
FINDING_COUNT=$(python3 -c "import json; print(len(json.load(open('$UPGRADE_DIR/findings.json'))))")

if [ "$FINDING_COUNT" -gt 10 ] || [ "$THOROUGH" = "true" ]; then
  # Send findings + key files to GPT for validation
  {
    echo "# Gemini's Findings (verify these)"
    cat "$UPGRADE_DIR/findings.json"
    echo ""
    echo "# Key Source Files"
    # Include only files referenced in findings
    python3 -c "
import json
findings = json.load(open('$UPGRADE_DIR/findings.json'))
files = set()
for f in findings:
    files.update(f.get('files', []))
for f in sorted(files):
    print(f)
" | head -20 | while read filepath; do
      [ -f "$filepath" ] && echo -e "\n## $filepath\n\`\`\`\n$(cat "$filepath")\n\`\`\`"
    done
  } | llmx chat -m gpt-5.4 --reasoning-effort high --stream --timeout 600 "
Gemini analyzed a codebase and produced findings (JSON above). Your job:

1. For each finding: is it CORRECT? Does the code actually have this issue?
2. Which findings are FALSE POSITIVES? (Gemini hallucinated the problem)
3. What did Gemini MISS that you can see in the source files?
4. Rank the real findings by IMPACT (which fixes prevent the most future bugs).

Output a JSON array of objects:
{\"id\": \"F001\", \"verdict\": \"CONFIRMED|FALSE_POSITIVE|NEEDS_CHECK\", \"reason\": \"...\"}

Include new findings Gemini missed as {\"id\": \"NEW_001\", \"verdict\": \"NEW\", ...} using the same schema as Gemini's findings.
" > "$UPGRADE_DIR/gpt-validation.txt" 2>&1
fi
```
