"""A running lane script must survive an edit of its file. Bash reads a script while it runs it, so
an edit in place that shifts the bytes hands a running lane other text: magic-crit's lane-opencode
failed with "syntax error near unexpected token `same'" when its worker finished, after the
headless note grew under it (2026-10-27). bin/lane exits on the line that runs main; bin/lane-opencode
is one brace group, which bash parses whole before running any of it."""
import json
import os
import subprocess
import tempfile
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


def test_reap_debuggers_kills_only_those_under_the_given_directories(tmp_path):
    # sleep through a symlink named debugserver stands in for lldb's orphan: pgrep matches the
    # name exec used. A copy of the platform binary would be killed at exec.
    fake = tmp_path / "debugserver"
    fake.symlink_to("/bin/sleep")
    lane, other = tmp_path / "lane" / "worktree", tmp_path / "other"
    (lane / "deep").mkdir(parents=True)
    other.mkdir()
    inside = subprocess.Popen([str(fake), "60"], cwd=lane / "deep")
    outside = subprocess.Popen([str(fake), "60"], cwd=other)
    try:
        time.sleep(0.2)
        result = subprocess.run(
            [str(BIN / "lane-reap-debuggers"), str(lane)], capture_output=True, text=True, check=True
        )
        assert inside.wait(timeout=5) != 0
        assert f"killed debugserver {inside.pid}" in result.stdout
        assert outside.poll() is None
    finally:
        for process in (inside, outside):
            if process.poll() is None:
                process.kill()
                process.wait()


@pytest.fixture
def agy_lane(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "agy").symlink_to(Path(__file__).with_name("fixtures") / "lane_fake_agy.py")
    # Match the shell suite's fake start time and give retire a free checkout.
    for tool, output in {"ps": "Thu Aug 27 18:00:00 2026", "lsof": "p1\nf cwd\nn/"}.items():
        path = fake_bin / tool
        path.write_text(f"#!/bin/sh\nprintf '%s\\n' '{output}'\n")
        path.chmod(0o755)
    env = {key: value for key, value in os.environ.items() if not key.startswith(("AGY_", "LANE_"))}
    home, repo, brief = tmp_path / "lanes", tmp_path / "repo", tmp_path / "brief.md"
    account = tmp_path / "account"
    account.mkdir()
    env.update(HOME=str(account), PATH=f"{fake_bin}:{env['PATH']}", FAKE_AGY_CALLS=str(tmp_path / "calls"),
               LANE_HOME=str(home), LANE_NICE="0", LANE_MAX_RUNNING="none",
               LANE_ARCHIVE_VOLUME=str(tmp_path / "no-archive"), DISK_FLOOR_GIB="0",
               GOOGLE_API_KEY="remove", GEMINI_API_KEY="remove", GOOGLE_APPLICATION_CREDENTIALS="remove",
               LANE_AGY_PASS_ENV="FAKE_AGY_MODE:FAKE_AGY_CALLS")
    repo.mkdir()
    (repo / "tracked.txt").write_text("base\n")
    brief.write_text("Do the fake AGY task.\n")
    for args in [("init", "-q"), ("add", "tracked.txt"),
                 ("-c", "user.name=Lane Test", "-c", "user.email=lane@example.invalid", "commit", "-qm", "base")]:
        subprocess.run(["git", "-C", str(repo), *args], env=env, check=True)

    def invoke(*args, **overrides):
        # Pipes engage lane's /dev/fd-based output relay, which the managed sandbox denies.
        with tempfile.TemporaryFile(mode="w+") as out, tempfile.TemporaryFile(mode="w+") as err:
            result = subprocess.run([str(BIN / "lane"), *args], env=env | overrides,
                                    stdout=out, stderr=err, timeout=25, check=False)
            out.seek(0)
            err.seek(0)
            stdout = out.read()
            assert result.returncode == 0, stdout + err.read()
            return stdout

    return invoke, home, repo, brief


def wait_for_lane_file(path):
    deadline = time.monotonic() + 15
    while not path.exists():
        assert time.monotonic() < deadline, f"missing {path}"
        time.sleep(0.05)
    return path.read_text().strip()


