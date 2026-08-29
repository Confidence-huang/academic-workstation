"""Detect locally available capability signals without launching native applications.

Detection is deliberately conservative: finding an executable or standard Office path
does not prove that the application is licensed, usable, or accepted. Native acceptance
still requires an isolated synthetic run and evidence from the target application.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from pathlib import Path

from path_tools import redact_path


COMMANDS = {
    "python": "python",
    "uv": "uv",
    "git": "git",
    "gh": "gh",
    "pdftoppm": "pdftoppm",
    "soffice": "soffice",
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


def detect_capabilities() -> dict:
    """Return capability names, sanitized executable locations, and honest caveats."""
    found_commands: dict[str, str] = {}
    capabilities: set[str] = set()
    applications: dict[str, str] = {}
    warnings = ["detection is not native acceptance; licensing and round-trip behavior remain unverified"]

    for capability_name, command in COMMANDS.items():
        resolved = shutil.which(command)
        if resolved:
            found_commands[capability_name] = redact_path(resolved)
    if "pdftoppm" in found_commands:
        capabilities.add("pdf-render-and-inspect")
    if "soffice" in found_commands:
        capabilities.add("structured-office-conversion")
    if "git" in found_commands:
        capabilities.add("git-local-commit")
    if "gh" in found_commands:
        capabilities.add("github-publication")
    if "uv" in found_commands:
        capabilities.add("python-uv")

    if platform.system() == "Windows":
        for executable, capability in OFFICE_EXECUTABLES.items():
            for candidate in _office_candidates(executable):
                if candidate.is_file():
                    applications[executable] = redact_path(str(candidate))
                    capabilities.add(capability)
                    break
    else:
        warnings.append("Windows-native Office application detection was not attempted on this platform")

    return {
        "schemaVersion": "1.0",
        "status": "PASS_WITH_WARNING",
        "platform": platform.system(),
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
