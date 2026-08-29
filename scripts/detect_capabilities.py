"""Detect tool and native-application signals without launching or mutating them.

The output describes command paths, short versions, host platform, and caveats. It is a routing
hint only: an executable does not prove license validity, native round-trip behavior, or a clean
process boundary. Example: ``python scripts/detect_capabilities.py --output capability.json``.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from path_tools import redact_path


COMMANDS = {
    "python": ("python", ["--version"]),
    "python3": ("python3", ["--version"]),
    "uv": ("uv", ["--version"]),
    "git": ("git", ["--version"]),
    "gh": ("gh", ["--version"]),
    "pwsh": ("pwsh", ["--version"]),
    "pdftoppm": ("pdftoppm", ["-v"]),
    "pdfinfo": ("pdfinfo", ["-v"]),
    "latexmk": ("latexmk", ["-v"]),
    "pdflatex": ("pdflatex", ["--version"]),
    "xelatex": ("xelatex", ["--version"]),
    "lualatex": ("lualatex", ["--version"]),
    "tectonic": ("tectonic", ["--version"]),
}
OFFICE_EXECUTABLES = {
    "POWERPNT.EXE": "native-powerpoint-acceptance",
    "WINWORD.EXE": "native-word-acceptance",
    "EXCEL.EXE": "native-excel-acceptance",
    "VISIO.EXE": "native-visio-acceptance",
    "FoxitPDFReader.exe": "native-pdf-reader-acceptance",
}


def _program_files_roots() -> list[Path]:
    """Return only Windows program roots exposed by the current process."""
    values = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramW670")]
    return [Path(value) for value in values if value]


def _office_candidates(executable: str) -> list[Path]:
    """Build bounded, read-only candidate paths for common Windows installations."""
    candidates: list[Path] = []
    for root in _program_files_roots():
        candidates.extend(
            [
                root / "Microsoft Office" / "root" / "Office16" / executable,
                root / "Microsoft Office" / "root" / "Office15" / executable,
                root / "Microsoft Office" / "Office16" / executable,
                root / "Foxit Software" / "Foxit PDF Reader" / executable,
            ]
        )
    return candidates


def _command_version(path: str, arguments: list[str]) -> str:
    """Read one short version line without exposing full command output or secrets."""
    try:
        result = subprocess.run(
            [path, *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    for line in (result.stdout + "\n" + result.stderr).splitlines():
        if line.strip():
            return line.strip()[:160]
    return "unknown"


def _which_tool(name: str, which: Callable[[str], str | None]) -> str | None:
    """Resolve a Linux command or its Windows executable form when running under WSL."""
    return which(name) or which(name + ".exe")


def detect_capabilities(
    which: Callable[[str], str | None] = shutil.which,
    system: Callable[[], str] = platform.system,
) -> dict:
    """Return sanitized capability records and honest native-acceptance caveats."""
    platform_name = system()
    found_commands: dict[str, dict[str, str]] = {}
    capabilities: set[str] = set()
    applications: dict[str, dict[str, str]] = {}
    warnings = ["detection is not native acceptance; licensing and round-trip behavior remain unverified"]

    for capability_name, (command, version_arguments) in COMMANDS.items():
        resolved = _which_tool(command, which)
        if not resolved:
            continue
        found_commands[capability_name] = {
            "available": "true",
            "path": redact_path(resolved),
            "version": _command_version(resolved, version_arguments),
            "platform": platform_name,
            "notes": "command was resolved without starting a native acceptance run",
        }

    if "pdftoppm" in found_commands and "pdfinfo" in found_commands:
        capabilities.add("pdf-render-and-inspect")
    if "latexmk" in found_commands or any(name in found_commands for name in ("tectonic", "xelatex", "lualatex", "pdflatex")):
        capabilities.add("latex-compilation")
    if "python" in found_commands or "python3" in found_commands:
        capabilities.add("python-runtime")
    if "git" in found_commands:
        capabilities.add("git-local-commit")
    if "gh" in found_commands:
        capabilities.add("github-publication")
    if "uv" in found_commands:
        capabilities.add("python-uv")

    if platform_name == "Windows":
        for executable, capability in OFFICE_EXECUTABLES.items():
            for candidate in _office_candidates(executable):
                if candidate.is_file():
                    applications[executable] = {
                        "available": "true",
                        "path": redact_path(str(candidate)),
                        "version": "installed executable; native behavior not tested by detection",
                        "platform": platform_name,
                        "notes": "path candidate only; license and isolated COM evidence remain separate",
                    }
                    capabilities.add(capability)
                    break
    else:
        warnings.append("Windows-native Office application detection was not attempted on this platform")

    return {
        "schemaVersion": "1.0",
        "status": "PASS_WITH_WARNING",
        "platform": platform_name,
        "commands": found_commands,
        "applications": applications,
        "availableCapabilities": sorted(capabilities),
        "warnings": warnings,
        "nativeAcceptance": "NOT_RUN",
    }


def main() -> int:
    """Print a sanitized capability snapshot without changing host state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    arguments = parser.parse_args()
    serialized = json.dumps(detect_capabilities(), ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
