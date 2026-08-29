"""Test rich capability records with a controlled resolver instead of host assumptions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from detect_capabilities import detect_capabilities


class CapabilityTest(unittest.TestCase):
    """The detector reports paths, versions, platform, and caveats without native claims."""

    def test_capability_records_are_descriptive(self) -> None:
        def fake_which(name: str) -> str | None:
            return "/tools/" + name if name in {"python3", "git", "pdfinfo", "pdftoppm"} else None

        with patch("detect_capabilities._command_version", return_value="synthetic version"):
            result = detect_capabilities(fake_which, lambda: "Linux")
        self.assertIn("pdf-render-and-inspect", result["availableCapabilities"])
        self.assertEqual(result["commands"]["python3"]["version"], "synthetic version")
        self.assertEqual(result["commands"]["git"]["platform"], "Linux")
        self.assertEqual(result["nativeAcceptance"], "NOT_RUN")

    def test_windows_executable_suffix_is_detected(self) -> None:
        def fake_which(name: str) -> str | None:
            if name in {"pdfinfo.exe", "pdftoppm.exe"}:
                return "/tools/" + name
            return None

        result = detect_capabilities(fake_which, lambda: "Linux")
        self.assertIn("pdf-render-and-inspect", result["availableCapabilities"])


if __name__ == "__main__":
    unittest.main()
