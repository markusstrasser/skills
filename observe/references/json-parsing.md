<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Structured Findings Handling

The shared review/dispatch path should already emit structured artifacts. Prefer:

- `findings.json` for extracted findings
- `coverage.json` for packet and dispatch provenance
- `disposition.md` for operator-readable synthesis

Do not maintain a second JSON-scraping pipeline for raw model transcripts inside
`upgrade`.

If you are recovering a legacy run that only has raw text:

1. extract findings through the shared review helpers
2. write `findings.json`
3. rebuild `coverage.json`
4. continue triage from those artifacts
