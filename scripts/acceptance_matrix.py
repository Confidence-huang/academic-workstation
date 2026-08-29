"""Merge artifact evidence into one capability and acceptance matrix.

The matrix is the public summary layer: it does not invent native results, it only combines
explicit gate records from evidence files. A missing artifact record remains UNAVAILABLE, and a
missing gate remains visible instead of being silently treated as a pass. Example:
``python scripts/acceptance_matrix.py --evidence-dir private-evidence --output matrix.json``.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MATRIX_STATUSES = {
    "SUPPORTED",
    "TESTED",
    "PASS",
    "PASS_WITH_WARNING",
    "DEFERRED",
    "NOT_RUN",
    "UNAVAILABLE",
    "NOT_APPLICABLE",
    "FAIL",
    "BLOCKED",
}
GATES = (
    "generate",
    "parse",
    "nativeOpen",
    "roundtrip",
    "export",
    "structuralQA",
    "visualQA",
    "evidence",
    "recovery",
)
ARTIFACT_DEFINITIONS = {
    "pptx": {
        "label": "PPTX",
        "nativeApplication": "Microsoft PowerPoint",
        "notApplicable": set(),
    },
    "docx": {
        "label": "DOCX",
        "nativeApplication": "Microsoft Word",
        "notApplicable": set(),
    },
    "xlsx": {
        "label": "XLSX",
        "nativeApplication": "Microsoft Excel",
        "notApplicable": set(),
    },
    "vsdx": {
        "label": "VSDX",
        "nativeApplication": "Microsoft Visio",
        "notApplicable": set(),
    },
    "latex": {
        "label": "LaTeX/PDF",
        "nativeApplication": "TeX engine plus configured PDF tools",
        "notApplicable": {"nativeOpen", "roundtrip"},
    },
}
# PDF is the derivative surface of the LaTeX/PDF row unless a caller supplies another source type.
FORMAT_ALIASES = {"tex": "latex", "latex": "latex", "pdf": "latex"}
GATE_ALIASES = {
    "nativeopen": "nativeOpen",
    "nativeOpen": "nativeOpen",
    "nativeroundtrip": "roundtrip",
    "nativeRoundtrip": "roundtrip",
    "nativeexport": "export",
    "nativeExport": "export",
    "structuralqa": "structuralQA",
    "structuralQA": "structuralQA",
    "visualqa": "visualQA",
    "visualQA": "visualQA",
}


def canonical_artifact_type(value: Any) -> str | None:
    """Map file extensions and evidence aliases to the matrix's stable row names."""
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().lower().lstrip(".")
    return FORMAT_ALIASES.get(normalized, normalized) if normalized in ARTIFACT_DEFINITIONS or normalized in FORMAT_ALIASES else None


def _record_artifact_type(record: dict[str, Any]) -> str | None:
    """Find the explicit artifact identity before falling back to a route target."""
    # A PDF record produced from LaTeX contributes to the LaTeX/PDF source row; standalone PDFs keep the PDF row.
    for field in ("sourceArtifactType", "artifactType"):
        artifact_type = canonical_artifact_type(record.get(field))
        if artifact_type:
            return artifact_type
    route = record.get("route")
    if isinstance(route, dict):
        return canonical_artifact_type(route.get("targetFormat"))
    return None


def _status(value: Any, default: str = "UNAVAILABLE") -> str:
    """Keep unknown producer values visible as unavailable matrix evidence."""
    candidate = str(value) if value is not None else default
    return candidate if candidate in MATRIX_STATUSES else default


def _legacy_gate_status(record: dict[str, Any], gate: str) -> str | None:
    """Read v0.1-style acceptance fields while preferring the new explicit gate map."""
    acceptance = record.get("acceptance")
    if not isinstance(acceptance, dict):
        return None
    gates = acceptance.get("gates")
    if isinstance(gates, dict):
        for name, value in gates.items():
            if GATE_ALIASES.get(name, name) == gate:
                return _status(value)
    legacy_fields = {
        "nativeOpen": "nativeOpen",
        "nativeRoundtrip": "roundtrip",
        "nativeExport": "export",
        "visualReview": "visualQA",
        "structuralQA": "structuralQA",
    }
    for field, legacy_gate in legacy_fields.items():
        if legacy_gate == gate and field in acceptance:
            value = acceptance[field]
            return _status(value) if isinstance(value, str) else None
    return None


