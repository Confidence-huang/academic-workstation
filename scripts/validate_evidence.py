"""Validate evidence status, provenance, safe paths, and optional artifact hashes.

This validator treats evidence as a claim with inputs, checks, and artifacts. A claimed
PASS is accepted only when deterministic status derivation also produces PASS, so an
author cannot hide a required failure or an unrun gate inside a hand-written status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from derive_status import CHECK_STATUSES, FINAL_STATUSES, derive_status
from path_tools import is_relative_safe


ORIGINS = {"CURRENT_RUN", "HISTORICAL_SOURCE", "SYNTHETIC_EXAMPLE", "USER_SUPPLIED"}
SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def _hash_file(path: Path) -> str:
    """Hash an evidence artifact in bounded chunks for reproducible verification."""
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_evidence(document: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Return validation errors without mutating the evidence or its artifact root."""
    errors: list[str] = []
    origin = document.get("origin")
    if origin not in ORIGINS:
        errors.append(f"origin must be one of {sorted(ORIGINS)}")

    declared_status = document.get("status")
    if declared_status not in FINAL_STATUSES:
        errors.append("status must be PASS, PASS_WITH_WARNING, FAIL, or BLOCKED")

    checks = document.get("checks", [])
    if not isinstance(checks, list):
        errors.append("checks must be an array")
    else:
        for index, check in enumerate(checks):
            if not isinstance(check, dict):
                errors.append(f"check {index} must be an object")
                continue
            if check.get("status", "UNKNOWN") not in CHECK_STATUSES:
                errors.append(f"check {index} has an unsupported status")
            if not isinstance(check.get("required", False), bool):
                errors.append(f"check {index} required must be boolean")

    artifact_items = document.get("artifacts", [])
    if not isinstance(artifact_items, list):
        errors.append("artifacts must be an array")
        artifact_items = []
    for index, artifact in enumerate(artifact_items):
        if not isinstance(artifact, dict):
            errors.append(f"artifact {index} must be an object")
            continue
        path = artifact.get("path")
        digest = artifact.get("sha256")
        if not isinstance(path, str) or not is_relative_safe(path):
            errors.append(f"artifact {index} path must be relative and safe")
            continue
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"artifact {index} must contain a 64-character SHA-256")
            continue
        if root is not None:
            candidate = root / Path(path)
            if candidate.is_symlink() or not candidate.is_file():
                errors.append(f"artifact is missing or is a link: {path}")
            elif _hash_file(candidate) != digest.lower():
                errors.append(f"artifact hash mismatch: {path}")
            if "bytes" in artifact and artifact["bytes"] != candidate.stat().st_size:
                errors.append(f"artifact byte count mismatch: {path}")

    try:
        derived = derive_status(document)
    except (TypeError, ValueError) as error:
        errors.append(f"status derivation failed: {error}")
        derived = {"status": "FAIL", "reasons": []}
    if declared_status in FINAL_STATUSES and derived["status"] != declared_status:
        errors.append(f"declared status {declared_status} disagrees with derived status {derived['status']}")

    return {
        "schemaVersion": "1.0",
        "valid": not errors,
        "status": "PASS" if not errors else "FAIL",
        "derived": derived,
        "errors": errors,
    }


def main() -> int:
    """Validate a JSON evidence record and optionally verify its artifact root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="evidence JSON")
    parser.add_argument("--root", type=Path, help="root containing relative evidence artifacts")
    arguments = parser.parse_args()
    root = arguments.root.resolve() if arguments.root else None
    result = validate_evidence(json.loads(arguments.input.read_text(encoding="utf-8")), root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
