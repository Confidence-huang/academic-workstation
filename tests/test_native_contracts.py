"""Test that the Windows runner exposes each native artifact boundary without broad cleanup."""

from __future__ import annotations

import unittest
from pathlib import Path


class NativeContractTest(unittest.TestCase):
    """Keep the native entrypoint present and safe even when Linux CI cannot execute COM."""

    def setUp(self) -> None:
        self.script = Path(__file__).resolve().parents[1] / "scripts" / "native_acceptance.ps1"
        self.source = self.script.read_text(encoding="utf-8")

    def test_word_acceptance_contract(self) -> None:
        self.assertIn("Microsoft Word", self.source)
        self.assertIn("academic-workstation-word-pilot.docx", self.source)

    def test_excel_acceptance_contract(self) -> None:
        self.assertIn("Microsoft Excel", self.source)
        self.assertIn("academic-workstation-excel-pilot.xlsx", self.source)

    def test_visio_acceptance_contract(self) -> None:
        self.assertIn("Microsoft Visio", self.source)
        self.assertIn("academic-workstation-visio-pilot.vsdx", self.source)

    def test_runner_does_not_use_broad_process_termination(self) -> None:
        self.assertNotIn("taskkill", self.source.lower())
        self.assertIn("taskTerminationUsed = $false", self.source)


if __name__ == "__main__":
    unittest.main()
