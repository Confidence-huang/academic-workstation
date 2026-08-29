"""Test PDF QA classification without requiring Poppler in the Linux unit-test host."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pdf_qa import _visual_check


class PdfQualityTest(unittest.TestCase):
    """Ensure diagnostic classes and explicit page observations stay conservative."""

    def test_visual_review_requires_every_page(self) -> None:
        check, records, warnings = _visual_check(
            [{"page": 1, "blank": False, "clipping": False, "overlap": False, "overflow": False, "notes": ["text is small"]}],
            1,
        )
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(len(records), 1)
        self.assertEqual(warnings, ["page 1: text is small"])

    def test_visual_review_without_input_is_not_run(self) -> None:
        check, records, _ = _visual_check(None, 1)
        self.assertEqual(check["status"], "NOT_RUN")
        self.assertTrue(check["required"])
        self.assertEqual(records, [])


if __name__ == "__main__":
    unittest.main()
