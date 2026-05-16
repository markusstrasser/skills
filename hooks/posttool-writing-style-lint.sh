#!/usr/bin/env bash
# posttool-writing-style-lint.sh — Advisory: warn on writing-style violations in drafts.
# Deploy as PostToolUse hook on Write|Edit.
#
# Two tiers based on path:
#   OUTREACH (short-form correspondence): em-dashes, throat-clearers, formal sign-offs, banned vocab
#   LONGFORM (essays, blog posts, content): banned vocab only
#
# Env (regex, alternation with |):
#   WRITING_LINT_OUTREACH_PATHS — default: outbox/|drafts/|correspondence/|messages/|email/|outreach/|docs/outreach/
#   WRITING_LINT_LONGFORM_PATHS — default: src/routes/.+\.svx$|src/lib/content/|content/|essays/|archive/.+\.svx$
#
# Exits 0 always. Warnings to stderr.
# Skips files containing the marker `<!-- writing-lint:skip -->`.

set -u

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null)
[[ -z "$FILE_PATH" ]] && exit 0
[[ ! -f "$FILE_PATH" ]] && exit 0

# Allow prose-bearing extensions. Data-prose tier (.ts/.tsx/.js/.jsx) covers
# TS/JS data modules that embed reader-facing strings (e.g. reception.ts).
case "$FILE_PATH" in
  *.md|*.svx|*.txt|*.eml|*.ts|*.tsx|*.js|*.jsx) ;;
  *) exit 0 ;;
esac

OUTREACH_PATHS="${WRITING_LINT_OUTREACH_PATHS:-outbox/|drafts/|correspondence/|messages/|email/|outreach/|docs/outreach/}"
LONGFORM_PATHS="${WRITING_LINT_LONGFORM_PATHS:-src/routes/.+\.svx$|src/lib/content/|content/|essays/|archive/.+\.svx$}"
DATA_PROSE_PATHS="${WRITING_LINT_DATA_PROSE_PATHS:-src/lib/data/.+\.(ts|tsx|js|jsx)$}"

TIER=""
if echo "$FILE_PATH" | grep -qE "$OUTREACH_PATHS"; then
  TIER="outreach"
elif echo "$FILE_PATH" | grep -qE "$LONGFORM_PATHS"; then
  TIER="longform"
elif echo "$FILE_PATH" | grep -qE "$DATA_PROSE_PATHS"; then
  TIER="data-prose"
else
  exit 0
fi

# Opt-out marker
if grep -q '<!-- writing-lint:skip -->' "$FILE_PATH" 2>/dev/null; then
  exit 0
fi

WARNINGS=()

# Universal: banned corporate vocab (case-insensitive, word-boundary where sensible)
# Use python for proper word-boundary matching across multiline files
HITS=$(python3 - "$FILE_PATH" <<'PY' 2>/dev/null
import re, sys
path = sys.argv[1]
try:
    text = open(path, encoding='utf-8', errors='replace').read()
except Exception:
    sys.exit(0)

banned = [
    (r'\bdelve\b',                       "delve"),
    (r'\bleverage\b',                    "leverage (verb)"),
    (r'\bunpack\b',                      "unpack (corporate sense)"),
    (r'\bshed light\b',                  "shed light"),
    (r'\bdive deep\b',                   "dive deep"),
    (r'\bcircle back\b',                 "circle back"),
    (r'\btouch base\b',                  "touch base"),
    (r'\bsynergy\b',                     "synergy"),
    (r'\bstakeholder',                   "stakeholder(s)"),
    (r'\bmoving forward\b',              "moving forward"),
    (r'\bat the end of the day\b',       "at the end of the day"),
    (r'\bneedless to say\b',             "needless to say"),
    (r'\bit goes without saying\b',      "it goes without saying"),
    (r'\bas discussed\b',                "as discussed"),
    (r'\bper our conversation\b',        "per our conversation"),
    (r'\btake this offline\b',           "take this offline"),
    (r'\bI just wanted to follow up\b',  "I just wanted to follow up"),
    (r'\babsolutely!',                   "absolutely!"),
    (r'\bperfect!',                      "Perfect!"),
]

flags = re.IGNORECASE | re.MULTILINE
hits = []
for pat, label in banned:
    matches = list(re.finditer(pat, text, flags))
    if matches:
        # report first occurrence with line number
        m = matches[0]
        line_no = text[:m.start()].count('\n') + 1
        hits.append(f"L{line_no}: {label} ({len(matches)}×)")
print("\n".join(hits))
PY
)

