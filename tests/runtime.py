"""Run the Skill's isolated runtime smoke test and emit one machine-readable result."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    """Import every core module and check the release's minimum structural contract."""
    root = Path(__file__).resolve().parents[1]
    scripts = root / "scripts"
    sys.path.insert(0, str(scripts))
    required = [
        root / "SKILL.md",
        root / "README.md",
        root / "agents" / "openai.yaml",
        root / "skill.manifest.yaml",
        root / "schemas" / "evidence.schema.json",
        root / "schemas" / "acceptance-matrix.schema.json",
        scripts / "route_artifact.py",
        scripts / "derive_status.py",
        scripts / "validate_evidence.py",
        scripts / "acceptance_matrix.py",
        scripts / "pdf_qa.py",
        scripts / "compile_latex.py",
        scripts / "recovery_rehearsal.py",
        scripts / "native_acceptance.ps1",
    ]
    missing = [path.relative_to(root).as_posix() for path in required if not path.is_file()]
    imported = []
    for module_name in [
        "path_tools",
        "route_artifact",
        "derive_status",
        "hash_artifacts",
        "compare_manifests",
        "validate_evidence",
        "acceptance_matrix",
        "pdf_qa",
        "compile_latex",
        "recovery_rehearsal",
        "detect_capabilities",
        "scan_public_repo",
    ]:
        __import__(module_name)
        imported.append(module_name)
    result = {
        "schemaVersion": "1.0",
        "status": "PASS" if not missing else "FAIL",
        "missing": missing,
        "imported": imported,
        "runtimeBehavior": "SMOKE_ONLY",
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
