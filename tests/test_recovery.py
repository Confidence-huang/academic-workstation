"""Test the conservative project backup and restore rehearsal."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from recovery_rehearsal import rehearse_recovery


class RecoveryRehearsalTest(unittest.TestCase):
    """A clean tracked fixture must survive copy, restore, and hash comparison."""

    def test_clean_checkout_restores_to_an_empty_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            source = workspace / "source"
            source.mkdir()
            (source / "result.txt").write_text("SYNTHETIC TEST DATA\n", encoding="utf-8")
            subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
            subprocess.run(["git", "add", "result.txt"], cwd=source, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Academic Workstation Test",
                    "-c",
                    "user.email=academic-workstation@example.invalid",
                    "commit",
                    "--quiet",
                    "-m",
                    "fixture",
                ],
                cwd=source,
                check=True,
            )

            result = rehearse_recovery(source, workspace / "backup", workspace / "restore")

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["fileCount"], 1)
            self.assertEqual(result["backupComparison"]["status"], "PASS")
            self.assertEqual(result["restoreComparison"]["status"], "PASS")
            self.assertEqual((workspace / "restore" / "result.txt").read_text(encoding="utf-8"), "SYNTHETIC TEST DATA\n")


if __name__ == "__main__":
    unittest.main()
