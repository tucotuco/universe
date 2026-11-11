"""Synthetic, offline coverage for the repository publication gate."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check_publication_safety.py"


def git(path: Path, *args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=path, input=data, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    )
    return result.stdout


class PublicationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "Fixture Author")
        git(self.repo, "config", "user.email", "fixture@example.invalid")

    def tearDown(self):
        self.temp.cleanup()

    def commit(self, message: str) -> str:
        git(self.repo, "add", "--all")
        git(self.repo, "commit", "-q", "-m", message)
        return git(self.repo, "rev-parse", "HEAD").decode().strip()

    def run_checker(self, *args: str):
        return subprocess.run(
            [sys.executable, str(CHECKER), *args], cwd=self.repo,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def test_clean_relative_and_placeholder_text_pass(self):
        (self.repo / "README.md").write_text(
            "Use docs/DEVELOPMENT-PROCESS.md and <LOCAL_CHECKOUT>.\n"
            "Illustrative locations: /Users/<account>/work and /private/tmp/<TEMP_DIR>.\n"
        )
        base = self.commit("clean initial state")
        (self.repo / "README.md").write_text("Updated docs/relative/path.md.\n")
        tip = self.commit("relative-only update")
        result = self.run_checker("--range", f"{base}..{tip}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("result=PASS", result.stdout)

    def test_detects_home_file_url_and_secret_without_echoing_values(self):
        (self.repo / "record.md").write_text("safe baseline\n")
        base = self.commit("initial baseline")
        (self.repo / "record.md").write_text(
            "source=" + "/" + "Users/alice/private/report.txt\n"
            "resource=" + "file:" + "/" * 2 + "/" + "home/alice/data.json\n"
            "password=" + "synthetic_super_secret_value_123\n"
        )
        tip = self.commit("safe-looking commit subject")
        result = self.run_checker("--range", f"{base}..{tip}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mac-home", result.stdout)
        self.assertIn("local-file-url", result.stdout)
        self.assertIn("secret-assignment", result.stdout)
        self.assertNotIn("alice", result.stdout)
        self.assertNotIn("synthetic_super_secret_value_123", result.stdout)

    def test_detects_content_removed_before_tip_and_commit_message(self):
        (self.repo / "record.md").write_text("safe baseline\n")
        base = self.commit("initial")
        (self.repo / "record.md").write_text("obsolete=" + "/" + "Users/alice/old.txt\n")
        middle = self.commit("draft path " + "/" + "home/alice/from-message.txt")
        (self.repo / "record.md").write_text("safe current file\n")
        tip = self.commit("remove draft path")
        self.assertNotEqual(base, middle)
        result = self.run_checker("--range", f"{base}..{tip}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mac-home", result.stdout)
        self.assertNotIn("alice", result.stdout)

    def test_detects_new_reference_to_already_reachable_disclosure_blob(self):
        disclosed = "path=" + "/" + "Users/alice/reviewed-before-base.txt\n"
        (self.repo / "legacy.md").write_text(disclosed)
        base = self.commit("reviewed legacy baseline")
        # Git deduplicates this content: the new path points to the exact blob
        # already reachable from the base and therefore is absent from the
        # range's object set. A content-only object audit would miss it.
        (self.repo / "copied.md").write_text(disclosed)
        tip = self.commit("copy legacy disclosure into new history")
        result = self.run_checker("--range", f"{base}..{tip}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mac-home", result.stdout)
        self.assertNotIn("alice", result.stdout)

    def test_staged_gate_reports_categories_without_content(self):
        path = self.repo / "new.md"
        path.write_text("location=" + "/" + "private/tmp/private-copy/report.txt\n")
        git(self.repo, "add", "new.md")
        result = self.run_checker("--staged")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mac-temp", result.stdout)
        self.assertNotIn("private-copy", result.stdout)

    def test_detects_windows_volume_and_run_user_paths(self):
        (self.repo / "paths.md").write_text("clean baseline\n")
        base = self.commit("initial clean paths")
        home = "C:" + chr(92) + "Users" + chr(92) + "alice" + chr(92) + "private.txt"
        volume = "/" + "Volumes/Backup/private.txt"
        run_user = "/" + "run/user/501/private.txt"
        (self.repo / "paths.md").write_text(f"{home}\n{volume}\n{run_user}\n")
        self.commit("add local path sample")
        (self.repo / "paths.md").write_text("docs/relative.md\n")
        tip = self.commit("remove local path examples")
        result = self.run_checker("--range", f"{base}..{tip}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("windows-home", result.stdout)
        self.assertIn("volume-path", result.stdout)
        self.assertIn("run-user-path", result.stdout)
        self.assertNotIn("alice", result.stdout)

    def test_staged_gate_flags_unexpected_workspace_state_file(self):
        workspace = self.repo / "workspace"
        workspace.mkdir()
        (workspace / "arena-session.json").write_text('{"example": true}\n')
        git(self.repo, "add", "workspace/arena-session.json")
        result = self.run_checker("--staged")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workspace-state-review", result.stdout)


if __name__ == "__main__":
    unittest.main()
