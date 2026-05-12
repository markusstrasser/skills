#!/usr/bin/env python3
"""Structural provenance tag validator.

Called from postwrite-source-check.sh. Reads hook JSON from stdin.
Validates:
  1. Diff-level density — only checks new/changed content (Edit: new_string, Write: full file)
  2. Structural type checks — [SOURCE: url] must have URL, [DATA: x] must have qualifier
  3. TRAINING-DATA cap — max 30% of tags in the file can be [TRAINING-DATA]

Outputs JSON with additionalContext (advisory) or exits 2 (block mode).
"""
import json
import re
import sys
import os

# --- Tag patterns ---
TAG_RE = re.compile(
    r'\[(?:SOURCE|DATABASE|DATA|INFERENCE|SPEC|CALC|QUOTE|TRAINING-DATA|PREPRINT|FRONTIER|UNVERIFIED)'
    r'(?::?\s*[^\]]*)?\]'
    r'|\[[A-F][1-6](?::\s*[^\]]*)?\]'
)

SOURCE_RE = re.compile(r'\[SOURCE:\s*([^\]]*)\]')
DATABASE_RE = re.compile(r'\[DATABASE:\s*([^\]]*)\]')
DATA_QUAL_RE = re.compile(r'\[DATA:\s*([^\]]*)\]')
TRAINING_RE = re.compile(r'\[TRAINING-DATA\]')
INFERENCE_RE = re.compile(r'\[INFERENCE\]')

URL_LIKE = re.compile(r'https?://|doi:|PMID:|arXiv:|PMC\d')

CLAIM_RE = re.compile(
    r'[0-9]+%|[0-9]{4}-[0-9]{2}|\$[0-9]|PMID|et al\.'
    r'|[A-Z][a-z]+ [0-9]{4}|confirmed|refuted|showed|found that'
    r'|OR [0-9]|P[=<>]|HR\s*[=:]|RR\s*[=:]|CI\s*[=:]'
)

# Numeric quantitative claims that demand a checkable source, not training memory.
# Matches: "30%", "20.5%", "$10B", "$1.2 billion", "5,000 units", "third largest",
# market-share / revenue / count language.
NUMERIC_CLAIM_RE = re.compile(
    r'\b\d+\.?\d*\s*%'                      # percentages: 30%, 20.5%
    r'|\$\s*\d+\.?\d*\s*[MBKmbk]?\b'        # dollar amounts: $10B, $1.2M
    r'|\b\d+\.?\d*\s*(?:million|billion|trillion|thousand)\b'  # spelled magnitudes
    r'|\b(?:first|second|third|fourth|fifth|top)\s*[- ]?(?:largest|biggest|leading)\b',
    re.IGNORECASE,
)

# HTML comments are invisible in rendered markdown. Strip before checking
# so [TAGS] inside <!-- ... --> don't satisfy provenance requirements.
HTML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)


def strip_invisible(text: str) -> str:
    """Remove HTML comments — they don't render and shouldn't count as provenance."""
    return HTML_COMMENT_RE.sub('', text)


def extract_diff_content(hook_input: dict) -> str | None:
    """Extract the new/changed content from the hook input.

    For Edit: returns new_string (the changed content).
    For Write: returns None (check the whole file).
    """
    tool_input = hook_input.get("tool_input", {})
    tool_name = hook_input.get("tool_name", "")

    if tool_name == "Edit" or "old_string" in tool_input:
        return tool_input.get("new_string", "")
    # Write — check whole file
    return None


def count_tags(text: str) -> int:
    return len(TAG_RE.findall(text))


def count_claims(text: str) -> int:
    # Strip TAG_RE matches first so dates inside tag brackets like
    # `[A1: filed 2026-04-16]` or `[DATA: form4 2026-04-26]` don't double-count
    # as claims. The tag itself satisfies the citation requirement; the date
    # inside it is provenance, not a separate claim.
    return len(CLAIM_RE.findall(TAG_RE.sub("", text)))


def check_structural_types(text: str) -> list[str]:
    """Check that tags have valid structural content. Returns list of errors."""
    errors = []

    for m in SOURCE_RE.finditer(text):
        content = m.group(1).strip()
        if not content:
            errors.append("[SOURCE: ] is empty — must include a URL, DOI, or PMID")
        elif not URL_LIKE.search(content):
            errors.append(f"[SOURCE: {content}] has no URL/DOI/PMID — not a checkable reference")

    for m in DATABASE_RE.finditer(text):
        if not m.group(1).strip():
            errors.append("[DATABASE: ] is empty — must name the database/dataset")

    for m in DATA_QUAL_RE.finditer(text):
        if not m.group(1).strip():
            errors.append("[DATA: ] is empty — must specify the data source or observation")

    return errors


def check_training_data_cap(file_content: str) -> str | None:
    """Check that TRAINING-DATA tags don't exceed 30% of all tags."""
    total_tags = count_tags(file_content)
    if total_tags == 0:
        return None

    training_count = len(TRAINING_RE.findall(file_content))
    if training_count == 0:
        return None

    ratio = training_count / total_tags
    if ratio > 0.30:
        pct = int(ratio * 100)
        return (
            f"[TRAINING-DATA] is {pct}% of tags ({training_count}/{total_tags}). "
            f"Cap is 30%. Replace some with [SOURCE: url] or [DATA] backed by verification."
        )
    return None