def agy_calls(tmp_path):
    path = tmp_path / "calls"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_agy_lane_captures_conversation_and_resumes_in_its_checkout(tmp_path, agy_lane):
    lane, home, repo, brief = agy_lane
    shared = tmp_path / "shared cache"
    shared.mkdir()
    env_deny, repo_deny = shared / "env denied", shared / "repo denied"
    alias = tmp_path / "alias"
    alias.symlink_to(shared, target_is_directory=True)
    other_deny = tmp_path / "another repo denial"
    for path in (repo_deny, other_deny):
        subprocess.run(["git", "-C", str(repo), "config", "--add", "lane.agyDenyRead", str(path)], check=True)
    launch = lane("run", "gem", "--repo", str(repo), "--brief", str(brief), "--worker", "agy", "--keep-checkout",
                  FAKE_AGY_MODE="hold", LANE_AGY_ADD_DIRS=str(shared),
                  LANE_AGY_DENY_READ=f"{alias / env_deny.name}:{repo_deny}")
    assert "agy_model=gemini-4-neon agy_effort=xhigh" in launch
    assert wait_for_lane_file(home / "gem.agy-session") == "fake-conversation"
    assert json.loads(lane("state", "gem"))["state"] == "RUNNING"
    stamp = time.time() - 10
    os.utime(home / "gem.log", (stamp, stamp))
    assert "gem STALLED " in " ".join(lane("ls", "--stall-min", "0").split())
    (tmp_path / "calls.release").touch()
    assert wait_for_lane_file(home / "gem.done") == "EXIT=0"

    probe, turn = agy_calls(tmp_path)
    assert probe["args"][probe["args"].index("-p") + 1] == "/model"
    checkout = repo / ".claude/worktrees/codex-gem"
    assert turn["cwd"] == str(checkout)
    args = turn["args"]
    assert args[args.index("--model") + 1] == "gemini-4-neon-xhigh"
    assert args[args.index("--add-dir") + 1] == str(shared)
    assert args[args.index("--mode") + 1] == "accept-edits" and "--sandbox" in args
    settings = json.loads(args[args.index("--settings") + 1])
    assert settings["useG1Credits"] is False and settings["allowNonWorkspaceAccess"] is False
    assert settings["permissions"]["allow"] == ["read_file(*)", "read_url(*)"]
    deny = settings["permissions"]["deny"]
    assert {rule for rule in deny if rule.startswith("read_file(")} == {
        f"read_file({path})" for path in (
            env_deny, repo_deny, alias / env_deny.name, other_deny,
            *(tmp_path / "account" / suffix for suffix in
              (".modal.toml", ".config/secrets", ".config/sops", ".ssh", ".aws", ".netrc", ".env", ".codex",
               ".claude", ".config/gh", ".git-credentials", ".docker", ".npmrc", ".pypirc")),
        )
    }
    assert {f"write_file({checkout}/.git)", f"write_file({repo}/.git)", f"write_file({repo}/.git/worktrees/codex-gem)"} <= set(deny)
    assert {"command(security)", "command(/usr/bin/security)"} <= set(deny)
    assert "Do the fake AGY task." in args[args.index("-p") + 1]
    assert '"event": "step_update"' in (home / "gem.log").read_text()

    note = tmp_path / "resume.md"
    note.write_text("Continue the AGY task.\n")
    new_env_deny, new_repo_deny = shared / "new env denial", shared / "new repo denial"
    subprocess.run(["git", "-C", str(repo), "config", "--add", "lane.agyDenyRead", str(new_repo_deny)], check=True)
    lane("resume", "gem", "--note", str(note), LANE_AGY_MODEL="gemini-4-carbon", LANE_AGY_EFFORT="medium",
         LANE_AGY_DENY_READ=str(new_env_deny))
    assert wait_for_lane_file(home / "gem.done") == "EXIT=0"
    assert json.loads(lane("state", "gem"))["state"] == "DONE:0"
    resumed = agy_calls(tmp_path)[-1]["args"]
    assert resumed[resumed.index("--conversation") + 1] == "fake-conversation"
    assert resumed[resumed.index("--model") + 1] == "gemini-4-carbon-medium"
    assert resumed[resumed.index("--add-dir") + 1] == str(shared)
    resumed_deny = json.loads(resumed[resumed.index("--settings") + 1])["permissions"]["deny"]
    assert set(resumed_deny) == {*deny, f"read_file({new_env_deny})", f"read_file({new_repo_deny})"}
    assert "Continue the AGY task." in resumed[resumed.index("-p") + 1]
    assert "agy changed this" in (checkout / "tracked.txt").read_text()
    lane("reap", "gem", "--force")
    assert not checkout.exists() and not (home / "gem.agy-session").exists()
    assert "+agy changed this" in next((home / "gem.harvest").glob("*/lane.patch")).read_text()


def test_agy_lane_reads_deny_config_from_source_repo_of_hook_checkout(tmp_path, agy_lane):
    lane, home, repo, brief = agy_lane
    hook = tmp_path / "checkout"
    hook.write_text('#!/bin/sh\nexec git clone -q --no-local "$LANE_REPO" "$1"\n')
    hook.chmod(0o755)
    for key, value in (("lane.checkout", hook), ("lane.agyDenyRead", repo)):
        subprocess.run(["git", "-C", str(repo), "config", "--add", key, str(value)], check=True)
    lane("run", "gem", "--repo", str(repo), "--brief", str(brief), "--worker", "agy", "--keep-checkout")
    assert wait_for_lane_file(home / "gem.done") == "EXIT=0"
    turn = agy_calls(tmp_path)[-1]
    assert turn["cwd"] == str(home / "checkouts/gem")
    settings = json.loads(turn["args"][turn["args"].index("--settings") + 1])
    assert f"read_file({repo})" in settings["permissions"]["deny"]


