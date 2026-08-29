"""Test capability-first routing and explicit fallback behavior."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from route_artifact import choose_route


class RoutingTest(unittest.TestCase):
    """Ensure the user's target and structured source remain visible in every route."""

    def test_structured_presentation_route(self) -> None:
        result = choose_route(
            {
                "inputFormat": "svg",
                "targetFormat": "pptx",
                "editable": True,
                "structuredSource": True,
                "availableCapabilities": ["structured-svg-to-presentation", "native-powerpoint-acceptance"],
                "nativeAcceptance": True,
            }
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["capability"], "structured-svg-to-presentation")
        self.assertTrue(result["structuredSourcePreserved"])

    def test_explicit_fallback_is_a_warning(self) -> None:
        result = choose_route(
            {
                "inputFormat": "json",
                "targetFormat": "pptx",
                "editable": True,
                "availableCapabilities": ["screenshot-to-editable-presentation"],
                "fallbackCapabilities": ["screenshot-to-editable-presentation"],
            }
        )
        self.assertEqual(result["status"], "PASS_WITH_WARNING")
        self.assertIn("explicit fallback", result["warnings"][0])

    def test_missing_required_native_acceptance_blocks(self) -> None:
        result = choose_route(
            {
                "inputFormat": "pptx",
                "targetFormat": "pptx",
                "nativeAcceptance": True,
                "requiredNative": True,
                "availableCapabilities": ["template-preserving-presentation-editing"],
            }
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["blockers"])

    def test_document_spreadsheet_diagram_and_latex_policies_are_explicit(self) -> None:
        requests = [
            ("docx", "document-generation", "native-word-acceptance", "Microsoft Word"),
            ("xlsx", "spreadsheet-generation", "native-excel-acceptance", "Microsoft Excel"),
            ("vsdx", "editable-diagram-generation", "native-visio-acceptance", "Microsoft Visio"),
        ]
        for target_format, capability, native_capability, application in requests:
            result = choose_route(
                {
                    "inputFormat": target_format,
                    "targetFormat": target_format,
                    "nativeAcceptance": True,
                    "requiredNative": True,
                    "availableCapabilities": [capability, native_capability],
                }
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["capability"], capability)
            self.assertEqual(result["nativeApplication"], application)
            self.assertIn(native_capability, result["route"])

        latex = choose_route(
            {
                "inputFormat": "tex",
                "targetFormat": "pdf",
                "availableCapabilities": ["latex-compilation", "pdf-render-and-inspect"],
            }
        )
        self.assertEqual(latex["status"], "PASS")
        self.assertEqual(latex["capability"], "latex-compilation")
        self.assertIn("pdf-render-and-inspect", latex["route"])


if __name__ == "__main__":
    unittest.main()
