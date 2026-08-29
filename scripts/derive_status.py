"""Derive a final artifact status from structured checks and explicit open work.

The input status, if present, is ignored. This prevents a producer from manually overriding a
required failure. Example: ``python scripts/derive_status.py --input evidence.json``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FINAL_STATUSES = {"PASS", "PASS_WITH_WARNING", "FAIL", "BLOCKED"}
CHECK_STATUSES = {"PASS", "FAIL", "NOT_RUN", "NOT_APPLICABLE", "BLOCKED", "UNKNOWN"}


def _items(value: Any) -> list[Any]:
    """Treat missing collections as empty while rejecting ambiguous scalar values."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("checks, warnings, deferred, and blockers must be arrays")
    return value


def derive_status(document: dict[str, Any]) -> dict[str, Any]:
    """Apply the deterministic blocker → failure → warning → pass precedence."""
    checks = _items(document.get("checks"))
    warnings = _items(document.get("warnings"))
    deferred = _items(document.get("deferred"))
    blockers = _items(document.get("blockers"))
    fallbacks = _items(document.get("fallbacks"))
    failed_required = 0
    required_not_run = 0
    not_run = 0
    reasons: list[str] = []

    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("each check must be an object")
        status = str(check.get("status", "UNKNOWN"))
        if status not in CHECK_STATUSES:
            raise ValueError(f"unsupported check status: {status}")
        if status in {"NOT_RUN", "UNKNOWN"}:
            not_run += 1
        if check.get("required", False) and status in {"FAIL", "BLOCKED", "UNKNOWN"}:
            failed_required += 1
            reasons.append(f"required check failed or is unknown: {check.get('name', 'unnamed')}")
        if check.get("required", False) and status == "NOT_RUN":
            required_not_run += 1
            reasons.append(f"required check was not run: {check.get('name', 'unnamed')}")

    if blockers:
        status = "BLOCKED"
        reasons.append(f"{len(blockers)} external blocker(s) remain")
    elif failed_required or required_not_run:
        status = "FAIL"
    elif warnings or deferred or fallbacks or not_run:
        status = "PASS_WITH_WARNING"
        if deferred:
            reasons.append(f"{len(deferred)} deferred item(s) remain; DEFERRED is not PASS")
        if fallbacks:
            reasons.append(f"{len(fallbacks)} compatibility fallback(s) were used")
        if not_run:
            reasons.append(f"{not_run} check(s) were not run")
    else:
        status = "PASS"

    if status not in FINAL_STATUSES:
        raise ValueError("internal status derivation error")
    return {
        "status": status,
        "warningCount": len(warnings) + len(deferred) + len(fallbacks),
        "deferredCount": len(deferred),
        "blockerCount": len(blockers),
        "fallbackCount": len(fallbacks),
        "failedRequiredCheckCount": failed_required,
        "requiredNotRunCount": required_not_run,
        "notRunCount": not_run,
        "reasons": reasons,
    }


def main() -> int:
    """Derive and print one status record from a JSON document."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="checks/evidence JSON")
    arguments = parser.parse_args()
    print(json.dumps(derive_status(json.loads(arguments.input.read_text(encoding="utf-8"))), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
