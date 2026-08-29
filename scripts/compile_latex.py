"""Compile a LaTeX source with an installed engine and classify its acceptance evidence.

The compiler prefers ``latexmk -xelatex`` when both tools exist, then records an explicit engine
fallback rather than silently changing the toolchain. Example:
``python scripts/compile_latex.py --source examples/latex/main.tex --output-dir private-evidence/latex``.
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
from typing import Any, Callable

from derive_status import derive_status
from path_tools import redact_path


ENGINE_NAMES = ("latexmk", "tectonic", "xelatex", "lualatex", "pdflatex")
PREFERRED_ENGINE = "latexmk-xelatex"
UNDEFINED_REFERENCE = re.compile(r"undefined references?|Reference .* undefined", re.IGNORECASE)
UNDEFINED_CITATION = re.compile(r"undefined citations?|Citation .* undefined", re.IGNORECASE)
OVERFULL_BOX = re.compile(r"Overfull \\hbox", re.IGNORECASE)
UNDERFULL_BOX = re.compile(r"Underfull \\hbox", re.IGNORECASE)
MISSING_FIGURE = re.compile(r"(?:file|image|figure).*not found|not find file", re.IGNORECASE)
MISSING_FONT = re.compile(r"(?:font|mktextfm).*not found|font warning", re.IGNORECASE)
FATAL_ERROR = re.compile(r"(?:LaTeX Error:|Fatal error|Emergency stop|Undefined control sequence)", re.IGNORECASE)


def _hash_file(path: Path) -> str:
    """Hash compile outputs in chunks so the evidence does not depend on memory size."""
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_engines(which: Callable[[str], str | None] = shutil.which) -> dict[str, str]:
    """Return installed LaTeX commands without assuming a fixed TeX distribution path."""
    return {name: resolved for name in ENGINE_NAMES if (resolved := which(name))}


def select_engine(available: dict[str, str]) -> dict[str, Any] | None:
    """Select the strongest reproducible route from the commands actually found."""
    if "latexmk" in available and "xelatex" in available:
        return {
            "name": PREFERRED_ENGINE,
            "command": available["latexmk"],
            "arguments": ["-cd", "-xelatex", "-synctex=1", "-interaction=nonstopmode", "-halt-on-error"],
            "primary": True,
        }
    if "latexmk" in available:
        return {
            "name": "latexmk-pdf",
            "command": available["latexmk"],
            "arguments": ["-cd", "-pdf", "-synctex=1", "-interaction=nonstopmode", "-halt-on-error"],
            "primary": False,
        }
    for name in ("tectonic", "xelatex", "lualatex", "pdflatex"):
        if name in available:
            return {"name": name, "command": available[name], "arguments": [], "primary": False}
    return None


def _run(command: list[str], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    """Run one compiler command with captured output and a hard upper bound."""
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )


def _artifact(path: Path, root: Path) -> dict[str, Any]:
    """Return a relative artifact hash for a compile output."""
    return {
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _hash_file(path),
    }


def _check(name: str, status: str, required: bool, details: str = "") -> dict[str, Any]:
    """Keep compile decisions in the same check shape as Office evidence."""
    result: dict[str, Any] = {"name": name, "status": status, "required": required}
    if details:
        result["details"] = details
    return result


def _classify_log(log_text: str) -> dict[str, Any]:
    """Turn common TeX diagnostics into stable content and layout checks."""
    return {
        "undefinedReferences": bool(UNDEFINED_REFERENCE.search(log_text)),
        "undefinedCitations": bool(UNDEFINED_CITATION.search(log_text)),
        "missingFigure": bool(MISSING_FIGURE.search(log_text)),
        "missingFont": bool(MISSING_FONT.search(log_text)),
        "fatalError": bool(FATAL_ERROR.search(log_text)),
        "overfullBoxes": len(OVERFULL_BOX.findall(log_text)),
        "underfullBoxes": len(UNDERFULL_BOX.findall(log_text)),
    }


def compile_latex(source: Path, output_dir: Path, timeout_seconds: int = 180) -> dict[str, Any]:
    """Compile one source file, preserve the log, and derive a conservative evidence status."""
    source = Path(source).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    blockers: list[str] = []
    fallbacks: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    log_text = ""
    command_record: list[str] = []
    compile_result: subprocess.CompletedProcess[str] | None = None
    source_ok = source.is_file() and source.suffix.lower() == ".tex"
    checks.append(_check("LaTeX source exists", "PASS" if source_ok else "FAIL", True, redact_path(str(source))))

    available = discover_engines()
    selected = select_engine(available)
    if selected is None:
        blockers.append("no supported LaTeX engine is available on this host")
        checks.append(_check("LaTeX engine available", "NOT_RUN", False, "Checked latexmk, tectonic, xelatex, lualatex, and pdflatex."))
    elif source_ok:
        checks.append(_check("LaTeX engine available", "PASS", True, selected["name"]))
        if not selected["primary"]:
            fallbacks.append(
                {
                    "step": "latex-engine",
                    "primary": "latexmk -xelatex",
                    "error": "preferred latexmk-xelatex route was unavailable",
                    "fallback": selected["name"],
                    "fallbackResult": "NOT_RUN",
                }
            )
        if selected["name"].startswith("latexmk"):
            command = [selected["command"], *selected["arguments"], f"-outdir={output_dir}", source.name]
        elif selected["name"] == "tectonic":
            command = [selected["command"], "--keep-logs", "--outdir", str(output_dir), source.name]
        else:
            command = [selected["command"], "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={output_dir}", source.name]
        command_record = [redact_path(str(item)) if index == 0 else str(item) for index, item in enumerate(command)]
        try:
            compile_result = _run(command, source.parent, timeout_seconds)
            log_text = f"{compile_result.stdout}\n{compile_result.stderr}"
        except (OSError, subprocess.TimeoutExpired) as error:
            log_text = str(error)
            checks.append(_check("LaTeX compilation", "FAIL", True, str(error)))

    log_path = output_dir / "compile.log"
    log_path.write_text(log_text, encoding="utf-8")
    artifacts.append(_artifact(log_path, output_dir))
    pdf_path = output_dir / f"{source.stem}.pdf"
    if compile_result is not None:
        # Latexmk intentionally reports first-pass unresolved labels before rerunning TeX; classify the final TeX log so transient warnings do not become false failures.
        final_log_path = output_dir / f"{source.stem}.log"
        final_log_text = final_log_path.read_text(encoding="utf-8", errors="replace") if final_log_path.is_file() else log_text
        classification = _classify_log(final_log_text)
        compile_passed = compile_result.returncode == 0 and not classification["fatalError"]
        checks.append(_check("LaTeX compilation", "PASS" if compile_passed else "FAIL", True, f"exit code {compile_result.returncode}"))
        if not pdf_path.is_file():
            checks.append(_check("compiled PDF exists", "FAIL", True, "The compiler returned without the expected PDF."))
        else:
            checks.append(_check("compiled PDF exists", "PASS", True, "The expected PDF was created."))
            artifacts.append(_artifact(pdf_path, output_dir))
        checks.append(_check("references resolved", "FAIL" if classification["undefinedReferences"] else "PASS", True))
        checks.append(_check("citations resolved", "FAIL" if classification["undefinedCitations"] else "PASS", True))
        checks.append(_check("figures and fonts resolved", "FAIL" if classification["missingFigure"] or classification["missingFont"] else "PASS", True))
        if classification["overfullBoxes"]:
            warnings.append(f"{classification['overfullBoxes']} overfull hbox warning(s) remain")
        if classification["underfullBoxes"]:
            warnings.append(f"{classification['underfullBoxes']} underfull hbox warning(s) remain")
    else:
        classification = _classify_log(log_text)
        if not blockers and not any(item["name"] == "LaTeX compilation" for item in checks):
            checks.append(_check("LaTeX compilation", "NOT_RUN", True, "Compilation did not start."))
        checks.extend(
            [
                _check("compiled PDF exists", "NOT_RUN", True),
                _check("references resolved", "NOT_RUN", True),
                _check("citations resolved", "NOT_RUN", True),
                _check("figures and fonts resolved", "NOT_RUN", True),
            ]
        )

    evidence: dict[str, Any] = {
        "schemaVersion": "1.0",
        "origin": "CURRENT_RUN",
        "artifactType": "latex",
        "task": "LaTeX compilation and PDF preparation",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "platform": "current host",
        "nativeApplication": "TeX engine",
        "nativeApplicationVersion": selected["name"] if selected else "unavailable",
        "sourcePath": source.name if source_ok else None,
        "exportPath": pdf_path.name if pdf_path.is_file() else None,
        "checks": checks,
        "artifacts": artifacts,
        "warnings": warnings,
        "deferred": ["Run pdf_qa.py with a page-by-page visual review after compilation."],
        "blockers": blockers,
        "fallbacks": fallbacks,
        "engine": {
            "selected": selected["name"] if selected else None,
            "path": redact_path(selected["command"]) if selected else None,
            "command": command_record,
            "available": {name: redact_path(path) for name, path in available.items()},
        },
        "logClassification": classification,
        "acceptance": {
            "highestLevel": "L1" if pdf_path.is_file() else "L0",
            "gates": {
                "generate": "PASS" if source_ok else "FAIL",
                "parse": "PASS" if source_ok else "FAIL",
                "nativeOpen": "NOT_APPLICABLE",
                "roundtrip": "NOT_APPLICABLE",
                "export": "PASS" if pdf_path.is_file() else "FAIL",
                "structuralQA": "PASS" if pdf_path.is_file() and compile_result and compile_result.returncode == 0 and not any(classification[key] for key in ("fatalError", "undefinedReferences", "undefinedCitations", "missingFigure", "missingFont")) else "FAIL",
                "visualQA": "NOT_RUN",
                "evidence": "PASS" if artifacts else "FAIL",
                "recovery": "NOT_RUN",
            },
        },
    }
    if fallbacks and compile_result is not None:
        fallbacks[0]["fallbackResult"] = "PASS" if evidence["acceptance"]["gates"]["structuralQA"] == "PASS" else "FAIL"
    evidence["status"] = derive_status(evidence)["status"]
    return evidence


def main() -> int:
    """Compile a source, write JSON evidence, and return a status-sensitive exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="LaTeX source file")
    parser.add_argument("--output-dir", type=Path, required=True, help="directory for PDF and compile log")
    parser.add_argument("--output", type=Path, help="optional evidence JSON output")
    parser.add_argument("--timeout", type=int, default=180, help="compiler timeout in seconds")
    arguments = parser.parse_args()
    evidence = compile_latex(arguments.source, arguments.output_dir, arguments.timeout)
    serialized = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return {"PASS": 0, "PASS_WITH_WARNING": 0, "FAIL": 1, "BLOCKED": 2}[evidence["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
