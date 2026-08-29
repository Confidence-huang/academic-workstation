---
name: academic-workstation
description: Orchestrate research and Office artifact workflows when a task spans specialist tools, native round-trips, rendering, evidence, or controlled Skill lifecycle work; do not use for ordinary text-only answers or simple file reading.
---

# Academic Workstation

The current public release line is v0.2.0. The acceptance contract is unified by
[references/acceptance-matrix.md](references/acceptance-matrix.md): PPTX, DOCX, XLSX, VSDX,
and LaTeX/PDF share the same gate vocabulary while keeping native applicability explicit.

Use this Skill when a research or Office artifact crosses a specialist tool boundary and the
deliverable needs more than file creation: route selection, structural checks, native round-trip,
rendering, visual QA, evidence, or controlled Skill lifecycle work.

This project is an orchestrator. Specialist tools create or edit the artifact; this Skill selects,
composes, validates, evidences, and decides whether it is ready to deliver. It does not replace
PowerPoint, Word, Excel, PDF, Visio, or LaTeX tools and does not copy their implementations.

## Two operating modes

- **Artifact Orchestration Mode** handles research and Office artifacts. Read the relevant route
  and acceptance references only, then follow `Route → Build → Structural QA → Native Roundtrip →
  Export/Render → Visual QA → Evidence → Final Status`.
- **Skill Lifecycle Mode** is used only when the user asks to install, update, pilot, promote,
  back up, restore, or roll back another Skill. Read [references/skill-lifecycle.md](references/skill-lifecycle.md)
  and do not mutate an existing third-party Skill without explicit scope and a recovery point.

## Shared invariants

1. Route by capability and artifact shape before choosing an integration name. Use
   [references/routing.md](references/routing.md); use [scripts/route_artifact.py](scripts/route_artifact.py)
   for a deterministic route record when a machine-readable decision is useful.
2. A user-specified format or tool takes precedence. Use a fallback only when the requested path is
   unavailable, fails, or would cause clear loss; record the reason and repeat all applicable QA.
3. Keep structured SVG/XML/PPTX/native charts/structured data structured. Do not rasterize or OCR
   them just to fit a tool. Read the route reference for the narrow exceptions.
4. Treat generation as L0 only. Select the acceptance depth from
   [references/acceptance-levels.md](references/acceptance-levels.md), and never claim native
   levels without the target application or authoritative tool evidence.
5. Use synthetic data for pilots and label it `SYNTHETIC TEST DATA` and `NOT RESEARCH RESULTS`.
   Keep private source evidence, absolute paths, credentials, and original artifacts outside a
   public repository.
6. Fallbacks are explicit records, not silent retries. Read
   [references/fallback-and-status.md](references/fallback-and-status.md) before choosing one.
7. Derive the final state from checks with [scripts/derive_status.py](scripts/derive_status.py).
   `NOT_RUN` and `DEFERRED` never become `PASS`; unresolved external work is accounted for.
8. Before public delivery, validate evidence, hash artifacts, scan tracked files, review the Git
   index and release archive, complete the license gate, and run `scripts/recovery_rehearsal.py`
   for the committed checkout.
9. Use [scripts/acceptance_matrix.py](scripts/acceptance_matrix.py) to aggregate stage evidence;
   pass its `--recovery-evidence` record when the project-level backup/restore rehearsal passes;
   a PDF QA record linked with `sourceArtifactType` completes the LaTeX/PDF row instead of
   creating a second artifact identity.

## Route-specific references

- PPTX or presentation planning: read [references/presentations.md](references/presentations.md)
  and the acceptance levels.
- DOCX: read [references/documents.md](references/documents.md).
- XLSX: read [references/spreadsheets.md](references/spreadsheets.md).
- PDF or rendered pages: read [references/pdf-and-visual-qa.md](references/pdf-and-visual-qa.md).
- Editable diagrams: read [references/diagrams-and-visio.md](references/diagrams-and-visio.md).
- LaTeX source: read [references/latex.md](references/latex.md).
- Unified matrix: read [references/acceptance-matrix.md](references/acceptance-matrix.md).
- Evidence or provenance: read [references/evidence-and-provenance.md](references/evidence-and-provenance.md).
- Windows/WSL/Linux boundaries: read [references/platform-support.md](references/platform-support.md).
- Discovered integrations and license boundaries: read [references/integrations.md](references/integrations.md).

## Final delivery

Return the artifact paths, route, acceptance level actually reached, fallback count, evidence path,
derived status, warnings, deferred items, blockers, and the exact next action when one is needed.
Do not call a file complete merely because it exists or opens in a non-target application.
