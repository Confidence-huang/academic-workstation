"""Test relative manifest creation and backup/restore comparison."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from compare_manifests import compare_manifests
from hash_artifacts import build_manifest


class HashTest(unittest.TestCase):
    """A byte change or missing file must be visible in the restore comparison."""

    def test_equal_manifests_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "one.txt").write_text("one", encoding="utf-8")
            expected = build_manifest(root)
            actual = build_manifest(root)
            self.assertEqual(compare_manifests(expected, actual)["status"], "PASS")

    def test_changed_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            file_path = root / "one.txt"
            file_path.write_text("one", encoding="utf-8")
            expected = build_manifest(root)
            file_path.write_text("two", encoding="utf-8")
            actual = build_manifest(root)
            result = compare_manifests(expected, actual)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["hashMismatch"][0]["path"], "one.txt")


if __name__ == "__main__":
    unittest.main()
