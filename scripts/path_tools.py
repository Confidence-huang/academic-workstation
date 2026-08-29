"""Keep cross-platform paths logical, testable, and safe to publish.

The functions here never access the filesystem. They normalize Windows, WSL, UNC, and POSIX
spellings into a logical form, translate only known path families, and redact personal roots before
a public report is written. Example: ``translate_path("C:\\work\\paper.pdf", "posix")`` returns
``/mnt/c/work/paper.pdf``.
"""

from __future__ import annotations

import re


class PathError(ValueError):
    """Report a path that cannot be safely normalized or translated."""


WINDOWS_DRIVE = re.compile(r"^(?P<drive>[A-Za-z]):(?:/|$)")
WSL_PREFIX = "/" + "/" + "wsl.localhost/"
WSL_UNC = re.compile(r"^" + re.escape(WSL_PREFIX) + r"(?P<distro>[^/]+)(?P<path>/.*)?$", re.IGNORECASE)
WINDOWS_USER = re.compile(r"(?i)(?P<prefix>[A-Za-z]:/Users/)[^/]+(?P<tail>/.*)?$")
POSIX_HOME = re.compile(r"^/home/[^/]+(?P<tail>/.*)?$")


def _parts_without_escape(value: str) -> list[str]:
    """Normalize separators while rejecting NUL and traversal above a logical root."""
    if "\x00" in value:
        raise PathError("path contains a NUL character")

    parts: list[str] = []
    for part in value.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise PathError("path escapes its logical root")
            parts.pop()
            continue
        parts.append(part)
    return parts


def normalize_path(value: str) -> str:
    """Return a stable slash-separated path without changing its platform family."""
    if not isinstance(value, str) or not value.strip():
        raise PathError("path must be a non-empty string")

    candidate = value.strip().replace("\\", "/")
    unc_match = WSL_UNC.match(candidate)
    if unc_match:
        distro = unc_match.group("distro")
        parts = _parts_without_escape(unc_match.group("path") or "/")
        suffix = "/" + "/".join(parts) if parts else ""
        return WSL_PREFIX + f"{distro}{suffix}"

    drive_match = WINDOWS_DRIVE.match(candidate)
    if drive_match:
        drive = drive_match.group("drive").upper()
        suffix = "/".join(_parts_without_escape(candidate[3:]))
        return f"{drive}:/" + suffix if suffix else f"{drive}:/"

    is_absolute = candidate.startswith("/")
    parts = _parts_without_escape(candidate)
    prefix = "/" if is_absolute else ""
    return prefix + "/".join(parts)


def translate_path(value: str, target: str, distro: str = "Ubuntu-24.04") -> str:
    """Translate a known Windows/WSL path family to ``posix`` or ``windows``."""
    normalized = normalize_path(value)
    if target not in {"posix", "windows"}:
        raise PathError("target must be 'posix' or 'windows'")

    unc_match = WSL_UNC.match(normalized)
    drive_match = WINDOWS_DRIVE.match(normalized)
    if target == "posix":
        if unc_match:
            return normalize_path(unc_match.group("path") or "/")
        if drive_match:
            suffix = normalized[2:]
            return "/mnt/" + drive_match.group("drive").lower() + suffix
        return normalized

    if drive_match:
        return normalized.replace("/", "\\")
    if normalized.startswith("/mnt/") and len(normalized) >= 7:
        drive = normalized[5].upper()
        suffix = normalized[6:]
        return f"{drive}:\\" + suffix.replace("/", "\\") if suffix else f"{drive}:\\"
    if unc_match:
        windows_prefix = "\\" * 2 + "wsl.localhost" + "\\"
        return windows_prefix + unc_match.group("distro") + (unc_match.group("path") or "").replace("/", "\\")
    if normalized.startswith("/"):
        return f"\\\\wsl.localhost\\{distro}" + normalized.replace("/", "\\")
    raise PathError("relative paths have no safe Windows translation")


def redact_path(value: str) -> str:
    """Replace personal path components with public placeholders without exposing the name."""
    normalized = normalize_path(value)
    unc_match = WSL_UNC.match(normalized)
    if unc_match:
        public_path = unc_match.group("path") or "/"
        return "${WSL_ROOT}" + public_path

    windows_match = WINDOWS_USER.match(normalized)
    if windows_match:
        return "C:/Users/<USER>" + (windows_match.group("tail") or "")

    home_match = POSIX_HOME.match(normalized)
    if home_match:
        return "/home/<USER>" + (home_match.group("tail") or "")

    replacements = (
        ("D:" + "/CodexProjects", "${SKILLS_ROOT}"),
        ("E:" + "/CodexBackups", "${BACKUP_ROOT}"),
    )
    for private_root, public_root in replacements:
        if normalized == private_root or normalized.startswith(private_root + "/"):
            return public_root + normalized[len(private_root) :]
    return normalized


def is_relative_safe(value: str) -> bool:
    """Return whether a manifest path is relative and cannot escape its owning root."""
    try:
        normalized = normalize_path(value)
    except PathError:
        return False
    return not normalized.startswith(("/", "//")) and not WINDOWS_DRIVE.match(normalized)
