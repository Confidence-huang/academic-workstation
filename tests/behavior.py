"""Exercise the public route, status, evidence, and publication gates in one process."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    """Run a deterministic self-bootstrapping behavior check without native applications."""
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "scripts"))
    from derive_status import derive_status
    from acceptance_matrix import build_matrix
    from route_artifact import choose_route
    from scan_public_repo import scan_public_repo
    from validate_evidence import validate_evidence

    route = choose_route(
        {
            "inputFormat": "svg",
            "targetFormat": "pptx",
            "editable": True,
            "structuredSource": True,
            "nativeAcceptance": True,
            "availableCapabilities": ["structured-svg-to-presentation", "native-powerpoint-acceptance"],
        }
    )
    status = derive_status(
        {
            "checks": [{"name": "route", "status": "PASS", "required": True}],
            "warnings": [],
            "deferred": [],
            "blockers": [],
        }
    )
    evidence = validate_evidence(
        {
            "schemaVersion": "1.0",
            "origin": "SYNTHETIC_EXAMPLE",
            "status": "PASS",
            "checks": [{"name": "fixture", "status": "PASS", "required": True}],
            "artifacts": [],
            "warnings": [],
            "deferred": [],
            "blockers": [],
        },
        root,
    )
    matrix = build_matrix(
        [
            {
                "artifactType": "docx",
                "status": "PASS",
                "acceptance": {"gates": {"generate": "PASS", "parse": "PASS", "nativeOpen": "PASS", "roundtrip": "PASS"}},
            }
        ]
    )
    scan = scan_public_repo(root)
    result = {
        "schemaVersion": "1.0",
        "status": "PASS"
        if route["status"] == "PASS" and status["status"] == "PASS" and evidence["valid"] and scan["status"] == "PASS" and matrix["overallStatus"] == "PASS_WITH_WARNING"
        else "FAIL",
        "route": route["status"],
        "derived": status["status"],
        "evidenceValid": evidence["valid"],
        "publicationScan": scan["status"],
        "acceptanceMatrix": matrix["overallStatus"],
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
