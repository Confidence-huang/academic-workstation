"""Back up a clean tracked checkout, restore it into an empty root, and compare SHA-256 manifests.

The command is deliberately conservative: it never deletes an existing directory, overwrites a
backup, follows a link, or treats a dirty checkout as a release source. Example:
``python scripts/recovery_rehearsal.py --source-root . --backup-root /mnt/e/CodexBackups/... \
--restore-root private-restore --output private-recovery.json``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compare_manifests import compare_manifests
from hash_artifacts import build_manifest
from path_tools import is_relative_safe, redact_path


def _git_output(source_root: Path, *arguments: str) -> str:
    """Read one non-sensitive Git fact without invoking a shell or exposing command output."""
    completed = subprocess.run(
        ["git", *arguments],
        cwd=source_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(arguments[:1])} failed with exit code {completed.returncode}")
    return completed.stdout


def _tracked_files(source_root: Path) -> tuple[str, list[str]]:
    """Return the exact tracked file list and revision for a clean release checkout."""
    status = _git_output(source_root, "status", "--porcelain=v1")
    if status.strip():
        raise RuntimeError("source checkout is dirty; recovery requires a committed baseline")
    revision = _git_output(source_root, "rev-parse", "HEAD").strip()
    raw_paths = _git_output(source_root, "ls-files", "-z")
    paths = [value for value in raw_paths.split("\x00") if value]
    if not paths:
        raise RuntimeError("source checkout has no tracked files")
    for relative in paths:
        # The manifest contract is intentionally stricter than Git's path vocabulary.
        if not is_relative_safe(relative):
            raise RuntimeError(f"tracked path is not safe for a portable snapshot: {relative}")
        candidate = source_root / relative
        if candidate.is_symlink() or not candidate.is_file():
            raise RuntimeError(f"tracked path is not a regular file: {relative}")
    return revision, sorted(paths)


def _new_empty_root(path: Path, source_root: Path, label: str) -> Path:
    """Create a new destination only when it cannot contain or be contained by the source."""
    candidate = path.expanduser().resolve(strict=False)
    if candidate == source_root or candidate.is_relative_to(source_root) or source_root.is_relative_to(candidate):
        raise RuntimeError(f"{label} must be outside the source checkout")
    if candidate.exists():
        if not candidate.is_dir() or any(candidate.iterdir()):
            raise RuntimeError(f"{label} must be absent or empty: {candidate}")
    else:
        candidate.mkdir(parents=True)
    return candidate


def _copy_snapshot(source_root: Path, target_root: Path, relative_paths: list[str]) -> None:
    """Copy only the validated regular files while preserving their relative names."""
    for relative in relative_paths:
        source = source_root / relative
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _check(name: str, status: str, details: str) -> dict[str, Any]:
    """Keep recovery stages in the same explicit check vocabulary as artifact evidence."""
    return {"name": name, "status": status, "required": True, "details": details}


def rehearse_recovery(source_root: Path, backup_root: Path, restore_root: Path) -> dict[str, Any]:
    """Create, verify, restore, and compare one immutable project snapshot."""
    source_root = source_root.expanduser().resolve()
    if not source_root.is_dir() or source_root.is_symlink():
        raise RuntimeError("source root must be a real directory")
    revision, relative_paths = _tracked_files(source_root)
    backup_root = _new_empty_root(backup_root, source_root, "backup root")
    restore_root = _new_empty_root(restore_root, source_root, "restore root")
    snapshot_root = backup_root / "snapshot"
    snapshot_root.mkdir()

    source_manifest = build_manifest(source_root, relative_paths=relative_paths)
    _copy_snapshot(source_root, snapshot_root, relative_paths)
    backup_manifest = build_manifest(snapshot_root, relative_paths=relative_paths)
    backup_comparison = compare_manifests(source_manifest, backup_manifest)

    _copy_snapshot(snapshot_root, restore_root, relative_paths)
    restore_manifest = build_manifest(restore_root, relative_paths=relative_paths)
    restore_comparison = compare_manifests(backup_manifest, restore_manifest)
    passed = backup_comparison["status"] == "PASS" and restore_comparison["status"] == "PASS"
    status = "PASS" if passed else "FAIL"
    checks = [
        _check("clean committed source", "PASS", f"revision={revision}"),
        _check("backup copy", "PASS", f"files={len(relative_paths)}"),
        _check("backup manifest comparison", backup_comparison["status"], "source equals backup snapshot"),
        _check("restore copy", "PASS", f"destination={redact_path(str(restore_root))}"),
        _check("restore manifest comparison", restore_comparison["status"], "backup snapshot equals restored checkout"),
    ]
    manifest_path = backup_root / "manifest.json"
    manifest_path.write_text(json.dumps(backup_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schemaVersion": "1.0",
        "origin": "CURRENT_RUN",
        "task": "Academic Workstation release backup and restore rehearsal",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "acceptance": {
            "highestLevel": "L6" if passed else "L5",
            "gates": {"recovery": status, "evidence": "PASS" if passed else "FAIL"},
        },
        "checks": checks,
        "artifacts": [],
        "warnings": [],
        "deferred": [],
        "blockers": [] if passed else ["backup or restore manifest comparison failed"],
        "fallbacks": [],
        "sourceRevision": revision,
        "fileCount": len(relative_paths),
        "backupRoot": redact_path(str(backup_root)),
        "backupManifest": "manifest.json",
        "restoreRoot": redact_path(str(restore_root)),
        "backupComparison": backup_comparison,
        "restoreComparison": restore_comparison,
    }


def main() -> int:
    """Run one recovery rehearsal and write a machine-readable release gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="clean tracked checkout")
    parser.add_argument("--backup-root", type=Path, required=True, help="new backup destination")
    parser.add_argument("--restore-root", type=Path, required=True, help="new empty restore destination")
    parser.add_argument("--output", type=Path, required=True, help="recovery evidence JSON")
    arguments = parser.parse_args()
    try:
        result = rehearse_recovery(arguments.source_root, arguments.backup_root, arguments.restore_root)
    except (OSError, RuntimeError, ValueError) as error:
        result = {
            "schemaVersion": "1.0",
            "origin": "CURRENT_RUN",
            "status": "FAIL",
            "checks": [],
            "artifacts": [],
            "warnings": [],
            "deferred": [],
            "blockers": [str(error)],
            "fallbacks": [],
        }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
