# Platform support

The scripts are standard-library Python and avoid host mutation. They accept logical
relative paths and translate only known Windows, WSL, and POSIX path families.

## Boundaries

- Linux-native development should run on a native Linux filesystem with the project's
  selected interpreter and lockfile.
- Windows-only Office, Visio, PDF-reader, and hardware acceptance stays on Windows.
- WSL paths may require local Windows staging before native COM save operations.
- A detected executable or installed application is not proof of license, login, or usable
  automation.
- User-owned native application instances must remain untouched.

The Windows-only `scripts/native_acceptance.ps1` runner is the native boundary for Word, Excel,
and Visio. It writes synthetic artifacts to a caller-supplied private staging root, uses fresh
COM instances, waits for bounded cleanup, and records process IDs without terminating them.
LaTeX compilation and PDF QA can run on any host with the discovered tools; the matrix keeps
missing native capabilities as `UNAVAILABLE` or `NOT_RUN`.

Use placeholders such as <PROJECT_ROOT>, <SKILLS_ROOT>, and <BACKUP_ROOT> in public reports.
Never publish a concrete workstation root.
