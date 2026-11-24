"""codex-thread contract tests — offline, no app, no spend.

Guards the two things that broke before: (1) the removed socket subcommands must fail loud, not
hang on a dead ~/.codex/ipc/ipc.sock; (2) queue must shell the bundled CLI with the right argv;
(3) status must read the queue DB and a rollout's turn marker. HOME is redirected to a tmp dir so
the DB/rollout readers hit synthetic fixtures, not the real app state.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "bin" / "codex-thread"
THREAD = "01a20c2c-38eb-7b00-94bd-cd8866a63fa6"


def run(*args: str, home: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if home is not None:
        env["HOME"] = str(home)
    return subprocess.run([sys.executable, str(TOOL), *args], input=stdin,
                          capture_output=True, text=True, env=env)


def test_help_lists_the_two_live_subcommands():
    out = run("--help").stdout
    assert "queue" in out and "status" in out


def test_removed_subcommands_fail_loud():
    for mode in ("steer", "settings", "unqueue"):
        r = run(mode, "x")
        assert r.returncode == 3, (mode, r.returncode, r.stderr)
        assert "removed" in r.stderr.lower()
        assert "bypass" in r.stderr.lower() or "peer-authorized" in r.stderr.lower()
        # it must NOT reach for the dead socket at all
        assert "ipc.sock" in r.stderr  # names what was removed, as guidance


def test_queue_dry_run_builds_bundled_argv():
    r = run("queue", THREAD, "--message", "hello world", "--resume", "--dry-run")
    assert r.returncode == 0, r.stderr
    argv = json.loads(r.stdout)
    assert argv[0].endswith("CodexCLI.app/Contents/MacOS/codex")
    assert argv[1] == "queue"
    assert "--thread" in argv and THREAD in argv
    i = argv.index("--message")
    assert argv[i + 1] == "hello world"
    assert "--resume" in argv


def test_queue_stdin_input():
    r = run("queue", THREAD, "-", "--dry-run", stdin="from stdin")
    assert r.returncode == 0, r.stderr
    argv = json.loads(r.stdout)
    assert argv[argv.index("--message") + 1] == "from stdin"


def test_queue_requires_exactly_one_input():
    r = run("queue", THREAD, "--dry-run")
    assert r.returncode != 0
    assert "exactly one" in (r.stderr + r.stdout)


def _fixture_home(tmp_path: Path, *, running: bool, extra_line: str = "") -> Path:
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    db = home / ".codex" / "queue_1.sqlite"
    con = sqlite3.connect(db)
    con.execute("create table queued_items (id TEXT PRIMARY KEY NOT NULL, thread_id TEXT NOT NULL, "
                "payload_json TEXT NOT NULL, queue_order INTEGER NOT NULL, created_at_ms INTEGER NOT NULL, "
                "updated_at_ms INTEGER NOT NULL)")
    con.execute("insert into queued_items values (?,?,?,?,?,?)",
                ("item-synthetic-1", THREAD, json.dumps({"UserInput": {"content": [{"type": "text", "text": "hi astra"}]}}),
                 0, 1764000000000, 1764000000000))
    con.commit()
    con.close()
    day = home / ".codex" / "sessions" / "2026" / "11" / "25"
    day.mkdir(parents=True)
    rollout = day / f"rollout-2026-11-25T00-00-00-{THREAD}.jsonl"
    marker = "task_started" if running else "task_complete"
    lines = [
        json.dumps({"type": "event_msg", "payload": {"type": marker}, "timestamp": "2026-11-25T08:00:00.000Z"}),
    ]
    if extra_line:
        lines.append(extra_line)
    rollout.write_text("\n".join(lines) + "\n")
    return home


def test_status_reads_synthetic_queue_and_running_turn(tmp_path):
    home = _fixture_home(tmp_path, running=True)
    r = run("status", THREAD, home=home)
    assert r.returncode == 0, r.stderr
    assert "item-synthetic-1" in r.stdout
    assert "running" in r.stdout
    assert "queued (1)" in r.stdout


def test_status_idle_turn(tmp_path):
    home = _fixture_home(tmp_path, running=False)
    assert "idle" in run("status", THREAD, home=home).stdout


def test_status_grep_present_and_absent(tmp_path):
    needle = "numbers are the lever"
    home = _fixture_home(tmp_path, running=True,
                         extra_line=json.dumps({"type": "message", "text": "the " + needle + " today"}))
    assert "present" in run("status", THREAD, "--grep", needle, home=home).stdout
    assert "absent" in run("status", THREAD, "--grep", "no such phrase here xyz", home=home).stdout
