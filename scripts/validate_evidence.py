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
from path_tools import is_relative_safe, normalize_path


ORIGINS = {"CURRENT_RUN", "HISTORICAL_SOURCE", "SYNTHETIC_EXAMPLE", "USER_SUPPLIED"}
SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
ACCEPTANCE_GATE_STATUSES = {
    "PASS",
    "PASS_WITH_WARNING",
    "FAIL",
    "BLOCKED",
    "NOT_RUN",
    "NOT_APPLICABLE",
    "DEFERRED",
    "UNAVAILABLE",
    "SUPPORTED",
    "TESTED",
}


def _hash_file(path: Path) -> str:
    """Hash an evidence artifact in bounded chunks for reproducible verification."""
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_optional_paths(document: dict[str, Any], errors: list[str]) -> None:
    """Reject absolute evidence pointers before a report can leak or escape its root."""
    for field in ("sourcePath", "roundtripPath", "exportPath"):
        if field not in document or document[field] is None:
            continue
        if not isinstance(document[field], str) or not is_relative_safe(document[field]):
            errors.append(f"{field} must be a safe relative path")


def _validate_fallbacks(document: dict[str, Any], errors: list[str]) -> None:
    """Require enough fallback detail to reproduce the downstream acceptance decision."""
    fallbacks = document.get("fallbacks", [])
    if not isinstance(fallbacks, list):
        errors.append("fallbacks must be an array")
        return
    required_fields = {"step", "primary", "error", "fallback", "fallbackResult"}
    allowed_results = {"PASS", "PASS_WITH_WARNING", "FAIL", "NOT_RUN"}
    for index, fallback in enumerate(fallbacks):
        if not isinstance(fallback, dict):
            errors.append(f"fallback {index} must be an object")
            continue
        missing = sorted(required_fields - set(fallback))
        if missing:
            errors.append(f"fallback {index} is missing: {', '.join(missing)}")
        if fallback.get("fallbackResult") not in allowed_results:
            errors.append(f"fallback {index} has an unsupported result")


def _validate_visual_review(document: dict[str, Any], errors: list[str]) -> None:
    """Validate page-by-page visual observations without pretending to infer them from pixels."""
    reviews = document.get("visualReview", [])
    if not isinstance(reviews, list):
        errors.append("visualReview must be an array")
        return
    required_fields = {"page", "blank", "clipping", "overlap", "overflow", "notes"}
    for index, review in enumerate(reviews):
        if not isinstance(review, dict):
            errors.append(f"visual review {index} must be an object")
            continue
        missing = sorted(required_fields - set(review))
        if missing:
            errors.append(f"visual review {index} is missing: {', '.join(missing)}")
        if not isinstance(review.get("page"), int) or review.get("page", 0) < 1:
            errors.append(f"visual review {index} page must be a positive integer")
        if not all(isinstance(review.get(field), bool) for field in ("blank", "clipping", "overlap", "overflow")):
            errors.append(f"visual review {index} geometry flags must be boolean")
        if not isinstance(review.get("notes"), list) or not all(isinstance(note, str) for note in review.get("notes", [])):
            errors.append(f"visual review {index} notes must be an array of strings")


def validate_evidence(document: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Return validation errors without mutating the evidence or its artifact root."""
    errors: list[str] = []
    origin = document.get("origin")
    if origin not in ORIGINS:
        errors.append(f"origin must be one of {sorted(ORIGINS)}")

    declared_status = document.get("status")
    if declared_status not in FINAL_STATUSES:
        errors.append("status must be PASS, PASS_WITH_WARNING, FAIL, or BLOCKED")

    _validate_optional_paths(document, errors)
    _validate_fallbacks(document, errors)
    _validate_visual_review(document, errors)

    acceptance = document.get("acceptance")
    if acceptance is not None:
        if not isinstance(acceptance, dict):
            errors.append("acceptance must be an object")
        else:
            gates = acceptance.get("gates", {})
            if not isinstance(gates, dict):
                errors.append("acceptance.gates must be an object")
            else:
                for gate_name, gate_status in gates.items():
                    if gate_status not in ACCEPTANCE_GATE_STATUSES:
                        errors.append(f"acceptance gate {gate_name} has an unsupported status")

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
    seen_artifact_paths: set[str] = set()
    for index, artifact in enumerate(artifact_items):
        if not isinstance(artifact, dict):
            errors.append(f"artifact {index} must be an object")
            continue
        path = artifact.get("path")
        digest = artifact.get("sha256")
        if not isinstance(path, str) or not is_relative_safe(path):
            errors.append(f"artifact {index} path must be relative and safe")
            continue
        if path in seen_artifact_paths:
            errors.append(f"artifact path is duplicated: {path}")
        seen_artifact_paths.add(path)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"artifact {index} must contain a 64-character SHA-256")
            continue
        if root is not None:
            candidate = root / Path(normalize_path(path))
            if candidate.is_symlink() or not candidate.is_file():
                errors.append(f"artifact is missing or is a link: {path}")
            elif _hash_file(candidate) != digest.lower():
                errors.append(f"artifact hash mismatch: {path}")
            if candidate.is_file() and not candidate.is_symlink() and "bytes" in artifact and artifact["bytes"] != candidate.stat().st_size:
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
