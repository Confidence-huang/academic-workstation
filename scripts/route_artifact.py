"""Choose an artifact route from capabilities before integration names.

The command reads a small JSON request and prints a deterministic decision. It never starts a
specialist tool, edits an artifact, or contacts an external service. Example:
``python scripts/route_artifact.py --request request.json``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TARGET_CAPABILITIES = {
    "pptx": "editable-presentation-generation",
    "docx": "document-generation",
    "xlsx": "spreadsheet-generation",
    "vsdx": "editable-diagram-generation",
    "pdf": "pdf-understanding",
}
NATIVE_CAPABILITIES = {
    "pptx": "native-powerpoint-acceptance",
    "docx": "native-word-acceptance",
    "xlsx": "native-excel-acceptance",
    "vsdx": "native-visio-acceptance",
}
STRUCTURED_INPUTS = {"svg", "xml", "pptx", "xlsx", "csv", "json", "ooxml"}
IMAGE_INPUTS = {"png", "jpg", "jpeg", "image", "screenshot", "scan", "flattened-pdf"}


def _format_name(value: Any) -> str:
    """Normalize a user-facing format while rejecting empty or non-string values."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("format must be a non-empty string")
    return value.strip().lower().lstrip(".")


def _choose_capability(input_format: str, target_format: str, editable: bool) -> str:
    """Select the capability from the input shape and requested output."""
    if target_format == "pptx":
        if input_format in STRUCTURED_INPUTS:
            return "structured-svg-to-presentation" if input_format == "svg" else "editable-presentation-generation"
        if input_format in IMAGE_INPUTS and editable:
            return "screenshot-to-editable-presentation"
        if input_format == "pptx":
            return "template-preserving-presentation-editing"
        return "editable-presentation-generation"
    if input_format == "tex" and target_format == "pdf":
        return "latex-compilation"
    return TARGET_CAPABILITIES.get(target_format, "artifact-validation")


def choose_route(request: dict[str, Any]) -> dict[str, Any]:
    """Return a capability-first route while preserving the user's target and tool choice."""
    input_format = _format_name(request.get("inputFormat"))
    target_format = _format_name(request.get("targetFormat"))
    editable = bool(request.get("editable", False))
    structured_source = bool(request.get("structuredSource", input_format in STRUCTURED_INPUTS))
    native_required = bool(request.get("nativeAcceptance", False))
    available = {str(item).strip() for item in request.get("availableCapabilities", []) if str(item).strip()}
    optional = {str(item).strip() for item in request.get("optionalCapabilities", []) if str(item).strip()}
    capability = _choose_capability(input_format, target_format, editable)
    route = [capability]
    warnings: list[str] = []
    blockers: list[str] = []

    if target_format == "pptx":
        route.append("native-powerpoint-acceptance" if native_required else "pdf-render-and-inspect")
    elif target_format == "pdf":
        route.append("pdf-render-and-inspect")
    if structured_source:
        route.append("preserve-structured-source")
    if request.get("userTool"):
        route.append(f"requested-tool:{str(request['userTool']).strip()}")

    if available and capability not in available:
        fallback = next((item for item in request.get("fallbackCapabilities", []) if item in available), None)
        if fallback and request.get("allowFallback", True):
            route[0] = str(fallback)
            warnings.append(f"primary capability unavailable; selected explicit fallback {fallback}")
        else:
            blockers.append(f"required capability unavailable: {capability}")

    missing_optional = sorted(optional - available) if available else []
    for item in missing_optional:
        warnings.append(f"optional integration unavailable: {item}")
    native_capability = NATIVE_CAPABILITIES.get(target_format)
    if native_required and native_capability and available and native_capability not in available:
        if request.get("requiredNative", False):
            blockers.append(f"required native acceptance unavailable: {native_capability}")
        else:
            warnings.append(f"native acceptance unavailable: {native_capability}")

    status = "BLOCKED" if blockers else "PASS_WITH_WARNING" if warnings else "PASS"
    return {
        "schemaVersion": "1.0",
        "status": status,
        "inputFormat": input_format,
        "targetFormat": target_format,
        "editable": editable,
        "capability": capability,
        "route": route,
        "userTargetPreserved": True,
        "structuredSourcePreserved": structured_source,
        "lossyConversion": "forbidden" if structured_source else "allowed-only-when-requested",
        "missingOptional": missing_optional,
        "warnings": warnings,
        "blockers": blockers,
    }


def main() -> int:
    """Read one request, print one route record, and return a useful process status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True, help="JSON route request")
    arguments = parser.parse_args()
    request = json.loads(arguments.request.read_text(encoding="utf-8"))
    result = choose_route(request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
