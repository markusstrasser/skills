#!/usr/bin/env python3
"""Stop hook: shadow-detect plan-complete claims without closeout artifacts.

Modes (PLAN_CLOSE_GATE env):
  shadow (default) — append JSONL only, exit 0
  advisory         — stderr envelope, exit 0
  block            — stderr envelope, exit 2

Measure-before-enforce. Analyze with: just plan-close-report
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

COMPLETE = re.compile(
    r"\b("
    r"plan\s+(?:is\s+)?(?:complete|done|finished|fully\s+executed)|"
    r"(?:fully|entirely)\s+executed\s+the\s+plan|"
    r"implementation\s+is\s+complete|"
    r"migration\s+is\s+(?:done|complete)|"
    r"all\s+(?:phases?|steps?)\s+(?:are\s+)?complete"
    r")\b",
    re.I,
)
HISTORICAL = re.compile(
    r"\b(?:was\s+(?:complete|done|finished)|(?:earlier|previous)\s+plan)\b",
    re.I,
)
LOG_FILE = Path.home() / ".claude" / "surface-gates" / "plan-close-shadow.jsonl"
FIX_CMD = (
    "uv run python3 ~/Projects/skills/critique/scripts/review_gate.py triage "
    "--mode close --repo . --packet .model-review/plan-close-context.md && "
    "uv run python3 ~/Projects/skills/critique/scripts/model-review.py "
    "--dispatch-manifest .model-review/dispatch.json "
    "--context .model-review/plan-close-context.md --project . "
    "\"Review plan closeout.\""
)


def _repo_root(cwd: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, OSError):
        return cwd


def _last_assistant_message(data: dict) -> str:
    msg = data.get("last_assistant_message") or ""
    if msg:
        return msg
    transcript = data.get("transcript_path") or ""
    if not transcript:
        return ""
    path = Path(transcript).expanduser()
    if not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("type") == "assistant" and isinstance(row.get("message"), dict):
            content = row["message"].get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                return "\n".join(p for p in parts if p)
    return ""


def _artifacts(repo_root: Path) -> dict[str, bool]:
    review = repo_root / ".model-review"
    verified = False
    if review.is_dir():
        for d in review.iterdir():
            if d.is_dir() and (d / "verified-disposition.md").is_file():
                verified = True
                break
    return {
        "dispatch_json": (review / "dispatch.json").is_file(),
        "plan_close_context": (review / "plan-close-context.md").is_file(),
        "verified_disposition": verified,
    }


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    if data.get("stop_hook_active"):
        return 0

    msg = _last_assistant_message(data)
    if not msg or not COMPLETE.search(msg):
        return 0
    if HISTORICAL.search(msg):
        return 0

    cwd = Path(data.get("cwd") or os.getcwd())
    repo_root = _repo_root(cwd)
    artifacts = _artifacts(repo_root)

    if artifacts["dispatch_json"] and artifacts["verified_disposition"]:
        return 0

    mode = os.environ.get("PLAN_CLOSE_GATE", "shadow").lower()
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "cwd": str(cwd),
        "repo_root": str(repo_root),
        "session_id": data.get("session_id"),
        "artifacts": artifacts,
        "snippet": msg[:400],
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    if mode == "shadow":
        return 0

    envelope = (
        "[plan-close-gate] BLOCKED — plan completion claimed without closeout artifacts\n"
        f"dispatch.json={artifacts['dispatch_json']} "
        f"verified-disposition={artifacts['verified_disposition']}\n"
        f"fix: {FIX_CMD}"
    )
    print(envelope, file=sys.stderr)
    return 2 if mode == "block" else 0


if __name__ == "__main__":
    sys.exit(main())
