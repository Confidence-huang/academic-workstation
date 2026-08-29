"""Inspect and render a PDF without treating a renderer as native source acceptance.

The command uses ``pdfinfo`` for page geometry and ``pdftoppm`` for deterministic PNG output.
Pixel-level readability remains an explicit page-by-page visual record supplied with
``--visual-review``. Example: ``python scripts/pdf_qa.py --pdf export.pdf --root evidence
--render-dir evidence/rendered --visual-review evidence/visual-review.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from derive_status import derive_status


PDFINFO_PAGE_COUNT = re.compile(r"^Pages:\s*(?P<count>\d+)", re.MULTILINE)
PDFINFO_PAGE_SIZE = re.compile(r"^Page size:\s*(?P<width>[0-9.]+)\s+x\s+(?P<height>[0-9.]+)", re.MULTILINE)


def _hash_file(path: Path) -> str:
    """Hash each output in bounded chunks so PDF evidence stays reproducible."""
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_tool(command: str, arguments: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    """Run one read-only PDF utility with a bounded timeout and captured diagnostics."""
    return subprocess.run(
        [command, *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )


def _relative_path(path: Path, root: Path) -> str:
    """Return only a relative evidence name and reject outputs outside the evidence root."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"PDF evidence output is outside root: {path}") from error


def _artifact(path: Path, root: Path) -> dict[str, Any]:
    """Create a relative hash record for one existing regular output file."""
    return {
        "path": _relative_path(path, root),
        "bytes": path.stat().st_size,
        "sha256": _hash_file(path),
    }


def _check(name: str, status: str, required: bool, details: str = "") -> dict[str, Any]:
    """Keep every QA decision in the common evidence check shape."""
    result: dict[str, Any] = {"name": name, "status": status, "required": required}
    if details:
        result["details"] = details
    return result


def _load_visual_review(path: Path | None) -> list[dict[str, Any]] | None:
    """Load human/model page observations while accepting either a list or a wrapped object."""
    if path is None:
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict) and isinstance(value.get("pages"), list):
        return value["pages"]
    if isinstance(value, list):
        return value
    raise ValueError("visual review must be an array or an object with a pages array")


