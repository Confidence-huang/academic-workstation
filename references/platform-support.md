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

Use placeholders such as <PROJECT_ROOT>, <SKILLS_ROOT>, and <BACKUP_ROOT> in public reports.
Never publish a concrete workstation root.
