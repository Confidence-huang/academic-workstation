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
    "tex": "latex-compilation",
    "pdf": "pdf-understanding",
}
NATIVE_CAPABILITIES = {
    "pptx": "native-powerpoint-acceptance",
    "docx": "native-word-acceptance",
    "xlsx": "native-excel-acceptance",
    "vsdx": "native-visio-acceptance",
    "pdf": "native-pdf-reader-acceptance",
}
FORMAT_ALIASES = {"latex": "tex"}
STRUCTURED_INPUTS = {"svg", "xml", "pptx", "xlsx", "csv", "json", "ooxml"}
IMAGE_INPUTS = {"png", "jpg", "jpeg", "image", "screenshot", "scan", "flattened-pdf"}
ROUTE_POLICIES = {
    "pptx": {
        "preferredGenerator": "presentation specialist",
        "nativeApplication": "Microsoft PowerPoint",
        "acceptanceTarget": "native PowerPoint round-trip, export, and rendered-page QA",
        "fallbackPolicy": "Keep editable structure; record and re-run downstream PDF QA after export fallback.",
    },
    "docx": {
        "preferredGenerator": "document specialist",
        "nativeApplication": "Microsoft Word",
        "acceptanceTarget": "native Word open/save/reopen, PDF export, and rendered-page QA",
        "fallbackPolicy": "Stage on a local Windows path when UNC save fails; never substitute a non-native renderer.",
    },
    "xlsx": {
        "preferredGenerator": "spreadsheet specialist",
        "nativeApplication": "Microsoft Excel",
        "acceptanceTarget": "native Excel formula/chart round-trip, PDF export, and rendered-page QA",
        "fallbackPolicy": "Preserve formulas and editable chart objects; an image is not an Excel-chart fallback.",
    },
    "vsdx": {
        "preferredGenerator": "editable diagram specialist",
        "nativeApplication": "Microsoft Visio",
        "acceptanceTarget": "native Visio shape/connector round-trip, export, and rendered-page QA",
        "fallbackPolicy": "Keep native editable shapes and connectors; never replace the diagram with a screenshot.",
    },
    "tex": {
        "preferredGenerator": "LaTeX toolchain",
        "nativeApplication": "TeX engine plus PDF QA tools",
        "acceptanceTarget": "controlled compile, bibliography/reference checks, PDF render, and visual QA",
        "fallbackPolicy": "Select an installed engine explicitly and record the engine fallback and log classification.",
    },
    "pdf": {
        "preferredGenerator": "requested source generator",
        "nativeApplication": "configured PDF reader",
        "acceptanceTarget": "PDF structural inspection, target-reader check when requested, and rendered-page QA",
        "fallbackPolicy": "A different reader may diagnose only; it cannot be reported as the requested native reader.",
    },
}


def _format_name(value: Any) -> str:
    """Normalize a user-facing format while rejecting empty or non-string values."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("format must be a non-empty string")
    return value.strip().lower().lstrip(".")


def _canonical_format(value: Any) -> str:
    """Normalize extension aliases so LaTeX and TeX share one matrix row."""
    return FORMAT_ALIASES.get(_format_name(value), _format_name(value))


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
    if input_format == "tex" and target_format in {"tex", "pdf"}:
        return "latex-compilation"
    return TARGET_CAPABILITIES.get(target_format, "artifact-validation")


def choose_route(request: dict[str, Any]) -> dict[str, Any]:
    """Return a capability-first route while preserving the user's target and tool choice."""
    input_format = _format_name(request.get("inputFormat"))
    target_format = _canonical_format(request.get("targetFormat"))
    editable = bool(request.get("editable", False))
    structured_source = bool(request.get("structuredSource", input_format in STRUCTURED_INPUTS))
    native_required = bool(request.get("nativeAcceptance", False))
    available = {str(item).strip() for item in request.get("availableCapabilities", []) if str(item).strip()}
    optional = {str(item).strip() for item in request.get("optionalCapabilities", []) if str(item).strip()}
    capability = _choose_capability(input_format, target_format, editable)
    route = [capability]
    warnings: list[str] = []
    blockers: list[str] = []

    if target_format in {"pptx", "docx", "xlsx", "vsdx"}:
        native_capability = NATIVE_CAPABILITIES[target_format]
        route.append(native_capability if native_required else "pdf-render-and-inspect")
    elif target_format == "tex":
        route.append("compile-and-render-pdf")
    elif target_format == "pdf":
        route.append("pdf-render-and-inspect")
        if native_required:
            route.append(NATIVE_CAPABILITIES["pdf"])
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

    policy = ROUTE_POLICIES.get(
        target_format,
        {
            "preferredGenerator": "capability-specific generator",
            "nativeApplication": "not specified",
            "acceptanceTarget": "structural QA and explicit requested native checks",
            "fallbackPolicy": "Record any fallback and repeat applicable downstream checks.",
        },
    )
    status = "BLOCKED" if blockers else "PASS_WITH_WARNING" if warnings else "PASS"
    return {
        "schemaVersion": "1.0",
        "status": status,
        "supportStatus": "SUPPORTED" if target_format in ROUTE_POLICIES else "EXPERIMENTAL",
        "inputFormat": input_format,
        "targetFormat": target_format,
        "editable": editable,
        "capability": capability,
        "preferredGenerator": policy["preferredGenerator"],
        "nativeApplication": policy["nativeApplication"],
        "acceptanceTarget": policy["acceptanceTarget"],
        "fallbackPolicy": policy["fallbackPolicy"],
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
