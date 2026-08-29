"""Test the deterministic final-status precedence rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from derive_status import derive_status


class StatusTest(unittest.TestCase):
    """A required failure or blocker must never be downgraded by a producer claim."""

    def test_required_failure_cannot_pass(self) -> None:
        result = derive_status(
            {
                "status": "PASS",
                "checks": [{"name": "native", "status": "FAIL", "required": True}],
                "warnings": [],
                "deferred": [],
                "blockers": [],
            }
        )
        self.assertEqual(result["status"], "FAIL")

    def test_deferred_is_not_pass(self) -> None:
        result = derive_status(
            {
                "checks": [{"name": "visual", "status": "NOT_APPLICABLE", "required": False}],
                "warnings": [],
                "deferred": ["optional Word pilot"],
                "blockers": [],
            }
        )
        self.assertEqual(result["status"], "PASS_WITH_WARNING")

    def test_blocker_has_precedence(self) -> None:
        result = derive_status(
            {
                "checks": [{"name": "route", "status": "FAIL", "required": True}],
                "warnings": [],
                "deferred": [],
                "blockers": ["interactive login required"],
            }
        )
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
