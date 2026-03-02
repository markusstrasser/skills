#!/usr/bin/env python3
"""Parse git commit message and check format rules.

Reads hook JSON from stdin, outputs one of:
  SKIP        — not a git commit
  BLOCK:msg   — must block (Co-Authored-By)
  WARN:msg    — advisory warnings (pipe-separated)
  OK          — all checks pass
"""

import json
import re
import sys


def main():
    try:
        d = json.load(sys.stdin)
        cmd = d.get("tool_input", {}).get("command", "")
    except Exception:
        print("SKIP")
        return

    if "git commit" not in cmd:
        print("SKIP")
        return

    # Blocking: Co-Authored-By: Claude
    if re.search(r"Co-Authored-By.*Claude", cmd, re.IGNORECASE):
        print("BLOCK:Commit contains Co-Authored-By: Claude \u2014 remove it per global CLAUDE.md rules.")
        return

    # Extract commit message from heredoc or -m flag
    msg = ""
    heredoc = re.search(r"<<\s*'?EOF'?\s*\n(.*?)\nEOF", cmd, re.DOTALL)
    if heredoc:
        msg = heredoc.group(1)
    else:
        m_match = re.search(r'-m\s+"(.*?)"', cmd, re.DOTALL)
        if not m_match:
            m_match = re.search(r"-m\s+'(.*?)'", cmd, re.DOTALL)
        if m_match:
            msg = m_match.group(1)

    if not msg.strip():
        print("SKIP")
        return

    warnings = []
    lines = msg.strip().split("\n")
    subject = lines[0].strip()

    # Check [prefix]
    if not re.search(r"\[[-a-zA-Z0-9]+\]", subject):
        warnings.append("Missing [scope] prefix in subject.")

    # Check Type: trailer
    if not re.search(r"^Type:", msg, re.MULTILINE):
        warnings.append(
            "Missing Type: trailer. Valid: feature|fix|refactor|research|"
            "architecture|experiment|measurement|wiring|cleanup|governance."
        )

    # Check em-dash (U+2014)
    if "\u2014" not in subject:
        warnings.append(
            "Subject lacks em-dash separator. "
            "Format: [scope] Verb thing \u2014 why/impact."
        )

    # Check body presence (shell will filter by staged file count)
    body_lines = [
        l
        for l in lines[1:]
        if l.strip() and not re.match(r"^[A-Za-z-]+:\s", l)
    ]
    if len(body_lines) < 1:
        warnings.append("NOBODY")

    if warnings:
        print("WARN:" + " | ".join(warnings))
    else:
        print("OK")


if __name__ == "__main__":
    main()
