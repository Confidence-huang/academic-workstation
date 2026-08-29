"""Test provenance, relative artifact paths, and hash verification."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_evidence import validate_evidence


class EvidenceTest(unittest.TestCase):
    """Evidence must agree with derived status and the bytes on disk."""

    def test_valid_fixture_with_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "result.txt"
            artifact.write_text("SYNTHETIC TEST DATA\n", encoding="utf-8")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            evidence = {
                "schemaVersion": "1.0",
                "origin": "CURRENT_RUN",
                "status": "PASS",
                "checks": [{"name": "artifact", "status": "PASS", "required": True}],
                "artifacts": [{"path": "result.txt", "bytes": artifact.stat().st_size, "sha256": digest}],
                "warnings": [],
                "deferred": [],
                "blockers": [],
            }
            result = validate_evidence(evidence, root)
            self.assertTrue(result["valid"], result)

    def test_absolute_path_is_rejected(self) -> None:
        result = validate_evidence(
            {
                "schemaVersion": "1.0",
                "origin": "CURRENT_RUN",
                "status": "PASS",
                "checks": [{"name": "artifact", "status": "PASS", "required": True}],
                "artifacts": [{"path": "/private/result.txt", "sha256": "0" * 64}],
                "warnings": [],
                "deferred": [],
                "blockers": [],
            }
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("path" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