@pytest.mark.parametrize("source", ["LANE_AGY_DENY_READ", "lane.agyDenyRead"])
def test_agy_lane_rejects_relative_denials_before_launch(tmp_path, agy_lane, source):
    lane, home, repo, brief = agy_lane
    overrides = {}
    if source == "lane.agyDenyRead":
        subprocess.run(["git", "-C", str(repo), "config", "--add", source, "donor"], check=True)
    else:
        overrides[source] = "donor"
    lane("run", "gem", "--repo", str(repo), "--brief", str(brief), "--worker", "agy", "--no-worktree", **overrides)
    assert wait_for_lane_file(home / "gem.done") == "EXIT=1"
    assert f"{source} must name absolute paths" in (home / "gem.log").read_text()
    assert not agy_calls(tmp_path)


@pytest.mark.parametrize(("mode", "budget", "rc", "message"), [
    ("quota", "1200", 86, "Antigravity usage quota exhausted"),
    ("capacity", "0", 85, "capacity retry budget of 0s exhausted"),
    ("capacity-once", "8", 0, "Retrying in 5s"),
])
def test_agy_lane_classifies_quota_and_retries_capacity(tmp_path, agy_lane, mode, budget, rc, message):
    lane, home, repo, brief = agy_lane
    lane("run", "gem", "--repo", str(repo), "--brief", str(brief), "--worker", "agy", "--no-worktree",
         FAKE_AGY_MODE=mode, LANE_AGY_CAPACITY_WAIT_S=budget)
    assert wait_for_lane_file(home / "gem.done") == f"EXIT={rc}"
    assert message in (home / "gem.log").read_text()
    calls = agy_calls(tmp_path)
    assert len(calls) == (3 if rc == 0 else 2)
    if rc == 0:
        args = calls[-1]["args"]
        assert args[args.index("--conversation") + 1] == "fake-conversation"


def test_agy_lane_passes_no_credentials_and_skips_shell_startup(tmp_path, agy_lane):
    lane, home, repo, brief = agy_lane
    lane("run", "gem", "--repo", str(repo), "--brief", str(brief), "--worker", "agy", "--no-worktree",
         CANARY_API_KEY="canary", LANE_CANARY_TOKEN="canary", GIT_ASKPASS="canary", ODD_PASSWORD="canary")
    assert wait_for_lane_file(home / "gem.done") == "EXIT=0"
    calls = agy_calls(tmp_path)
    assert len(calls) == 2
    for call in calls:
        names = set(call["env"])
        assert not names & {"CANARY_API_KEY", "LANE_CANARY_TOKEN", "GIT_ASKPASS", "ODD_PASSWORD"}
        assert {"HOME", "PATH", "ZDOTDIR", "GIT_OPTIONAL_LOCKS"} <= names
        assert call["zdotdir"] == []


@pytest.mark.parametrize(("mode", "rc", "message"), [
    ("slow-model-once", 0, "/model probe timed out after 1s (attempt 1/3); retrying in 0s"),
    ("slow-model", 1, "agy /model probe timed out after 1s, 3 attempts"),
])
def test_agy_lane_retries_a_slow_model_probe(tmp_path, agy_lane, mode, rc, message):
    lane, home, repo, brief = agy_lane
    lane("run", "gem", "--repo", str(repo), "--brief", str(brief), "--worker", "agy", "--no-worktree",
         FAKE_AGY_MODE=mode, LANE_AGY_PROBE_TIMEOUT_S="1", LANE_AGY_PROBE_RETRY_S="0")
    assert wait_for_lane_file(home / "gem.done") == f"EXIT={rc}"
    assert message in (home / "gem.log").read_text()


@pytest.mark.parametrize("config", ["gcp", "modelProvider", "adc", "wrong-selection"])
def test_agy_lane_preflight_refuses_paid_routes_and_model_fallback(tmp_path, agy_lane, config):
    lane, home, repo, brief = agy_lane
    overrides = {}
    if config == "adc":
        overrides["AGY_ADC_AUTH"] = "1"
    elif config == "wrong-selection":
        overrides["FAKE_AGY_MODE"] = config
    else:
        settings = tmp_path / "account/.gemini/antigravity-cli/settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({config: "configured"}))
    lane("run", "gem", "--repo", str(repo), "--brief", str(brief), "--worker", "agy", "--no-worktree", **overrides)
    assert wait_for_lane_file(home / "gem.done") == "EXIT=1"
    log = (home / "gem.log").read_text()
    if config == "wrong-selection":
        assert "agy did not confirm gemini-4-neon-xhigh" in log
        assert len(agy_calls(tmp_path)) == 1
    else:
        assert "consumer Google Account sign-in required" in log
        assert not agy_calls(tmp_path)
