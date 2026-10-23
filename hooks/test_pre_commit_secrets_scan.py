"""Behavior tests for pre-commit-secrets-scan.sh.

Each case stages files in a throwaway repo and runs the hook: a staged credential must
block, clean changes and git-crypt paths must pass, and a missing gitleaks must pass with
[DEGRADED]. Run:
  uv run --no-project python3 hooks/test_pre_commit_secrets_scan.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

HOOK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pre-commit-secrets-scan.sh"
)
# Built at runtime so this file never holds a credential-shaped literal.
FAKE_PAT = "ghp_" + "Zq8Lr2Vx7Kp4Nw9Bt3Hy6Jd1Fs5Gm0Ca2Ue7Q"


def run_case(files, attributes="", path_env=None):
    with tempfile.TemporaryDirectory() as repo:
        git = ["git", "-C", repo]
        subprocess.run([*git, "init", "-q"], check=True)
        if attributes:
            files = {**files, ".gitattributes": attributes}
        for name, text in files.items():
            full = os.path.join(repo, name)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write(text)
        subprocess.run([*git, "add", "-A"], check=True)
        env = {**os.environ}
        if path_env is not None:
            env["PATH"] = path_env
        return subprocess.run(
            ["bash", HOOK], cwd=repo, env=env, capture_output=True, text=True
        )


def main():
    if not shutil.which("gitleaks"):
        print("SKIP: gitleaks not installed")
        return 0
    no_gitleaks_path = ":".join(
        d
        for d in os.environ["PATH"].split(":")
        if not os.path.exists(os.path.join(d, "gitleaks"))
    )
    cases = [
        (
            "staged PAT blocks",
            run_case({"cfg.py": f'TOKEN = "{FAKE_PAT}"\n'}),
            1,
            "BLOCKED",
        ),
        ("clean change passes", run_case({"notes.md": "nothing secret here\n"}), 0, ""),
        (
            "git-crypt path skipped",
            run_case(
                {"private/cfg.py": f'TOKEN = "{FAKE_PAT}"\n'},
                "private/** filter=git-crypt\n",
            ),
            0,
            "",
        ),
        (
            "non-crypt path still blocks beside a crypt path",
            run_case(
                {
                    "private/a.py": f'T = "{FAKE_PAT}"\n',
                    "pub/b.py": f'T = "{FAKE_PAT}"\n',
                },
                "private/** filter=git-crypt\n",
            ),
            1,
            "BLOCKED",
        ),
        (
            "missing gitleaks degrades",
            run_case({"cfg.py": f'TOKEN = "{FAKE_PAT}"\n'}, path_env=no_gitleaks_path),
            0,
            "[DEGRADED]",
        ),
    ]
    failed = 0
    for name, proc, want_rc, want_text in cases:
        ok = proc.returncode == want_rc and want_text in proc.stderr + proc.stdout
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name} (rc={proc.returncode})")
        if not ok:
            print(proc.stdout + proc.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
