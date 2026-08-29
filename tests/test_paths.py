"""Test logical path normalization and cross-platform translation boundaries."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from path_tools import PathError, is_relative_safe, normalize_path, redact_path, translate_path


class PathRulesTest(unittest.TestCase):
    """Keep personal roots redacted and traversal rejected."""

    def test_windows_and_wsl_translation(self) -> None:
        self.assertEqual(translate_path("C:/work/paper.pdf", "posix"), "/mnt/c/work/paper.pdf")
        self.assertEqual(
            translate_path("/" + "/" + "wsl.localhost/Ubuntu-24.04/home/<USER>/paper.pdf", "windows"),
            "\\\\wsl.localhost\\Ubuntu-24.04\\home\\<USER>\\paper.pdf",
        )

    def test_redaction_and_safe_relative_path(self) -> None:
        self.assertEqual(redact_path("C:/Users/<USER>/Documents/paper.pdf"), "C:/Users/<USER>/Documents/paper.pdf")
        self.assertTrue(is_relative_safe("reports/final.json"))
        self.assertFalse(is_relative_safe("../outside.json"))
        self.assertFalse(is_relative_safe("C:outside.json"))
        with self.assertRaises(PathError):
            normalize_path("../../outside.json")


if __name__ == "__main__":
    unittest.main()
