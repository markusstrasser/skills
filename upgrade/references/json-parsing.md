<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# JSON Parsing from Model Output

Extract JSON from both model responses (they sometimes wrap in markdown):

```bash
for MODEL in gemini gpt; do
python3 << PYEOF
import json, re, sys

text = open('$UPGRADE_DIR/${MODEL}-raw.txt').read()

# Strip markdown code fences if present
text = re.sub(r'```json\s*', '', text)
text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)

# Find the first complete JSON array (non-greedy would fail on nested arrays)
# Instead, find first [ and use bracket counting
start = text.find('[')
if start == -1:
    print(f'ERROR: No JSON array found in ${MODEL} output', file=sys.stderr)
    sys.exit(1)

depth = 0
end = start
for i, ch in enumerate(text[start:], start):
    if ch == '[': depth += 1
    elif ch == ']': depth -= 1
    if depth == 0:
        end = i + 1
        break

json_str = text[start:end]

# Sanitize trailing commas (LLMs produce these frequently)
json_str = re.sub(r',\s*([\]}])', r'\1', json_str)

try:
    data = json.loads(json_str)
    with open('$UPGRADE_DIR/${MODEL}-findings.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f'${MODEL}: Parsed {len(data)} findings')
except json.JSONDecodeError as e:
    print(f'ERROR: Invalid JSON from ${MODEL}: {e}', file=sys.stderr)
    with open('$UPGRADE_DIR/${MODEL}-raw-extract.txt', 'w') as f:
        f.write(json_str)
    sys.exit(1)
PYEOF
done
```
