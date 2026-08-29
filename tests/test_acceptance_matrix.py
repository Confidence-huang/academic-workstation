"""Test the single matrix that combines native and derivative acceptance records."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from acceptance_matrix import GATES, build_matrix


def _gates(native: bool = True) -> dict[str, str]:
    """Create a complete synthetic gate map for a matrix fixture."""
    result = {gate: "PASS" for gate in GATES}
    if not native:
        result["nativeOpen"] = "NOT_APPLICABLE"
        result["roundtrip"] = "NOT_APPLICABLE"
    return result


class AcceptanceMatrixTest(unittest.TestCase):
    """Keep missing gates and compatibility fallbacks visible in the aggregate row."""

    def test_acceptance_matrix_covers_all_artifact_rows(self) -> None:
        records = [
            {"artifactType": "pptx", "status": "PASS_WITH_WARNING", "acceptance": {"highestLevel": "L5", "gates": _gates()}},
            {"artifactType": "docx", "status": "PASS", "acceptance": {"highestLevel": "L5", "gates": _gates()}},
            {"artifactType": "xlsx", "status": "PASS_WITH_WARNING", "fallbacks": [{}], "acceptance": {"highestLevel": "L5", "gates": _gates()}},
            {"artifactType": "vsdx", "status": "PASS", "acceptance": {"highestLevel": "L5", "gates": _gates()}},
            {"artifactType": "latex", "status": "PASS", "acceptance": {"highestLevel": "L5", "gates": _gates(False)}},
            {"artifactType": "pdf", "sourceArtifactType": "latex", "status": "PASS", "acceptance": {"highestLevel": "L5", "gates": {"visualQA": "PASS"}}},
        ]
        matrix = build_matrix(records)
        rows = {row["artifactType"]: row for row in matrix["rows"]}
        self.assertEqual(set(rows), {"pptx", "docx", "xlsx", "vsdx", "latex"})
        self.assertEqual(rows["docx"]["gates"]["nativeOpen"], "PASS")
        self.assertEqual(rows["latex"]["gates"]["nativeOpen"], "NOT_APPLICABLE")
        self.assertEqual(rows["latex"]["gates"]["visualQA"], "PASS")
        self.assertEqual(matrix["overallStatus"], "PASS_WITH_WARNING")

    def test_missing_native_gate_is_not_a_pass(self) -> None:
        matrix = build_matrix(
            [
                {
                    "artifactType": "docx",
                    "status": "PASS",
                    "acceptance": {"gates": {"generate": "PASS", "parse": "PASS"}},
                }
            ]
        )
        row = next(item for item in matrix["rows"] if item["artifactType"] == "docx")
        self.assertEqual(row["gates"]["nativeOpen"], "UNAVAILABLE")
        self.assertEqual(row["status"], "PASS_WITH_WARNING")

    def test_project_recovery_gate_can_close_l6(self) -> None:
        matrix = build_matrix(
            [
                {
                    "artifactType": "docx",
                    "status": "PASS",
                    "acceptance": {
                        "highestLevel": "L5",
                        "gates": _gates(),
                    },
                }
            ],
            {"status": "PASS", "acceptance": {"gates": {"recovery": "PASS"}}},
        )
        row = next(item for item in matrix["rows"] if item["artifactType"] == "docx")
        self.assertEqual(row["gates"]["recovery"], "PASS")
        self.assertEqual(row["highestLevel"], "L6")
        self.assertEqual(matrix["recovery"]["status"], "PASS")

    def test_companion_gates_close_stage_local_warnings(self) -> None:
        gates = _gates()
        gates["recovery"] = "NOT_RUN"
        matrix = build_matrix(
            [
                {
                    "artifactType": "docx",
                    "status": "PASS_WITH_WARNING",
                    "acceptance": {"gates": gates},
                    "warnings": [],
                    "deferred": ["Backup/restore rehearsal is a separate release gate."],
                    "fallbacks": [],
                }
            ],
            {"status": "PASS", "acceptance": {"gates": {"recovery": "PASS"}}},
        )
        row = next(item for item in matrix["rows"] if item["artifactType"] == "docx")
        self.assertEqual(row["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
