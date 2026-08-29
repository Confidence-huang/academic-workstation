"""Test engine selection and warning classification for the LaTeX route."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from compile_latex import _classify_log, select_engine


class LatexRouteTest(unittest.TestCase):
    """Keep the preferred engine deterministic while preserving safe fallbacks."""

    def test_preferred_xelatex_route(self) -> None:
        selected = select_engine({"latexmk": "/tool/latexmk", "xelatex": "/tool/xelatex"})
        self.assertIsNotNone(selected)
        self.assertEqual(selected["name"], "latexmk-xelatex")
        self.assertTrue(selected["primary"])

    def test_engine_fallback_is_explicit(self) -> None:
        selected = select_engine({"pdflatex": "/tool/pdflatex"})
        self.assertIsNotNone(selected)
        self.assertEqual(selected["name"], "pdflatex")
        self.assertFalse(selected["primary"])

    def test_content_and_layout_diagnostics_are_separate(self) -> None:
        result = _classify_log("LaTeX Error: missing\nOverfull \\hbox")
        self.assertTrue(result["fatalError"])
        self.assertEqual(result["overfullBoxes"], 1)


if __name__ == "__main__":
    unittest.main()
