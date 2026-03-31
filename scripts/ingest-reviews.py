#!/usr/bin/env python3
"""Ingest clipboard captures into .reviews/roundN-responses/.

Matches ~/Downloads/clipboard-*.{md,txt} to outbox prompts by two signals:
1. Prompt ID (R39, T5, etc.) mentioned in the clipboard file
2. Distinctive code filenames from the prompt appearing in the response

Usage:
    ingest-reviews.py PROJECT ROUND [--dry-run] [--clipboard-dir DIR] [--min-size BYTES]
    ingest-reviews.py ~/Projects/genomics 5
    ingest-reviews.py ~/Projects/genomics 5 --dry-run
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path


def extract_prompt_id(filename: str) -> str:
    """Extract prompt ID (R39, T5, C1, etc.) from prompt filename."""
    m = re.match(r"([RTC]\d+[ab]?)", filename)
    return m.group(1) if m else ""


def extract_code_files(prompt_path: Path) -> set[str]:
    """Extract referenced script/config filenames from a prompt."""
    text = prompt_path.read_text(errors="replace")
    # Match scripts/foo.py, config/bar.json, etc.
    return set(re.findall(r"(?:scripts|config)/[a-z_]+\.\w+", text))


def score_match(clipboard_path: Path, prompt_id: str, code_files: set[str]) -> int:
    """Score how well a clipboard file matches a prompt. Higher = better match."""
    text = clipboard_path.read_text(errors="replace")
    score = 0

    # Signal 1: prompt ID mentioned in response
    if re.search(rf"\b{re.escape(prompt_id)}\b", text):
        score += 10

    # Signal 2: code filenames from prompt mentioned in response
    for cf in code_files:
        if cf in text:
            score += 3
        # Also check just the basename
        basename = cf.split("/")[-1]
        if basename in text:
            score += 1

    return score


def find_clipboard_files(
    clipboard_dir: Path, after_mtime: float, min_size: int
) -> list[Path]:
    """Find clipboard captures newer than a threshold, sorted by mtime."""
    files = []
    for pattern in ("clipboard-*.md", "clipboard-*.txt"):
        files.extend(clipboard_dir.glob(pattern))

    # Filter by mtime and minimum size
    files = [
        f
        for f in files
        if f.stat().st_mtime >= after_mtime and f.stat().st_size >= min_size
    ]

    return sorted(files, key=lambda f: f.stat().st_mtime)


def main():
    parser = argparse.ArgumentParser(description="Match clipboard captures to review prompts")
    parser.add_argument("project", help="Project path (e.g., ~/Projects/genomics)")
    parser.add_argument("round", type=int, help="Review round number")
    parser.add_argument("--dry-run", action="store_true", help="Show matches without copying")
    parser.add_argument(
        "--clipboard-dir",
        default=os.path.expanduser("~/Downloads"),
        help="Directory with clipboard captures",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=500,
        help="Minimum clipboard file size in bytes (filters noise)",
    )
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    prompts_dir = project / ".reviews" / f"round{args.round}-prompts"
    responses_dir = project / ".reviews" / f"round{args.round}-responses"
    clipboard_dir = Path(args.clipboard_dir)

    if not prompts_dir.is_dir():
        print(f"No prompts directory: {prompts_dir}", file=sys.stderr)
        sys.exit(1)

    # Read prompts
    prompt_files = sorted(prompts_dir.glob("*.md"))
    prompt_files = [f for f in prompt_files if f.name not in ("INDEX.md", "POST-IMPLEMENTATION-INDEX.md")]

    if not prompt_files:
        print("No prompt files found.", file=sys.stderr)
        sys.exit(1)

    # Build prompt metadata
    prompts = {}
    for pf in prompt_files:
        pid = extract_prompt_id(pf.name)
        if not pid:
            continue
        prompts[pid] = {
            "path": pf,
            "code_files": extract_code_files(pf),
            "mtime": pf.stat().st_mtime,
        }

    # Check existing responses
    existing_responses = set()
    if responses_dir.is_dir():
        for rf in responses_dir.iterdir():
            rid = extract_prompt_id(rf.name)
            if rid:
                existing_responses.add(rid)

    unmatched_prompts = {pid: p for pid, p in prompts.items() if pid not in existing_responses}
    if not unmatched_prompts:
        print(f"All {len(prompts)} prompts already have responses.")
        return

    print(f"Round {args.round}: {len(prompts)} prompts, {len(existing_responses)} existing responses, {len(unmatched_prompts)} unmatched")

    # Find clipboard candidates
    oldest_prompt_mtime = min(p["mtime"] for p in prompts.values())
    # Look back 1 hour before oldest prompt to catch early responses
    candidates = find_clipboard_files(
        clipboard_dir, oldest_prompt_mtime - 3600, args.min_size
    )

    if not candidates:
        print(f"No clipboard files found in {clipboard_dir} newer than prompts.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(candidates)} clipboard candidates")

    # Score each candidate against each unmatched prompt
    matches: dict[str, tuple[Path, int]] = {}  # pid -> (clipboard_path, score)
    used_clipboards: set[Path] = set()

    # First pass: high-confidence matches (score >= 10 = ID match)
    for pid, pdata in unmatched_prompts.items():
        best_score = 0
        best_file = None
        for cf in candidates:
            if cf in used_clipboards:
                continue
            s = score_match(cf, pid, pdata["code_files"])
            if s > best_score:
                best_score = s
                best_file = cf
        if best_file and best_score >= 4:
            matches[pid] = (best_file, best_score)
            used_clipboards.add(best_file)

    # Report
    if not matches:
        print("\nNo matches found. Unmatched prompts:")
        for pid in sorted(unmatched_prompts):
            print(f"  {pid}")
        print(f"\nTry manually naming responses in {responses_dir}/")
        sys.exit(1)

    responses_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'Match':<8} {'Score':>5}  {'Clipboard file':<45} → Response")
    print("-" * 90)
    for pid in sorted(matches):
        cf, score = matches[pid]
        response_name = f"{pid}-response.md"
        confidence = "HIGH" if score >= 10 else "med" if score >= 6 else "low"
        print(f"  {pid:<6} {score:>3} ({confidence})  {cf.name:<45} → {response_name}")

    unmatched_remaining = set(unmatched_prompts) - set(matches)
    if unmatched_remaining:
        print(f"\nStill unmatched: {', '.join(sorted(unmatched_remaining))}")

    if args.dry_run:
        print("\n--dry-run: no files copied.")
        return

    # Copy matched files
    copied = 0
    for pid in sorted(matches):
        cf, score = matches[pid]
        dest = responses_dir / f"{pid}-response.md"
        if dest.exists():
            print(f"  SKIP {pid}: {dest.name} already exists")
            continue
        shutil.copy2(cf, dest)
        copied += 1

    print(f"\nCopied {copied} responses to {responses_dir}/")
    if unmatched_remaining:
        print(f"Manual match needed for: {', '.join(sorted(unmatched_remaining))}")


if __name__ == "__main__":
    main()
