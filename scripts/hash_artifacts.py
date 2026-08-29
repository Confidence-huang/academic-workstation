"""Create a relative SHA-256 manifest without following unsafe links.

The manifest is intentionally independent of the absolute root path. Example:
``python scripts/hash_artifacts.py --root examples --output manifest.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

from path_tools import is_relative_safe, normalize_path


def sha256_file(path: Path) -> str:
    """Hash one regular file in bounded chunks so large artifacts stay streamable."""
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(path: Path, root: Path) -> str:
    """Return a POSIX relative name and reject a path that escapes the requested root."""
    relative = path.relative_to(root)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"path escapes root: {path}")
    return relative.as_posix()


def _walk_files(root: Path, excluded_directories: set[str] | None = None) -> tuple[list[tuple[str, Path]], list[str]]:
    """Collect regular files while recording links instead of traversing them."""
    files: list[tuple[str, Path]] = []
    links: list[str] = []
    excluded = excluded_directories or set()
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for directory_name in directory_names:
            candidate = current_path / directory_name
            if directory_name in excluded:
                continue
            if candidate.is_symlink():
                links.append(_safe_relative(candidate, root))
            else:
                kept_directories.append(directory_name)
        directory_names[:] = kept_directories
        for file_name in file_names:
            candidate = current_path / file_name
            relative = _safe_relative(candidate, root)
            if candidate.is_symlink():
                links.append(relative)
            elif candidate.is_file():
                files.append((relative, candidate))
    return sorted(files), sorted(links)


def build_manifest(
    root: Path,
    relative_paths: Iterable[str] | None = None,
    excluded_directories: set[str] | None = None,
) -> dict:
    """Hash either an explicit safe file list or every regular file below the root."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("root must be a real directory")
    root = root.resolve()
    if relative_paths is None:
        files, links = _walk_files(root, excluded_directories)
    else:
        files = []
        links = []
        for raw_path in relative_paths:
            if not isinstance(raw_path, str) or not is_relative_safe(raw_path):
                raise ValueError(f"manifest path must be relative: {raw_path}")
            relative = Path(normalize_path(raw_path))
            candidate = root / relative
            if candidate.is_symlink():
                links.append(relative.as_posix())
            elif not candidate.is_file():
                raise FileNotFoundError(candidate)
            else:
                files.append((relative.as_posix(), candidate))
        files.sort()
    return {
        "schemaVersion": 1,
        "algorithm": "SHA-256",
        "files": [
            {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for relative, path in files
        ],
        "links": links,
    }


def main() -> int:
    """Build a manifest and write it without exposing the absolute root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="directory to hash")
    parser.add_argument("--path", action="append", dest="paths", help="safe relative path; repeatable")
    parser.add_argument("--exclude-dir", action="append", default=[], help="directory name to skip while walking")
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    arguments = parser.parse_args()
    manifest = build_manifest(arguments.root, arguments.paths, set(arguments.exclude_dir))
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