def _visual_check(reviews: list[dict[str, Any]] | None, page_count: int | None) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Require one observation per rendered page and surface geometry problems as failures."""
    if reviews is None:
        return _check("page-by-page visual review", "NOT_RUN", True, "Supply --visual-review after inspecting every rendered page."), [], []
    if page_count is None or not isinstance(page_count, int) or page_count < 1:
        return _check("page-by-page visual review", "FAIL", True, "Visual review cannot be matched without a valid page count."), reviews, []

    page_numbers = [item.get("page") for item in reviews if isinstance(item, dict)]
    expected_pages = set(range(1, page_count + 1))
    observed_pages = {page for page in page_numbers if isinstance(page, int)}
    if observed_pages != expected_pages or len(page_numbers) != len(observed_pages):
        return _check("page-by-page visual review", "FAIL", True, "Visual review must contain each page exactly once."), reviews, []

    warnings: list[str] = []
    problems: list[str] = []
    for review in reviews:
        if not isinstance(review, dict):
            problems.append("a visual review entry is not an object")
            continue
        if any(review.get(flag) is True for flag in ("blank", "clipping", "overlap", "overflow")):
            problems.append(f"page {review.get('page')} has a flagged geometry problem")
        notes = review.get("notes", [])
        if isinstance(notes, list):
            warnings.extend(f"page {review.get('page')}: {note}" for note in notes if isinstance(note, str) and note.strip())
        else:
            problems.append(f"page {review.get('page')} notes are not an array")
    status = "FAIL" if problems else "PASS"
    details = "; ".join(problems) if problems else "Every rendered page has an explicit visual observation."
    return _check("page-by-page visual review", status, True, details), reviews, warnings


def inspect_pdf(
    pdf_path: Path,
    root: Path | None = None,
    render_dir: Path | None = None,
    visual_review: list[dict[str, Any]] | None = None,
    source_artifact_type: str | None = None,
    native_application: str = "configured PDF reader",
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    """Inspect, render, hash, and derive one PDF QA evidence document."""
    pdf_path = Path(pdf_path).resolve()
    evidence_root = Path(root or pdf_path.parent).resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)
    render_root = Path(render_dir or evidence_root / "rendered").resolve()
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    blockers: list[str] = []
    artifacts: list[dict[str, Any]] = []
    rendered_pages: list[Path] = []
    page_count: int | None = None
    page_geometry: tuple[float, float] | None = None

    if pdf_path.is_symlink() or not pdf_path.is_file():
        checks.append(_check("PDF file exists", "FAIL", True, "The requested PDF is missing or is a link."))
    else:
        checks.append(_check("PDF file exists", "PASS", True, "The input is a regular file."))
        artifacts.append(_artifact(pdf_path, evidence_root))

    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        checks.append(_check("pdfinfo available", "NOT_RUN", False, "pdfinfo is not available on this host."))
        blockers.append("pdfinfo is required for deterministic PDF structure inspection")
    elif pdf_path.is_file() and not pdf_path.is_symlink():
        try:
            info = _run_tool(pdfinfo, [str(pdf_path)], timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as error:
            info = None
            checks.append(_check("pdfinfo execution", "FAIL", True, str(error)))
        if info is not None:
            combined_output = f"{info.stdout}\n{info.stderr}"
            page_match = PDFINFO_PAGE_COUNT.search(combined_output)
            size_match = PDFINFO_PAGE_SIZE.search(combined_output)
            if info.returncode == 0 and page_match:
                page_count = int(page_match.group("count"))
                checks.append(_check("PDF structure parse", "PASS", True, "pdfinfo parsed the document."))
            else:
                checks.append(_check("PDF structure parse", "FAIL", True, "pdfinfo could not parse the document."))
            if size_match:
                page_geometry = (float(size_match.group("width")), float(size_match.group("height")))
                checks.append(_check("page geometry", "PASS" if all(value > 0 for value in page_geometry) else "FAIL", True, "The first page has positive dimensions."))
            else:
                checks.append(_check("page geometry", "FAIL", True, "pdfinfo did not report page dimensions."))
    else:
        checks.append(_check("PDF structure parse", "NOT_RUN", True, "Structure inspection waits for a regular PDF file."))

    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        checks.append(_check("pdftoppm available", "NOT_RUN", False, "pdftoppm is not available on this host."))
        blockers.append("pdftoppm is required for deterministic page rendering")
    elif page_count and pdf_path.is_file() and not pdf_path.is_symlink():
        # A rerun may have fewer pages; remove only this QA command's old page images before counting.
        if render_root.is_dir():
            for old_page in render_root.glob("page-*.png"):
                if old_page.is_file() and not old_page.is_symlink():
                    old_page.unlink()
        render_root.mkdir(parents=True, exist_ok=True)
        prefix = render_root / "page"
        try:
            render = _run_tool(pdftoppm, ["-png", "-r", "120", str(pdf_path), str(prefix)], timeout_seconds)
            rendered_pages = sorted(render_root.glob("page-*.png"))
            render_passed = render.returncode == 0 and len(rendered_pages) == page_count and all(path.stat().st_size > 0 for path in rendered_pages)
            checks.append(_check("PDF page rendering", "PASS" if render_passed else "FAIL", True, f"Rendered {len(rendered_pages)} of {page_count} pages."))
            if not render_passed and render.stderr.strip():
                warnings.append("pdftoppm reported a rendering diagnostic; inspect the private command log.")
            artifacts.extend(_artifact(path, evidence_root) for path in rendered_pages if path.is_file())
        except (OSError, subprocess.TimeoutExpired) as error:
            checks.append(_check("PDF page rendering", "FAIL", True, str(error)))
    else:
        checks.append(_check("PDF page rendering", "NOT_RUN", True, "Rendering waits for a valid parsed page count."))

    visual_result, review_records, visual_warnings = _visual_check(visual_review, page_count)
    checks.append(visual_result)
    warnings.extend(visual_warnings)
    if visual_warnings:
        warnings.append("Visual review notes are non-blocking observations and remain visible in evidence.")

    evidence: dict[str, Any] = {
        "schemaVersion": "1.0",
        "origin": "CURRENT_RUN",
        "artifactType": "pdf",
        "sourceArtifactType": source_artifact_type,
        "task": "PDF structural, render, and page-by-page visual QA",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "platform": "current host",
        "nativeApplication": native_application,
        "nativeApplicationVersion": "not captured by the renderer",
        "sourcePath": _relative_path(pdf_path, evidence_root) if pdf_path.is_file() else None,
        "exportPath": _relative_path(pdf_path, evidence_root) if pdf_path.is_file() else None,
        "checks": checks,
        "artifacts": artifacts,
        "visualReview": review_records,
        "warnings": warnings,
        "deferred": [],
        "blockers": blockers,
        "acceptance": {
            "highestLevel": "L5" if visual_result["status"] == "PASS" else "L1",
            "gates": {
                "generate": "NOT_APPLICABLE",
                "parse": "PASS" if page_count else "FAIL",
                "nativeOpen": "NOT_APPLICABLE",
                "roundtrip": "NOT_APPLICABLE",
                "export": "NOT_APPLICABLE",
                "structuralQA": "PASS" if page_count and page_geometry else "FAIL",
                "visualQA": visual_result["status"],
                "evidence": "PASS" if artifacts else "FAIL",
                "recovery": "NOT_RUN",
            },
        },
        "pageCount": page_count,
        "pageGeometryPoints": {"width": page_geometry[0], "height": page_geometry[1]} if page_geometry else None,
    }
    evidence["status"] = derive_status(evidence)["status"]
    return evidence


def main() -> int:
    """Run PDF QA from the command line and return a status-sensitive exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True, help="PDF to inspect")
    parser.add_argument("--root", type=Path, help="evidence root containing the PDF and renders")
    parser.add_argument("--render-dir", type=Path, help="directory for page PNGs")
    parser.add_argument("--visual-review", type=Path, help="JSON array or {pages: [...]} page observations")
    parser.add_argument("--source-artifact-type", help="artifact row that produced this PDF, such as docx or latex")
    parser.add_argument("--native-application", default="configured PDF reader", help="reader name for the evidence record")
    parser.add_argument("--output", type=Path, help="optional evidence JSON output")
    arguments = parser.parse_args()
    evidence = inspect_pdf(
        arguments.pdf,
        arguments.root,
        arguments.render_dir,
        _load_visual_review(arguments.visual_review),
        arguments.source_artifact_type,
        arguments.native_application,
    )
    serialized = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return {"PASS": 0, "PASS_WITH_WARNING": 0, "FAIL": 1, "BLOCKED": 2}[evidence["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