if [[ -n "$HITS" ]]; then
    while IFS= read -r line; do
        [[ -n "$line" ]] && WARNINGS+=("banned vocab: $line")
    done <<< "$HITS"
fi

# Universal: structural slop patterns (X turns Y into Z, X makes Y look Z,
# closing defensive negation, importance inflation). All tiers.
STRUCT_HITS=$(python3 - "$FILE_PATH" <<'PY' 2>/dev/null
import re, sys
path = sys.argv[1]
try:
    text = open(path, encoding='utf-8', errors='replace').read()
except Exception:
    sys.exit(0)

# For .ts/.tsx/.js/.jsx files, only scan inside string literals containing reader
# prose. Heuristic: lines with `note:` or `body:` fields (covers reception.ts
# shape). For other files, scan whole text.
def extract_prose(text, path):
    if not path.endswith(('.ts', '.tsx', '.js', '.jsx')):
        return text
    out = []
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if s.startswith(('note:', 'body:', 'title:', 'imageAlt:', 'note :', 'body :')):
            out.append(line)
        else:
            out.append('\n')  # placeholder to preserve line numbers
    return ''.join(out)

scan_text = extract_prose(text, path)

checks = [
    # Editorial verbs: X (turns|moves|folds|gives|compresses) Y into Z
    (r'\b(turns?|moves?|folds?|gives?|compresses?)\s+(?:the\s+|a\s+|his\s+|her\s+|its\s+)?\w+(?:\s+\w+){0,3}\s+into\b',
     "editorial verb 'X into Y' (turns/moves/folds/gives/compresses ... into)"),
    # Makes X look/seem/feel Y
    (r'\bmakes?\s+(?:the\s+|a\s+|his\s+|her\s+|its\s+)?\w+(?:\s+\w+){0,2}\s+(?:look|seem|feel)\s+\w+',
     "editorial verb 'makes X look Y'"),
    # Closing defensive negation: ", not <word>" near end of sentence
    (r',\s+not\s+[a-z]+\.["\']?\s*$',
     "closing defensive negation 'X, not Y'"),
    (r',\s+not\s+[a-z]+\.["\']?,?\s*\n',
     "closing defensive negation 'X, not Y'"),
    # Importance inflation
    (r'\b(pivotal|crucial|vital|enduring|profound|stunning|breathtaking|groundbreaking|revolutionary|masterful|powerful|striking)\b',
     "importance inflation"),
    # Symbolic significance
    (r'\b(testament to|hallmark of|continues to (?:captivate|inspire))\b',
     "promotional warmth"),

    # Reader-reception patterns from 2026-05-16 dossier (matthew/macbeth).
    # See research/2026-05-14-primary-text-reception-reader-design-rules.md
    # §Art-note specific patterns to avoid for the full taxonomy.

    # Curation-meta — the note explains why the asset is in the slot, not the work.
    (r"\b(earns its place|belongs in the middle|missing exact \w+ image|better than another paragraph|a reception object,? not)\b",
     "curation-meta (note self-justifies, doesn't say something about the work)"),

    # Comparative framings — compare to a thing the reader wasn't thinking about.
    (r"\b(rather than|smaller and stranger than|more\s+\w+\s+than\s+\w+|less\s+\w+\s+than\s+\w+|not\s+illustrating\s+\w+\s+literally)\b",
     "comparative framing (vs. a thing the reader wasn't thinking about)"),

    # Rule-of-three abstract list + thesis verb: "A, B, and C (turn|make|render|fold|give) X (the|a) Y".
    # Tight version — requires the closing verb-and-object so we don't catch every triple-comma list.
    (r"\b\w+,\s+\w+,?\s+and\s+\w+\s+(turn|make|render|transform|fold|give)\s+(?:the|a|an|its|her|his)\s+\w+",
     "rule-of-three abstract list + thesis verb"),

    # Source-attribution openers — source label is its own field; don't double-attribute in prose.
    # Tight: only catches when an institution name STARTS the prose and is followed by an attribution verb.
    (r"^\s*[\"']?(RSC|Folger|Working Preacher|Bible Project|Yale CBA|Yale Center for British Art|Met|Tate|British Museum|Wellcome|Arden|Cambridge|Oxford)\s+(notes?|reads?|places?|argues?|writes?|says?|describes?|points out|observes?)\b",
     "source-attribution opener (the sourceLabel field already names it)"),

    # Reader-instruction-in-display-position — used as a heading/title field.
    (r"^\s*[\"']?(This\s+(scene|chapter|passage|painting|verse|line)\s+(should|must|needs to)|Handle\s+\w+\s+carefully|Read this through|Do not flatten)\b",
     "reader-instruction title (state the substance, don't direct the reader)"),

    # Aphoristic compression — concrete sentence then aphorism "X is Y before it is Z" or similar.
    # The 2026-05-16 incident: "The prophecy is geography before it is anyone's plan."
    (r"\b\w+\s+is\s+\w+\s+before\s+it\s+is\s+\w+",
     "aphoristic compression ('X is Y before it is Z')"),

    # Taxonomy labels surfacing as reader-facing field values.
    # Caveat: 'Theme' etc. are also legitimate noun usages — restrict to the canonical fit-label form.
    (r"^\s*[\"']?(Theme|Tension|Spicy|Structure|Frame|Lens|Composite tradition|Exact passage|Exact book|Wrong book|Direct quote|Fulfillment quote)\s*[\"',]?\s*$",
     "taxonomy label leaked into reader-facing field"),

    # Editorial location strings — 18-19c stage-location additions (Rowe/Capell), not in the Folio.
    # Tight: only the canonical compound form ("Inverness. A Castle"/"Forres. A heath").
    (r"(Inverness|Forres|Fife|Dunsinane|Glamis|Cawdor)\.\s+(?:A\s+|An\s+|The\s+)?\w+(?:'s)?\s+(?:Castle|Heath|Hall|Chamber|Palace|Room)",
     "editorial location string (Rowe/Capell 18-19c invention, not Folio)"),
]

flags = re.IGNORECASE | re.MULTILINE
hits = []
seen = set()
for pat, label in checks:
    for m in re.finditer(pat, scan_text, flags):
        line_no = scan_text[:m.start()].count('\n') + 1
        key = (line_no, label)
        if key in seen:
            continue
        seen.add(key)
        # First two occurrences per (line, label); aggregate counts elsewhere
        hits.append(f"L{line_no}: {label} — '{m.group(0)[:50]}'")
        if len(hits) >= 12:  # cap noise
            break
    if len(hits) >= 12:
        break
print("\n".join(hits))
PY
)

