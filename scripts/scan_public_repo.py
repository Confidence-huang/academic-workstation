"""Scan a Skill tree for secrets, private paths, binaries, links, and release omissions.

The scanner reports relative file locations only and never echoes suspicious source lines.
It is a gate for publication hygiene, not a substitute for human license review or a
credential provider's secret-revocation process.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


SECRET_PREFIXES = (
    "gh" + "p_",
    "gh" + "o_",
    "github_" + "pat_",
    "sk" + "-",
    "xoxb" + "-",
)
PRIVATE_KEY_MARKER = "-----BEGIN " + "PRIVATE KEY-----"
PATH_PATTERNS = (
    re.compile(r"(?i)[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/](?!<USER>)(?:[^\\/\s]+)"),
    re.compile(r"(?i)[A-Za-z]:[\\/](?:CodexProjects|CodexBackups)(?:[\\/]|$)"),
    re.compile(r"(?i)/home/(?!<USER>)(?:[A-Za-z0-9._-]+)(?:/|$)"),
    re.compile(r"(?i)" + re.escape("/" + "/" + "wsl.localhost") + r"/"),
)
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|authorization)\s*[:=]\s*([^\s#]+)"
)
BINARY_SUFFIXES = {".dll", ".exe", ".so", ".dylib", ".bin", ".pyc", ".pdb"}
IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"}
REQUIRED_RELEASE_FILES = {
    "SKILL.md",
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "agents/openai.yaml",
}


def _looks_like_secret(line: str) -> bool:
    """Detect high-signal credential forms while allowing documented placeholders."""
    lowered = line.lower()
    if PRIVATE_KEY_MARKER.lower() in lowered:
        return True
    if any(prefix.lower() in lowered for prefix in SECRET_PREFIXES):
        return True
    assignment = SENSITIVE_ASSIGNMENT.search(line)
    if assignment:
        value = assignment.group(1).strip("'\"`")
        if value and not (value.startswith("<") or value.startswith("${") or value in {"REDACTED", "redacted"}):
            return len(value) >= 8
    return False


def _looks_like_private_path(line: str) -> bool:
    """Reject concrete workstation paths but allow explicit public placeholders."""
    return any(pattern.search(line) for pattern in PATH_PATTERNS)


def scan_public_repo(root: Path, strict: bool = False) -> dict:
    """Return publication findings for regular files under ``root``."""
    root = Path(root).resolve()
    findings: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    seen: set[str] = set()
    if not root.is_dir():
        return {"schemaVersion": "1.0", "status": "FAIL", "findings": [{"rule": "root", "path": "."}], "warnings": []}

    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        directory_names[:] = [name for name in directory_names if name not in IGNORED_DIRECTORIES]
        for name in directory_names:
            candidate = current_path / name
            if candidate.is_symlink():
                findings.append({"rule": "symlink", "path": candidate.relative_to(root).as_posix()})
        for name in file_names:
            candidate = current_path / name
            relative = candidate.relative_to(root).as_posix()
            seen.add(relative)
            if candidate.is_symlink():
                findings.append({"rule": "symlink", "path": relative})
                continue
            if candidate.suffix.lower() in BINARY_SUFFIXES:
                findings.append({"rule": "binary", "path": relative})
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                findings.append({"rule": "non-utf8-binary", "path": relative})
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if _looks_like_secret(line):
                    findings.append({"rule": "secret", "path": relative, "line": str(line_number)})
                elif _looks_like_private_path(line):
                    findings.append({"rule": "private-path", "path": relative, "line": str(line_number)})
            if name in {".env", ".env.local", ".env.production"}:
                findings.append({"rule": "environment-file", "path": relative})

    missing = sorted(REQUIRED_RELEASE_FILES - seen) if strict else []
    for relative in missing:
        findings.append({"rule": "required-release-file", "path": relative})
    if not (root / "references").is_dir():
        warnings.append({"rule": "references-directory", "path": "references"})
    if not (root / "tests").is_dir():
        warnings.append({"rule": "tests-directory", "path": "tests"})
    status = "FAIL" if findings else "PASS_WITH_WARNING" if warnings else "PASS"
    return {
        "schemaVersion": "1.0",
        "status": status,
        "findings": findings,
        "warnings": warnings,
        "fileCount": len(seen),
        "strict": strict,
    }


def main() -> int:
    """Scan a repository and return non-zero when a publication finding exists."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Skill repository root")
    parser.add_argument("--strict", action="store_true", help="require the public release file set")
    arguments = parser.parse_args()
    result = scan_public_repo(arguments.root, arguments.strict)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
