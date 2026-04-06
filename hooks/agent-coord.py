#!/usr/bin/env python3
"""
Agent coordination for multiple Claude Code sessions.

Maintains a plain-text status file (.claude/agent-work.md) in the project root
so agents can see what other sessions are doing and avoid conflicts.

Works from any project — resolves .claude/ relative to git root or CWD.

Usage (from any project):
    python3 ~/Projects/skills/hooks/agent-coord.py status
    python3 ~/Projects/skills/hooks/agent-coord.py register "Updating search pipeline"
    python3 ~/Projects/skills/hooks/agent-coord.py check src/search.py
    python3 ~/Projects/skills/hooks/agent-coord.py deregister
"""

import argparse
import fcntl
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _find_project_root() -> Path:
    """Find .claude/ dir via git root, then CWD fallback."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


WORK_FILE = _find_project_root() / ".claude" / "agent-work.md"


def _find_claude_ancestor() -> tuple[str, int]:
    """Walk up the process tree to find the 'claude' process.

    Returns (terminal_id, claude_pid). Claude Code spawns ephemeral
    zsh subshells for each Bash tool call, so os.getppid() is useless.
    We walk up via `ps` until we find a process whose command is 'claude'.
    """
    pid = os.getpid()
    for _ in range(10):  # safety limit
        try:
            out = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "pid=,ppid=,comm="],
                text=True,
            ).strip()
        except subprocess.CalledProcessError:
            break
        parts = out.split(None, 2)
        if len(parts) < 3:
            break
        this_pid, ppid, comm = int(parts[0]), int(parts[1]), parts[2]
        if comm.strip().lower() == "claude":
            return _tty_for_pid(this_pid), this_pid
        pid = ppid
    return _tty_for_pid(os.getpid()), os.getppid()


def _tty_for_pid(pid: int) -> str:
    """Get terminal name for a PID, e.g. 's002'."""
    try:
        tty = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "tty="], text=True
        ).strip()
        if tty and tty != "??":
            return tty
    except Exception:
        pass
    try:
        tty = os.ttyname(sys.stdin.fileno())
        return tty.split("/")[-1].replace("ttys", "s")
    except Exception:
        return f"pid-{pid}"


def get_terminal() -> str:
    return _find_claude_ancestor()[0]


def get_pid() -> int:
    return _find_claude_ancestor()[1]


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def parse_entries(text: str) -> list[dict]:
    entries = []
    current = None
    for line in text.splitlines():
        header = re.match(r"^## (\S+) \(PID (\d+)\)", line)
        if header:
            if current:
                entries.append(current)
            current = {
                "terminal": header.group(1),
                "pid": int(header.group(2)),
                "lines": [line],
            }
        elif current is not None:
            current["lines"].append(line)
    if current:
        entries.append(current)
    return entries


def prune_stale(entries: list[dict]) -> list[dict]:
    return [e for e in entries if pid_alive(e["pid"])]


def read_entries() -> list[dict]:
    if not WORK_FILE.exists():
        return []
    with open(WORK_FILE, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            text = f.read()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return prune_stale(parse_entries(text))


def write_entries(entries: list[dict]):
    WORK_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Active Claude Code Sessions", ""]
    lines.append(f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("_Stale entries (dead PIDs) are auto-pruned on every read._")
    lines.append("")
    for e in entries:
        lines.extend(e["lines"])
        lines.append("")
    with open(WORK_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write("\n".join(lines) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def cmd_status(args):
    entries = read_entries()
    write_entries(entries)
    if not entries:
        print("No active agents.")
        return
    print(WORK_FILE.read_text())


def cmd_register(args):
    entries = read_entries()
    terminal = get_terminal()
    pid = get_pid()
    entries = [e for e in entries if e["terminal"] != terminal]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body_lines = [
        f"## {terminal} (PID {pid})",
        f"Started: {now}",
        "",
        args.description,
    ]
    if args.files:
        body_lines.append("")
        body_lines.append(f"Files: {', '.join(args.files)}")
    if args.modal:
        body_lines.append(f"Modal jobs: {', '.join(args.modal)}")

    entries.append({"terminal": terminal, "pid": pid, "lines": body_lines})
    write_entries(entries)
    print(f"Registered {terminal} (PID {pid})")


def cmd_check(args):
    entries = read_entries()
    terminal = get_terminal()
    conflicts = []
    for e in entries:
        if e["terminal"] == terminal:
            continue
        if args.path in "\n".join(e["lines"]):
            conflicts.append(e["terminal"])
    if conflicts:
        print(f"WARNING: {args.path} is being worked on by: {', '.join(conflicts)}")
        sys.exit(1)
    else:
        print(f"No conflicts for {args.path}")


def cmd_deregister(args):
    entries = read_entries()
    terminal = get_terminal()
    entries = [e for e in entries if e["terminal"] != terminal]
    write_entries(entries)
    print(f"Deregistered {terminal}")


def main():
    parser = argparse.ArgumentParser(description="Agent coordination")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show all active agents")

    reg = sub.add_parser("register", help="Register your work")
    reg.add_argument("description", nargs="?", default="Session active")
    reg.add_argument("--files", nargs="*", help="Files you're modifying")
    reg.add_argument("--modal", nargs="*", help="Modal jobs you're running")

    chk = sub.add_parser("check", help="Check if a file has conflicts")
    chk.add_argument("path", help="File path to check")

    sub.add_parser("deregister", help="Clean up when done")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"status": cmd_status, "register": cmd_register,
     "check": cmd_check, "deregister": cmd_deregister}[args.command](args)


if __name__ == "__main__":
    main()
