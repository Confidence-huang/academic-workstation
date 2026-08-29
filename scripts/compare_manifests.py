"""Compare two relative SHA-256 manifests without trusting absolute source paths.

The comparison is used for backup and restore rehearsal. It reports missing files,
unexpected files, hash differences, byte-size differences, and link differences while
keeping the result independent of the machine that created either manifest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from path_tools import is_relative_safe


def _entries(document: dict[str, Any], field: str) -> dict[str, dict[str, Any]]:
    """Convert manifest entries to a unique path map and reject unsafe names."""
    raw_entries = document.get(field, [])
    if not isinstance(raw_entries, list):
        raise ValueError(f"manifest field {field!r} must be an array")
    entries: dict[str, dict[str, Any]] = {}
    for entry in raw_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError(f"manifest field {field!r} contains an invalid entry")
        path = entry["path"]
        if not is_relative_safe(path):
            raise ValueError(f"manifest path must be relative: {path}")
        if path in entries:
            raise ValueError(f"manifest contains duplicate path: {path}")
        entries[path] = entry
    return entries


def _links(document: dict[str, Any]) -> set[str]:
    """Validate link names separately because a manifest stores them as strings."""
    raw_links = document.get("links", [])
    if not isinstance(raw_links, list):
        raise ValueError("manifest field 'links' must be an array")
    links: set[str] = set()
    for path in raw_links:
        if not isinstance(path, str) or not is_relative_safe(path):
            raise ValueError(f"manifest link must be relative: {path}")
        if path in links:
            raise ValueError(f"manifest contains duplicate link: {path}")
        links.add(path)
    return links


def compare_manifests(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic comparison suitable for an evidence record."""
    expected_files = _entries(expected, "files")
    actual_files = _entries(actual, "files")
    expected_links = _links(expected)
    actual_links = _links(actual)
    missing = sorted(set(expected_files) - set(actual_files))
    unexpected = sorted(set(actual_files) - set(expected_files))
    hash_mismatch: list[dict[str, str]] = []
    size_mismatch: list[dict[str, int | str]] = []

    for path in sorted(set(expected_files) & set(actual_files)):
        expected_entry = expected_files[path]
        actual_entry = actual_files[path]
        if expected_entry.get("sha256") != actual_entry.get("sha256"):
            hash_mismatch.append(
                {
                    "path": path,
                    "expected": str(expected_entry.get("sha256", "")),
                    "actual": str(actual_entry.get("sha256", "")),
                }
            )
        if expected_entry.get("bytes") != actual_entry.get("bytes"):
            size_mismatch.append(
                {
                    "path": path,
                    "expected": expected_entry.get("bytes", -1),
                    "actual": actual_entry.get("bytes", -1),
                }
            )

    missing_links = sorted(expected_links - actual_links)
    unexpected_links = sorted(actual_links - expected_links)
    status = "PASS" if not any(
        (missing, unexpected, hash_mismatch, size_mismatch, missing_links, unexpected_links)
    ) else "FAIL"
    return {
        "schemaVersion": 1,
        "status": status,
        "missing": missing,
        "unexpected": unexpected,
        "hashMismatch": hash_mismatch,
        "sizeMismatch": size_mismatch,
        "missingLinks": missing_links,
        "unexpectedLinks": unexpected_links,
    }


def main() -> int:
    """Compare two JSON files and return non-zero when restore equivalence fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=Path, required=True, help="expected SHA-256 manifest")
    parser.add_argument("--actual", type=Path, required=True, help="actual SHA-256 manifest")
    arguments = parser.parse_args()
    result = compare_manifests(
        json.loads(arguments.expected.read_text(encoding="utf-8")),
        json.loads(arguments.actual.read_text(encoding="utf-8")),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