if [[ -n "$STRUCT_HITS" ]]; then
    while IFS= read -r line; do
        [[ -n "$line" ]] && WARNINGS+=("structural slop: $line")
    done <<< "$STRUCT_HITS"
fi

# Data-prose tier only: source-attribution provenance.
# Catches the 2026-05-16 RSC-stamp failure mode: sourceLabel claims institutional
# attribution but sourceUrl host doesn't match. Walks pairs in object-literal order.
if [[ "$TIER" == "data-prose" ]]; then
  PROVENANCE_HITS=$(python3 - "$FILE_PATH" <<'PY' 2>/dev/null
import re, sys
from urllib.parse import urlparse

path = sys.argv[1]
try:
    text = open(path, encoding='utf-8', errors='replace').read()
except Exception:
    sys.exit(0)

# Institution → expected URL host substrings. Add liberally; matches are case-insensitive substring.
INSTITUTIONS = {
    'RSC':                ['rsc.org.uk', 'youtube.com/c/theroyalshakespeare', 'youtube.com/@royalshakespeare'],
    'Folger':             ['folger.edu', 'folgerpedia'],
    'Working Preacher':   ['workingpreacher.org'],
    'Bible Project':      ['bibleproject.com'],
    'Yale CBA':           ['britishart.yale.edu'],
    'Yale Center':        ['britishart.yale.edu'],
    'British Museum':     ['britishmuseum.org'],
    'Met':                ['metmuseum.org'],
    'The Met':            ['metmuseum.org'],
    'Tate':               ['tate.org.uk'],
    'Wellcome':           ['wellcomecollection.org', 'wellcomeimages'],
    'National Gallery':   ['nga.gov', 'nationalgallery.org.uk', 'nationalgallery.'],
    'Louvre':             ['louvre.fr', 'collections.louvre'],
    'Cleveland Museum':   ['clevelandart.org'],
    'Art Institute':      ['artic.edu'],
    'Library of Congress':['loc.gov'],
    'Arden':              ['bloomsbury.com', 'arden'],
    'Cambridge':          ['cambridge.org'],
    'Oxford':             ['oxford', 'oup.com'],
    'McKellen':           ['mckellen.com'],
    'NYPL':               ['nypl.org', 'digitalcollections.nypl'],
    'Bible Odyssey':      ['bibleodyssey.org'],
    'Princeton':          ['princeton.edu'],
    'Visual Commentary':  ['thevcs.org'],
}
# Hosts that are valid generic image carriers (work attribution still owned by listed institution).
# These are allowed for *any* institutional label.
GENERIC_IMAGE_HOSTS = ['commons.wikimedia.org', 'upload.wikimedia.org']

# Find all (sourceLabel, sourceUrl) pairs by walking the file in order.
# Heuristic: within a 30-line window, label and url appear adjacent.
label_re = re.compile(r"sourceLabel\s*:\s*['\"]([^'\"]+)['\"]")
url_re   = re.compile(r"sourceUrl\s*:\s*['\"]([^'\"]+)['\"]")

labels = [(m.start(), m.group(1)) for m in label_re.finditer(text)]
urls   = [(m.start(), m.group(1)) for m in url_re.finditer(text)]

hits = []
seen = set()
for pos, label in labels:
    # Find nearest sourceUrl after this label (within ~30 lines = ~1500 chars).
    url = None
    for upos, uval in urls:
        if upos > pos and (upos - pos) < 1500:
            url = uval
            break
    if url is None:
        continue
    host = urlparse(url).netloc.lower()
    # Composite labels like "Wellcome / Wikimedia Commons" or "Tate work record / Wikimedia"
    # are OK if (a) one of the named institutions matches OR (b) host is a generic image carrier
    # and the label names at least one institution. Split on '/' and '&' for split-credit cases.
    if any(g in host for g in GENERIC_IMAGE_HOSTS):
        continue  # generic image host is acceptable for any institutional label
    label_parts = re.split(r'\s*[/&]\s*', label)
    # Check if ANY listed institution in any part of the label matches the host.
    matched = False
    primary_inst = None
    for inst, hosts in INSTITUTIONS.items():
        for part in label_parts:
            if inst.lower() in part.lower():
                if primary_inst is None:
                    primary_inst = (inst, hosts)
                if any(h in host for h in hosts):
                    matched = True
                    break
        if matched:
            break
    if primary_inst is not None and not matched:
        inst, hosts = primary_inst
        line_no = text[:pos].count('\n') + 1
        key = (line_no, inst)
        if key in seen:
            continue
        seen.add(key)
        hits.append(f"L{line_no}: sourceLabel '{label[:50]}' → sourceUrl host '{host}' (expected one of {hosts[:2]})")
        if len(hits) >= 10:
            break

print("\n".join(hits))
PY
)
  if [[ -n "$PROVENANCE_HITS" ]]; then
      while IFS= read -r line; do
          [[ -n "$line" ]] && WARNINGS+=("source provenance: $line")
      done <<< "$PROVENANCE_HITS"
  fi