def check_training_data_on_numeric_claims(text: str) -> list[str]:
    """Flag numeric/quantitative claims tagged with [TRAINING-DATA] only.

    Specific numbers (market shares, revenues, ranks) sourced from training
    memory are high-risk fabrication targets. They need a checkable citation
    ([SOURCE:], [DATA], [CALC], or Admiralty grade), not just [TRAINING-DATA].

    Same-line scope: a [TRAINING-DATA] tag covers numeric claims on its line
    unless an explicit checkable tag also appears on that line.
    """
    errors: list[str] = []
    checkable = re.compile(
        r'\[SOURCE:|\[DATABASE:|\[DATA[\]:]|\[CALC[\]:]|\[QUOTE[\]:]|\[[A-F][1-6](?::[^\]]+)?\]'
    )
    for line in text.splitlines():
        if '[TRAINING-DATA]' not in line:
            continue
        if not NUMERIC_CLAIM_RE.search(line):
            continue
        if checkable.search(line):
            continue
        excerpt = line.strip()[:120]
        errors.append(
            f"[TRAINING-DATA] on numeric claim without checkable source: \"{excerpt}\""
        )
    return errors


def check_inference_has_premises(file_content: str) -> str | None:
    """Warn if file has [INFERENCE] but no [SOURCE] or [DATA] tags."""
    if not INFERENCE_RE.search(file_content):
        return None

    has_source = SOURCE_RE.search(file_content) or re.search(r'\[[A-F][1-6](?::[^\]]+)?\]', file_content)
    has_data = re.search(r'\[DATA', file_content) or re.search(r'\[DATABASE:', file_content)

    if not has_source and not has_data:
        return "[INFERENCE] used but no [SOURCE] or [DATA] tags in file — inference from what?"

    return None


def main():
    mode = os.environ.get("PROVENANCE_MODE", "warn")

    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    fpath = (
        hook_input.get("file_path", "")
        or hook_input.get("tool_input", {}).get("file_path", "")
    )
    if not fpath or not os.path.isfile(fpath):
        sys.exit(0)

    with open(fpath) as f:
        raw_file_content = f.read()

    # Strip HTML comments before any checking — invisible-to-reader provenance
    # tags are guard evasion, not real citation.
    file_content = strip_invisible(raw_file_content)

    # --- Determine what to check for density ---
    raw_diff = extract_diff_content(hook_input)
    diff_content = strip_invisible(raw_diff) if raw_diff is not None else None
    check_text = diff_content if diff_content is not None else file_content

    # If the diff is tiny (< 3 lines, likely a small edit), skip density check
    if diff_content is not None and check_text.count('\n') < 3:
        # Still run structural checks on the diff
        pass
    else:
        # --- Density check on diff/new content only ---
        tag_count = count_tags(check_text)
        claim_count = count_claims(check_text)

        if claim_count > 0 and tag_count == 0:
            # New content has claims but zero tags
            issues = [f"New content has {claim_count} claim-bearing lines but 0 provenance tags."]
            _emit(mode, fpath, issues)
            sys.exit(2 if mode == "block" else 0)

        if claim_count > 0 and tag_count > 0:
            ratio = claim_count / tag_count
            # README/index files are link inventories — relax density to 10:1
            is_index = os.environ.get("IS_INDEX", "false").lower() == "true"
            max_ratio = 10 if is_index else 5
            if ratio > max_ratio:
                issues = [
                    f"Tag density in new content: {claim_count} claims / {tag_count} tags "
                    f"(ratio {ratio:.0f}:1, max {max_ratio}:1)."
                ]
                _emit(mode, fpath, issues)
                sys.exit(2 if mode == "block" else 0)

    # --- Structural type checks (on diff content) ---
    struct_errors = check_structural_types(check_text)

    # --- TRAINING-DATA on numeric claims (on diff content) ---
    numeric_errors = check_training_data_on_numeric_claims(check_text)

    # --- TRAINING-DATA cap (on full file) ---
    training_warning = check_training_data_cap(file_content)

    # --- INFERENCE without premises (on full file) ---
    inference_warning = check_inference_has_premises(file_content)

    all_issues = struct_errors + numeric_errors
    if training_warning:
        all_issues.append(training_warning)
    if inference_warning:
        all_issues.append(inference_warning)

    if all_issues:
        _emit(mode, fpath, all_issues)
        # Numeric-claim [TRAINING-DATA] blocks in block mode (fabrication risk).
        # Other structural issues remain advisory.
        if mode == "block" and numeric_errors:
            sys.exit(2)
        sys.exit(0)

    sys.exit(0)


def _emit(mode: str, fpath: str, issues: list[str]):
    """Output warning or block message."""
    log_hook(mode, fpath)

    issue_text = " | ".join(issues)

    if mode == "block" and any(
        "density" in i.lower()
        or "claim-bearing" in i.lower()
        or "training-data] on numeric" in i.lower()
        for i in issues
    ):
        # NOTE: this runs in PostToolUse — the file is ALREADY written. Exit 2
        # blocks the *next* tool call from the Claude harness but does NOT
        # revert the write. The "POST-WRITE WARNING" framing makes that
        # semantics explicit so agents don't waste cycles re-running an edit
        # that already landed. To prevent the write, move this hook to
        # PreToolUse and gate on proposed_content instead.
        print(f"POST-WRITE WARNING: Provenance check failed for {fpath} (file already written; fix and re-edit)", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        print(
            "Tags: [SOURCE: url], [DATA], [DATABASE: name], [INFERENCE], "
            "[TRAINING-DATA], [SPEC], [CALC], or [A1]-[F6]",
            file=sys.stderr,
        )
    else:
        msg = f"PROVENANCE: {os.path.basename(fpath)}: {issue_text}"
        print(json.dumps({"additionalContext": msg}))


def log_hook(mode: str, fpath: str):
    """Best-effort trigger logging."""
    import subprocess
    try:
        subprocess.run(
            [os.path.expanduser("~/Projects/skills/hooks/hook-trigger-log.sh"),
             "source-check", mode, fpath],
            timeout=2, capture_output=True
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
