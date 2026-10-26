"""A running lane script must survive an edit of its file. Bash reads a script while it runs it, so
an edit in place that shifts the bytes hands a running lane other text: magic-crit's lane-opencode
failed with "syntax error near unexpected token `same'" when its worker finished, after the
headless note grew under it (2026-10-27). bin/lane exits on the line that runs main; bin/lane-opencode
is one brace group, which bash parses whole before running any of it."""
import os
import subprocess
import time
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parent.parent / "bin"


def test_lane_exits_on_the_line_that_runs_main():
    assert (BIN / "lane").read_text().rstrip("\n").splitlines()[-1] == 'main "$@"; exit'


def test_lane_opencode_body_is_one_brace_group():
    lines = (BIN / "lane-opencode").read_text().rstrip("\n").splitlines()
    first = lines.index("{")
    assert all(line.startswith("#") for line in lines[:first])
    assert lines[-1] == "}"
    assert lines[-2].startswith("exit ")


def run_edited(tmp_path: Path, body: str) -> subprocess.CompletedProcess | None:
    """Runs a script that blocks on a fifo, prepends a comment line to its file in place while it
    blocks, then releases it. None when it is still running 3 s later."""
    script, fifo, ready = tmp_path / "script.sh", tmp_path / "fifo", tmp_path / "ready"
    script.write_text(body)
    os.mkfifo(fifo)
    proc = subprocess.Popen(["bash", str(script), str(fifo), str(ready)], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 5
    while not ready.exists():
        assert time.monotonic() < deadline, "the script never reached its read"
        time.sleep(0.01)
    time.sleep(0.1)
    script.write_text("#" + "x" * 98 + "\n" + body)  # the same inode, every byte shifted
    with open(fifo, "w") as writer:
        writer.write("go\n")
    try:
        out, err = proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return None
    return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)


BLOCKING = 'touch "$2"\nread line < "$1"\necho after-read\n'


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs a fifo")
def test_a_brace_group_runs_the_text_it_parsed_after_an_edit_in_place(tmp_path):
    guarded = run_edited(tmp_path, "#!/bin/bash\n{\n" + BLOCKING + "exit\n}\n")
    assert guarded is not None and (guarded.returncode, guarded.stdout) == (0, "after-read\n")


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs a fifo")
def test_a_bare_script_runs_other_text_after_an_edit_in_place(tmp_path):
    # The control: without the group, bash reads on from its old offset into the shifted bytes.
    bare = run_edited(tmp_path, "#!/bin/bash\n" + BLOCKING)
    assert bare is None or (bare.returncode, bare.stdout) != (0, "after-read\n")