def _check_gate_status(record: dict[str, Any], gate: str) -> str | None:
    """Match a named check only when its wording clearly identifies the matrix gate."""
    checks = record.get("checks")
    if not isinstance(checks, list):
        return None
    for check in checks:
        if not isinstance(check, dict):
            continue
        name = str(check.get("name", "")).lower()
        aliases = {
            "generate": ("generate", "build", "create"),
            "parse": ("parse", "load", "inspect"),
            "nativeOpen": ("native open", "word open", "excel open", "visio open"),
            "roundtrip": ("round-trip", "roundtrip", "reopen", "save and reopen"),
            "export": ("export", "pdf fallback"),
            "structuralQA": ("structural", "formula", "shape", "page count"),
            "visualQA": ("visual", "render"),
            "evidence": ("evidence", "hash", "manifest"),
            "recovery": ("recovery", "restore", "backup"),
        }
        if any(alias in name for alias in aliases.get(gate, ())):
            return _status(check.get("status"))
    return None


def _gate_status(record: dict[str, Any], gate: str, not_applicable: set[str]) -> str:
    """Resolve one gate from explicit evidence, legacy fields, or a visible absence."""
    if gate in not_applicable:
        return "NOT_APPLICABLE"
    acceptance_status = _legacy_gate_status(record, gate)
    if acceptance_status:
        return acceptance_status
    check_status = _check_gate_status(record, gate)
    if check_status:
        return check_status
    return "UNAVAILABLE"


def _merge_gate_status(statuses: Iterable[str]) -> str:
    """Choose the strictest observed state so one missing or failed gate cannot disappear."""
    values = list(statuses)
    if not values:
        return "UNAVAILABLE"
    # Companion evidence can complete a gate left unrun by an earlier stage (for example,
    # compile evidence leaves visualQA NOT_RUN while pdf_qa supplies the visual PASS).
    if "BLOCKED" in values:
        return "BLOCKED"
    if "FAIL" in values:
        return "FAIL"
    if "PASS_WITH_WARNING" in values:
        return "PASS_WITH_WARNING"
    if "PASS" in values:
        return "PASS"
    for candidate in ("NOT_RUN", "DEFERRED", "UNAVAILABLE"):
        if candidate in values:
            return candidate
    if all(value == "NOT_APPLICABLE" for value in values):
        return "NOT_APPLICABLE"
    return "PASS"


def _merge_overall_status(records: Iterable[dict[str, Any]], gates: Iterable[str]) -> str:
    """Derive a row status from declared evidence and the merged gate states."""
    declared = [_status(record.get("status")) for record in records]
    gate_values = list(gates)
    if "BLOCKED" in declared or "BLOCKED" in gate_values:
        return "BLOCKED"
    if "FAIL" in declared or "FAIL" in gate_values:
        return "FAIL"
    if any(value in {"PASS_WITH_WARNING", "DEFERRED", "NOT_RUN", "UNAVAILABLE"} for value in declared + gate_values):
        return "PASS_WITH_WARNING"
    return "PASS" if declared or gate_values else "UNAVAILABLE"


def _highest_level(records: Iterable[dict[str, Any]], gates: dict[str, str]) -> str:
    """Report the highest explicit level without inferring native success from a file alone."""
    explicit_levels: list[int] = []
    for record in records:
        acceptance = record.get("acceptance")
        if isinstance(acceptance, dict):
            value = acceptance.get("highestLevel")
            if isinstance(value, str) and len(value) == 2 and value[0] == "L" and value[1].isdigit():
                explicit_levels.append(int(value[1]))
    if gates.get("recovery") == "PASS" and gates.get("evidence") == "PASS":
        return "L6"
    if explicit_levels:
        return f"L{max(explicit_levels)}"
    if gates.get("visualQA") == "PASS":
        return "L5"
    if gates.get("export") == "PASS":
        return "L4"
    if gates.get("roundtrip") == "PASS":
        return "L3"
    if gates.get("nativeOpen") == "PASS":
        return "L2"
    if gates.get("parse") == "PASS":
        return "L1"
    return "L0" if gates.get("generate") == "PASS" else "UNAVAILABLE"


