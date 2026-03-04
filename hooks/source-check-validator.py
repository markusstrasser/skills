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
    r'|\[[A-F][1-6]\]'
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
    return len(CLAIM_RE.findall(text))


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


def check_inference_has_premises(file_content: str) -> str | None:
    """Warn if file has [INFERENCE] but no [SOURCE] or [DATA] tags."""
    if not INFERENCE_RE.search(file_content):
        return None

    has_source = SOURCE_RE.search(file_content) or re.search(r'\[[A-F][1-6]\]', file_content)
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
        file_content = f.read()

    # --- Determine what to check for density ---
    diff_content = extract_diff_content(hook_input)
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
            if ratio > 5:
                issues = [
                    f"Tag density in new content: {claim_count} claims / {tag_count} tags "
                    f"(ratio {ratio:.0f}:1, max 5:1)."
                ]
                _emit(mode, fpath, issues)
                sys.exit(2 if mode == "block" else 0)

    # --- Structural type checks (on diff content) ---
    struct_errors = check_structural_types(check_text)

    # --- TRAINING-DATA cap (on full file) ---
    training_warning = check_training_data_cap(file_content)

    # --- INFERENCE without premises (on full file) ---
    inference_warning = check_inference_has_premises(file_content)

    all_issues = struct_errors
    if training_warning:
        all_issues.append(training_warning)
    if inference_warning:
        all_issues.append(inference_warning)

    if all_issues:
        _emit(mode, fpath, all_issues)
        # Structural issues are advisory even in block mode — only density blocks
        sys.exit(0)

    sys.exit(0)


def _emit(mode: str, fpath: str, issues: list[str]):
    """Output warning or block message."""
    log_hook(mode, fpath)

    issue_text = " | ".join(issues)

    if mode == "block" and any("density" in i.lower() or "claim-bearing" in i.lower() for i in issues):
        print(f"BLOCKED: Provenance check failed for {fpath}", file=sys.stderr)
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
