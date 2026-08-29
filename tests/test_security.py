"""Test that publication scanning catches secrets and concrete personal roots."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scan_public_repo import scan_public_repo


class SecurityTest(unittest.TestCase):
    """The scanner must report findings without echoing their sensitive source text."""

    def test_secret_and_private_path_are_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            secret = "gh" + "p_" + ("x" * 40)
            private_path = "C:" + "/Users/" + "private-user" + "/Documents/report.docx"
            (root / "unsafe.txt").write_text(f"token={secret}\n{private_path}\n", encoding="utf-8")
            result = scan_public_repo(root)
            rules = {finding["rule"] for finding in result["findings"]}
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("secret", rules)
            self.assertIn("private-path", rules)
            self.assertNotIn(secret, json_text(result))


def json_text(value: object) -> str:
    """Serialize scanner output for the assertion that sensitive lines stay withheld."""
    import json

    return json.dumps(value)


if __name__ == "__main__":
    unittest.main()
