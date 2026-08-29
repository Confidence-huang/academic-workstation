# Changelog

All notable changes to this project are recorded here.

## [0.2.0] - 2026-08-29

### Added

- Unified five-row Academic Artifact Acceptance Matrix for PPTX, DOCX, XLSX, VSDX, and LaTeX/PDF.
- Windows native Word, Excel, and Visio synthetic acceptance runner with isolated COM, editable
  round-trips, PDF export, Poppler rendering, visual-review ingestion, and relative SHA-256 evidence.
- LaTeX engine discovery/selection, final-log warning classification, PDF compilation evidence,
  and a shared PDF structure/render/visual-QA command.
- Cross-platform path hardening for drive-relative paths, traversal, and network UNC paths.
- Matrix, PDF, LaTeX, capability, schema, and native-runner contract tests plus a public synthetic
  LaTeX fixture.
- Project-level `scripts/recovery_rehearsal.py` and `--recovery-evidence` integration so a clean
  committed checkout can be backed up, restored, and promoted to L6 only after both SHA-256
  manifest comparisons pass.

### Validation boundary

- Native Office and TeX/PDF results are host evidence, not promises made by static repository
  inspection. Recovery is a separately recorded project-level release gate.

## [0.1.0] - 2026-08-29

### Added

- Capability-first artifact routing with target precedence and explicit fallbacks.
- Deterministic status derivation for required checks, warnings, deferred work, and blockers.
- Relative SHA-256 manifests and backup/restore comparison.
- Evidence provenance and artifact-hash validation.
- Read-only capability detection and public-repository security/path scanning.
- Route-specific references, schemas, templates, synthetic fixtures, and self-bootstrapping tests.

### Validation

- Script-level runtime and behavior checks are included in the repository.
- Native acceptance status is environment-specific and must be confirmed in the release evidence.
