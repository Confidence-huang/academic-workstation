# Academic Artifact Acceptance Matrix

v0.2.0 uses one matrix for five artifact rows. The source format remains the identity of the
row; a PDF is a derivative QA surface and is attached to its source row with
`sourceArtifactType`.

| Artifact | Generate | Parse | Native Open | Roundtrip | Export | Structural QA | Visual QA | Evidence | Recovery |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PPTX | required | required | required | required | required | required | required | required | required |
| DOCX | required | required | required | required | required | required | required | required | required |
| XLSX | required | required | required | required | required | required | required | required | required |
| VSDX | required | required | required | required | required | required | required | required | required |
| LaTeX/PDF | required | required | N/A | N/A | required | required | required | required | required |

The machine-readable implementation is `schemas/acceptance-matrix.schema.json`; generate it
from private evidence with:

```bash
python scripts/acceptance_matrix.py \
  --evidence-dir private-evidence \
  --recovery-evidence private-evidence/recovery.json \
  --output private-evidence/acceptance-matrix.json
```

Create `private-evidence/recovery.json` first with the project-level rehearsal. It must back up
a clean committed checkout to a new E: drive destination, restore it into an empty destination,
and pass both manifest comparisons:

```bash
python scripts/recovery_rehearsal.py \
  --source-root . \
  --backup-root /mnt/e/CodexBackups/academic-workstation/<timestamp> \
  --restore-root private-recovery/<timestamp> \
  --output private-evidence/recovery.json
```

## Gate meaning

- `Generate` proves that the producing command created the requested source artifact.
- `Parse` checks format structure and source-preservation markers without claiming native behavior.
- `Native Open` proves that the requested native application opened an isolated artifact.
- `Roundtrip` proves open, save, close, reopen, and key-structure inspection in that application.
- `Export` proves a native derivative export, usually PDF, with an explicit fallback if needed.
- `Structural QA` checks object counts, formulas, connectors, references, page count, and related
  format-specific invariants.
- `Visual QA` requires successful rendering and one observation for every page or slide.
- `Evidence` requires relative paths, hashes, provenance, and deterministic status derivation.
- `Recovery` requires the separately recorded backup/restore and reproducibility rehearsal.

LaTeX does not use Microsoft Office open or roundtrip. Its equivalent chain is source → TeX
compile → PDF → `pdfinfo`/`pdftoppm` → page observations → evidence. A standalone PDF record
or a PDF record linked to LaTeX is merged into the LaTeX/PDF row rather than creating a second
row.

## Status rules

`SUPPORTED` describes a declared route; `TESTED` means an evidence record exists. The row status
must remain one of `PASS`, `PASS_WITH_WARNING`, `DEFERRED`, `UNAVAILABLE`, `FAIL`, or `BLOCKED`.
Gate values additionally preserve `NOT_RUN` and `NOT_APPLICABLE`. A missing or unrun required
gate cannot be silently promoted to `PASS`; an explicit fallback keeps the result at least
`PASS_WITH_WARNING` even when downstream QA succeeds.

## Native boundary

The public Windows runner is `scripts/native_acceptance.ps1`. It creates synthetic Word, Excel,
and Visio files, uses fresh COM instances, records existing and residual process IDs, never
terminates a process, and never changes registry, licensing, or activation state. Supply the
verified recovery JSON with `-RecoveryEvidence` to close the native record's L6 gate. The
script is not a replacement for an authorized real document acceptance run. User-owned Office
instances must remain outside the pilot.

The LaTeX compiler and shared PDF QA are standard-library Python commands. Capability detection
is read-only and an executable path does not prove that a license, native roundtrip, or visual
acceptance is usable.
