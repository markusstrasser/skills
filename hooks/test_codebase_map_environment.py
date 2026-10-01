"""Codebase hooks must never sync an inherited caller's Python environment."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


class CodebaseMapEnvironmentTests(unittest.TestCase):
    def check_hook(self, hook_name: str, *, runtime_exit: int = 0) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "caller"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            infra = root / "infra"
            (infra / "scripts").mkdir(parents=True)
            (infra / "scripts/refresh_codebase_map_on_commit.py").write_text("# fixture\n")
            binaries = root / "bin"
            binaries.mkdir()
            capture = root / "invocation.txt"
            launcher = binaries / "uv"
            launcher.write_text(
                '#!/bin/bash\n'
                'printf "%s\\n%s\\n" "${UV_PROJECT_ENVIRONMENT-unset}" '
                '"${VIRTUAL_ENV-unset}" > "$CODEBASE_CAPTURE"\n'
                'printf "%s\\n" "$@" >> "$CODEBASE_CAPTURE"\n'
                'exit "${CODEBASE_EXIT:-0}"\n'
            )
            launcher.chmod(0o755)
            environment = dict(os.environ)
            environment.update(
                PATH=f"{binaries}:{environment.get('PATH', '')}",
                AGENT_INFRA_ROOT=str(infra),
                CODEBASE_CAPTURE=str(capture),
                CODEBASE_EXIT=str(runtime_exit),
                UV_PROJECT_ENVIRONMENT=str(repo / ".venv"),
                VIRTUAL_ENV=str(repo / ".venv"),
            )
            environment.pop("SKIP_CODEBASE_MAP_REFRESH", None)
            environment.pop("UV_NO_SYNC", None)
            result = subprocess.run(
                ["bash", str(Path(__file__).with_name(hook_name))],
                cwd=repo,
                env=environment,
                input=json.dumps({"tool_input": {"file_path": str(repo / "source.py")}}),
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            deadline = time.monotonic() + 2
            while not capture.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(capture.exists(), "the actual hook must invoke its owned runtime")
            inherited_project, inherited_active, *arguments = capture.read_text().splitlines()
            self.assertEqual(inherited_project, "unset")
            self.assertEqual(inherited_active, "unset")
            self.assertIn("--no-sync", arguments)
            self.assertEqual(arguments[arguments.index("--directory") + 1], str(infra))
            self.assertIn(str(infra / "scripts/refresh_codebase_map_on_commit.py"), arguments)
            if runtime_exit:
                self.assertIn("refresh failed (non-blocking)", result.stderr)

    def test_precommit_uses_its_own_environment_without_sync(self) -> None:
        self.check_hook("pre-commit-codebase-map.sh")

    def test_posttool_uses_its_own_environment_without_sync(self) -> None:
        self.check_hook("posttool-codebase-map.sh")

    def test_precommit_reports_runtime_failure(self) -> None:
        self.check_hook("pre-commit-codebase-map.sh", runtime_exit=17)

    def test_posttool_reports_runtime_failure(self) -> None:
        self.check_hook("posttool-codebase-map.sh", runtime_exit=17)


if __name__ == "__main__":
    unittest.main()