def build_matrix(
    evidence_records: Iterable[dict[str, Any]], recovery_record: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the five-row matrix while preserving source records and a project recovery gate."""
    records_by_type: dict[str, list[dict[str, Any]]] = {key: [] for key in ARTIFACT_DEFINITIONS}
    ignored_records = 0
    for record in evidence_records:
        if not isinstance(record, dict):
            ignored_records += 1
            continue
        artifact_type = _record_artifact_type(record)
        if artifact_type not in records_by_type:
            ignored_records += 1
            continue
        records_by_type[artifact_type].append(record)

    rows: list[dict[str, Any]] = []
    recovery_status = None
    if isinstance(recovery_record, dict):
        recovery_status = _status(recovery_record.get("status"), "UNAVAILABLE")
        acceptance = recovery_record.get("acceptance")
        if isinstance(acceptance, dict) and isinstance(acceptance.get("gates"), dict):
            recovery_status = _status(acceptance["gates"].get("recovery"), recovery_status)
    for artifact_type, definition in ARTIFACT_DEFINITIONS.items():
        records = records_by_type[artifact_type]
        gate_statuses = {
            gate: _merge_gate_status(_gate_status(record, gate, definition["notApplicable"]) for record in records)
            for gate in GATES
        }
        if recovery_status is not None:
            gate_statuses["recovery"] = _merge_gate_status((gate_statuses["recovery"], recovery_status))
        row_status = _merge_overall_status(records, gate_statuses.values()) if records else "UNAVAILABLE"
        rows.append(
            {
                "artifact": definition["label"],
                "artifactType": artifact_type,
                "supportStatus": "SUPPORTED",
                "testStatus": "TESTED" if records else "UNAVAILABLE",
                "nativeApplication": definition["nativeApplication"],
                "highestLevel": _highest_level(records, gate_statuses),
                "status": row_status,
                "gates": gate_statuses,
                "evidenceRecords": len(records),
            }
        )

    row_statuses = [row["status"] for row in rows]
    overall_status = _merge_overall_status(rows, row_statuses)
    result = {
        "schemaVersion": "1.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "overallStatus": overall_status,
        "gates": list(GATES),
        "rows": rows,
        "coverage": {
            "supported": len(rows),
            "tested": sum(row["testStatus"] == "TESTED" for row in rows),
            "unavailable": sum(row["status"] == "UNAVAILABLE" for row in rows),
            "ignoredEvidenceRecords": ignored_records,
        },
    }
    if isinstance(recovery_record, dict):
        result["recovery"] = recovery_record
    return result


def load_evidence(directory: Path) -> list[dict[str, Any]]:
    """Load JSON evidence candidates and skip unrelated machine-state records."""
    records: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and _record_artifact_type(value):
            records.append(value)
    return records


def load_recovery(path: Path) -> dict[str, Any]:
    """Load one project-level backup/restore gate without confusing it with an artifact row."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("recovery evidence must be an object")
    return value


def main() -> int:
    """Read private evidence files, print one matrix, and fail only on matrix failure/blocking."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True, help="directory containing JSON evidence")
    parser.add_argument("--output", type=Path, help="optional matrix JSON output")
    parser.add_argument("--recovery-evidence", type=Path, help="optional project backup/restore gate JSON")
    arguments = parser.parse_args()
    recovery = load_recovery(arguments.recovery_evidence) if arguments.recovery_evidence else None
    matrix = build_matrix(load_evidence(arguments.evidence_dir), recovery)
    serialized = json.dumps(matrix, ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 2 if matrix["overallStatus"] in {"FAIL", "BLOCKED"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
