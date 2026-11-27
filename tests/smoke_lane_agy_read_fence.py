"""Exercise the real lane-agy worker on disposable files and verify its tool events."""

import argparse
import json
import os
import resource
import secrets
import shlex
import subprocess
import tempfile
import time
from pathlib import Path

WORKER = Path(__file__).resolve().parents[1] / "bin/lane-agy"


def tool_events(log):
    for line in log.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("event") == "step_update":
            step = event["step_update"]
            if step["state"] in ("DONE", "ERROR") and step.get("tool_info"):
                yield step["tool_info"]


def check_read(events, path, marker, denied):
    command = f"/bin/cat {shlex.quote(str(path))}"
    shell = [tool for tool in events if tool["name"] == "run_command"
             and shlex.split(tool["parameters"].get("CommandLine", "")) == ["/bin/cat", str(path)]]
    files = [tool for tool in events if tool["name"] in {"read_file", "view_file"}
             and tool["parameters"].get("Path") == str(path)]
    shell_output = "\n".join(tool.get("output", "") for tool in shell)
    file_errors = "\n".join(tool.get("error", {}).get("message", "") for tool in files)
    if denied:
        shell_ok = f"cat: {path}: Operation not permitted" in shell_output
        file_ok = bool(files and "Matches user-configured deny rule" in file_errors
                       and all(tool.get("error") for tool in files))
    else:
        shell_ok = marker in shell_output
        file_ok = any(tool.get("output") and not tool.get("error") for tool in files)
    print(f"shell {'PASS' if shell_ok else 'FAIL'} {command}\n{shell_output.strip() or '(no output)'}")
    file_output = "\n".join(tool.get("output", "") for tool in files)
    print(f"file  {'PASS' if file_ok else 'FAIL'} {path}\n{(file_errors or file_output).strip() or '(no event)'}")
    return shell_ok and file_ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch", type=Path, help="existing directory for the disposable repo, fixtures and log")
    opts = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="smoke-", dir=opts.scratch.resolve()))
    repo, extra, lane_home = root / "repo", root / "extra", root / "lanes"
    for path in (repo, extra / "donor", lane_home):
        path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    env_denied, repo_denied, allowed = extra / "credential.txt", extra / "donor/record.txt", root / "ordinary.txt"
    subprocess.run(["git", "-C", str(repo), "config", "--add", "lane.agyDenyRead", str(repo_denied.parent)],
                   check=True)
    markers = {path: f"AGY_SMOKE_{secrets.token_hex(8)}" for path in (env_denied, repo_denied, allowed)}
    for path, marker in markers.items():
        path.write_text(marker + "\n")
    prompt = (
        "Perform six actual tool calls for a permission smoke test using only these disposable files. "
        "For each listed file, run its exact cat command in the sandbox (a separate call), and also "
        "use the native file read tool on its absolute path. Continue to the next check after any denial. "
        "Use neither commands outside the sandbox nor other files. Report what happened and finish.\n"
        + "\n".join(f"{path}: /bin/cat {shlex.quote(str(path))}" for path in markers)
    )
    env = os.environ | {
        "LANE_REPO": str(repo), "LANE_HOME": str(lane_home), "LANE_NAME": "agy-read-fence-smoke",
        "LANE_AGY_MODEL": "gemini-4-neon", "LANE_AGY_EFFORT": "xhigh", "LANE_AGY_CAPACITY_WAIT_S": "0",
        "LANE_AGY_ADD_DIRS": str(extra), "LANE_AGY_DENY_READ": str(env_denied),
    }
    log_file = root / "agy.log"
    print(f"Tool log at {log_file}", flush=True)
    start = time.perf_counter()
    with log_file.open("w") as log:
        result = subprocess.run([str(WORKER), "false", prompt], cwd=repo, env=env,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                timeout=180, check=False)
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    print(f"worker exit={result.returncode}, elapsed={time.perf_counter() - start:.2f}s, maxrss={usage.ru_maxrss}")
    log = log_file.read_text()
    events = list(tool_events(log))
    if not events:
        print(log.strip())
    checks = [check_read(events, path, marker, denied=path != allowed) for path, marker in markers.items()]
    exposed = any(markers[path] in log for path in (env_denied, repo_denied))
    if exposed:
        print("FAIL a denied marker appeared in the worker log")
    return int(result.returncode != 0 or not all(checks) or exposed)


if __name__ == "__main__":
    raise SystemExit(main())
