#!/usr/bin/env python3
"""Regression guard for pretool-research-provenance-warn.sh cry-wolf (2026-06-30).

The bug: the PreToolUse warn checked only the EDITED CHUNK (new_string), not the
file. So every edit to an already-tagged research memo re-warned — it fired 144x
across substrate sessions (32x on one HUMAN.md outbox, 26x on a handoff doc, 20x on
_done.md), disagreeing with the Stop gate (stop-research-gate.sh) that reads the
full file and would have PASSED them. A guard that cries wolf trains the agent to
ignore it.

The contract this locks: the write-time WARN fires iff the stop-time BLOCK would —
i.e. judged against the whole file, not the chunk; HUMAN.md outboxes are never
gated; and the tag taxonomy matches the gate's (comma-forms, [DOI:/[PMID:).

# precommit-trigger: pretool-research-provenance-warn.sh test_provenance_warn_crywolf.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "pretool-research-provenance-warn.sh"
WARN_MARK = "research file written without source tags"


def _run(envelope: dict) -> str:
    """Invoke the hook with the envelope on stdin; return stdout."""
    p = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        timeout=20,
    )
    return p.stdout


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _warned(out: str) -> bool:
    return WARN_MARK in out


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        research = Path(td) / "docs" / "research"

        # 1. THE FIX: editing an already-tagged file with an untagged chunk must NOT warn.
        tagged = research / "tagged-memo.md"
        _write(tagged, "# Memo\n\nFinding X. [SOURCE: https://example.org/x]\n")
        out = _run({"tool_name": "Edit", "tool_input": {
            "file_path": str(tagged),
            "old_string": "Finding X.",
            "new_string": "Finding X, expanded with more prose and no inline tag.",
        }})
        assert not _warned(out), f"cry-wolf: warned editing an already-tagged file:\n{out}"

        # 2. GUARD PRESERVED: editing an UNtagged file with an untagged chunk must warn.
        untagged = research / "untagged-memo.md"
        _write(untagged, "# Memo\n\nPlain claim with no source whatsoever.\n")
        out = _run({"tool_name": "Edit", "tool_input": {
            "file_path": str(untagged),
            "old_string": "Plain claim",
            "new_string": "Plain claim still unsourced",
        }})
        assert _warned(out), "guard regressed: did NOT warn on a genuinely untagged file"

        # 3. GUARD PRESERVED: the edit that ADDS the first tag must NOT warn (chunk carries it).
        out = _run({"tool_name": "Edit", "tool_input": {
            "file_path": str(untagged),
            "old_string": "Plain claim",
            "new_string": "Plain claim [SOURCE: https://example.org/y]",
        }})
        assert not _warned(out), "warned even though the incoming chunk adds a tag"

        # 4. HUMAN.md outbox is never gated, even untagged, even under docs/research/.
        human = research / "kg-verification" / "HUMAN.md"
        _write(human, "# Asks\n\n- Should we ship X? (no source, it's an outbox)\n")
        out = _run({"tool_name": "Edit", "tool_input": {
            "file_path": str(human),
            "old_string": "Should we ship X?",
            "new_string": "Should we ship X or Y?",
        }})
        assert not _warned(out), "cry-wolf: warned on a HUMAN.md escalation outbox"

        # 5. TAXONOMY PARITY: comma-qualified [DATA, src, date] counts (gate accepts it).
        comma = research / "comma-memo.md"
        _write(comma, "# Memo\n\nResult Z. [DATA, FlowKit, 2026-06-01]\n")
        out = _run({"tool_name": "Edit", "tool_input": {
            "file_path": str(comma),
            "old_string": "Result Z.",
            "new_string": "Result Z, restated without an inline tag here.",
        }})
        assert not _warned(out), f"taxonomy drift: warned despite [DATA, ...] comma-form:\n{out}"

        # 6. Write of a brand-new untagged research file still warns (full-file = the content).
        out = _run({"tool_name": "Write", "tool_input": {
            "file_path": str(research / "new-memo.md"),
            "content": "# New\n\nA fresh unsourced assertion.\n",
        }})
        assert _warned(out), "guard regressed: did NOT warn on an untagged new Write"

        # 7. Non-research path is out of scope entirely.
        out = _run({"tool_name": "Write", "tool_input": {
            "file_path": str(Path(td) / "src" / "thing.py"),
            "content": "x = 1  # no provenance needed\n",
        }})
        assert not _warned(out), "warned on a non-research file (out of scope)"

    print("OK: provenance-warn cry-wolf regression test passed (7 cases)")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