fi

# Outreach-only checks
if [[ "$TIER" == "outreach" ]]; then
  OUTREACH_HITS=$(python3 - "$FILE_PATH" <<'PY' 2>/dev/null
import re, sys
path = sys.argv[1]
try:
    text = open(path, encoding='utf-8', errors='replace').read()
except Exception:
    sys.exit(0)

checks = [
    (r'—',                                                            "em-dash (use period or comma)"),
    (r'\bI hope this (?:email |message )?finds you well\b',           "throat-clearing opener: 'I hope this finds you well'"),
    (r'\bI wanted to reach out\b',                                    "throat-clearing opener: 'I wanted to reach out'"),
    (r"\bI'?m writing to\b",                                          "throat-clearing opener: 'I'm writing to'"),
    (r'\bJust checking in\b',                                         "throat-clearing opener: 'Just checking in'"),
    (r'^Best regards,?\s*$',                                          "formal sign-off: 'Best regards' (use 'Markus' or 'best, Markus')"),
    (r'^Kind regards,?\s*$',                                          "formal sign-off: 'Kind regards'"),
    (r'^Warm regards,?\s*$',                                          "formal sign-off: 'Warm regards'"),
    (r'^Sincerely,?\s*$',                                             "formal sign-off: 'Sincerely'"),
    (r'^Thanks!?\s*$',                                                "formal sign-off: 'Thanks!' alone"),
    (r"\bI'?m SO excited\b",                                          "performative enthusiasm: 'I'm SO excited'"),
    (r'\babsolutely love\b',                                          "performative enthusiasm: 'absolutely love'"),
    (r'\bLet me start by\b',                                          "signposting: 'Let me start by'"),
    (r'\bFirst,.*\n.*\bThen,.*\n.*\bFinally,',                        "signposting: First/Then/Finally cadence"),
]

flags = re.IGNORECASE | re.MULTILINE
hits = []
for pat, label in checks:
    matches = list(re.finditer(pat, text, flags))
    if matches:
        m = matches[0]
        line_no = text[:m.start()].count('\n') + 1
        hits.append(f"L{line_no}: {label}")

# List-in-email heuristic: 3+ consecutive lines starting with `- ` or `1. ` etc.
list_pat = re.compile(r'(?:^[-*]\s|^\d+[.)]\s).+(?:\n(?:[-*]\s|\d+[.)]\s).+){2,}', re.MULTILINE)
m = list_pat.search(text)
if m:
    line_no = text[:m.start()].count('\n') + 1
    hits.append(f"L{line_no}: bullet/numbered list (weave into prose for outreach)")

print("\n".join(hits))
PY
)

  if [[ -n "$OUTREACH_HITS" ]]; then
      while IFS= read -r line; do
          [[ -n "$line" ]] && WARNINGS+=("outreach: $line")
      done <<< "$OUTREACH_HITS"
  fi
fi

if [[ ${#WARNINGS[@]} -gt 0 ]]; then
  # Trigger log if available
  ~/Projects/skills/hooks/hook-trigger-log.sh "writing-style-lint" "advise" "$FILE_PATH" 2>/dev/null || true

  echo "" >&2
  echo "Writing-style lint ($TIER) on $(basename "$FILE_PATH"):" >&2
  for w in "${WARNINGS[@]}"; do
    echo "  ! $w" >&2
  done
  echo "  (skill: writing-style. silence with <!-- writing-lint:skip --> in file.)" >&2
fi

exit 0
