from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = SCRIPT_DIR / "build_plan_close_context.py"
SPEC = importlib.util.spec_from_file_location("build_plan_close_context_script", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
plan_close_context = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan_close_context)


def run(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class BuildPlanCloseContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        run(self.repo, "init")
        run(self.repo, "config", "user.name", "Test User")
        run(self.repo, "config", "user.email", "test@example.com")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolve_touched_files_uses_worktree_status(self) -> None:
        tracked = self.repo / "tracked.py"
        tracked.write_text("print('one')\n")
        run(self.repo, "add", "tracked.py")
        run(self.repo, "commit", "-m", "init")

        tracked.write_text("print('two')\n")
        untracked = self.repo / "new_file.py"
        untracked.write_text("print('new')\n")

        touched = plan_close_context.resolve_touched_files(
            self.repo,
            base=None,
            head=None,
            files=None,
            tracked_only=False,
        )

        self.assertEqual(set(touched), {"new_file.py", "tracked.py"})

    def test_resolve_touched_files_tracked_only_excludes_untracked(self) -> None:
        tracked = self.repo / "tracked.py"
        tracked.write_text("print('one')\n")
        run(self.repo, "add", "tracked.py")
        run(self.repo, "commit", "-m", "init")

        tracked.write_text("print('two')\n")
        untracked = self.repo / "new_file.py"
        untracked.write_text("print('new')\n")

        touched = plan_close_context.resolve_touched_files(
            self.repo,
            base=None,
            head=None,
            files=None,
            tracked_only=True,
        )

        self.assertEqual(touched, ["tracked.py"])

    def test_build_packet_includes_diff_and_current_excerpt(self) -> None:
        target = self.repo / "module.py"
        target.write_text("value = 1\n")
        run(self.repo, "add", "module.py")
        run(self.repo, "commit", "-m", "initial")
        base = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        target.write_text("value = 2\nprint(value)\n")
        run(self.repo, "add", "module.py")
        run(self.repo, "commit", "-m", "update")
        head = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        packet = plan_close_context.build_packet(
            self.repo,
            base=base,
            head=head,
            files=None,
            tracked_only=False,
            scope_text="- Target users: internal\n- Scale: small\n- Rate of change: high\n",
            scope_file=None,
            max_diff_chars=10_000,
            max_file_chars=10_000,
            max_files=10,
        )

        self.assertIn("# Plan-Close Review Packet", packet)
        self.assertIn("## Scope", packet)
        self.assertIn("- `module.py`", packet)
        self.assertIn("value = 1", packet)
        self.assertIn("value = 2", packet)
        self.assertIn("print(value)", packet)


if __name__ == "__main__":
    unittest.main()
