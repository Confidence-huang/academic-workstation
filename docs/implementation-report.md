# Implementation report

## Release scope

v0.2.0 extends the v0.1.0 routing and evidence foundation with one executable acceptance
contract for PPTX, DOCX, XLSX, VSDX, and LaTeX/PDF. The repository contains the orchestrator,
schemas, references, templates, tests, and public synthetic fixtures. Private native artifacts,
rendered pages, workstation paths, and visual observations remain outside the repository.

## Implemented

- `scripts/native_acceptance.ps1` creates synthetic Word, Excel, and Visio artifacts in isolated
  COM instances, performs native open/save/reopen checks, exports PDF, renders with Poppler,
  ingests page observations, and records relative SHA-256 evidence without terminating user
  processes.
- `scripts/compile_latex.py` discovers the installed TeX toolchain, prefers `latexmk-xelatex`,
  classifies the final TeX log rather than transient first-pass warnings, and records compiler
  outputs and hashes.
- `scripts/pdf_qa.py` is the shared PDF structure/render/visual-QA stage for Office derivatives
  and LaTeX output. It requires one explicit observation for every rendered page.
- `scripts/acceptance_matrix.py` merges complementary evidence into five stable rows and keeps
  `SUPPORTED`, `TESTED`, `PASS`, `PASS_WITH_WARNING`, `DEFERRED`, `UNAVAILABLE`, `FAIL`,
  `BLOCKED`, and `NOT_RUN` visible.
- `scripts/recovery_rehearsal.py` creates a clean-checkout backup, restores it into an empty
  destination, compares both SHA-256 manifests, and can close the project-level Recovery gate.
- Evidence schemas and validation now cover acceptance gates, fallbacks, visual observations,
  safe relative paths, and network-UNC rejection. Capability detection remains read-only.
- `examples/latex/` supplies a synthetic four-page source with a bibliography, figure, table,
  equation, citation, and cross-references.

## Current acceptance evidence

The following is a private current-run summary, not a claim that a static repository checkout
can substitute for native applications:

| Artifact row | Native/derivative result | Matrix result | Evidence boundary |
| --- | --- | --- | --- |
| PPTX | v0.1.0 pilot reached L5 with the documented PDF fallback | `PASS_WITH_WARNING` | Existing private current-run PowerPoint evidence |
| DOCX | Word 16.0 generated, reopened, round-tripped, exported 3 PDF pages, and passed visual review | `PASS` / `L6` | Private Windows runner plus project recovery gate |
| XLSX | Excel 16.0 generated 3 sheets/25 data rows/formulas and an editable chart, exported the 1-page Dashboard, and passed visual review | `PASS` / `L6` | Private Windows runner plus project recovery gate |
| VSDX | Visio 16.0 preserved 6 labeled shapes and 5 connectors, round-tripped, exported, and passed visual review | `PASS` / `L6` | Private Windows runner plus project recovery gate |
| LaTeX/PDF | TeX Live 2026 `latexmk-xelatex` compiled 4 pages; PDF structure, render, and visual review passed | `PASS` / `L6` | Private Windows compiler/PDF QA plus project recovery gate |

The final aggregate is `PASS_WITH_WARNING` only because the current PPTX evidence records the
known `ExportAsFixedFormat` primary-export failure and uses an explicit PDF fallback; its legacy
record also predates the v0.2.0 gate-map shape. The DOCX, XLSX, VSDX, and LaTeX/PDF rows are
`PASS` at L6 after the project recovery record is attached. The recovery rehearsal used the
committed revision `16e5b5fe2be92308016abaff593448a2dba77ad4`, backed up 80 tracked files, and
passed both source-to-backup and backup-to-restore manifest comparisons.

## Verification commands

Run the Python checks from a WSL-native checkout:

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
uv run python tests/runtime.py
uv run python tests/behavior.py
uv run python scripts/scan_public_repo.py --root . --strict
```

Run the native boundary on Windows with a private output root, inspect every PNG, then rerun
with `-VisualReviewRoot` and `-RecoveryEvidence`. Compile the public LaTeX fixture with
`compile_latex.py`, run `pdf_qa.py`, run `recovery_rehearsal.py` from a clean commit, and finally
merge all JSON records with `acceptance_matrix.py --recovery-evidence`.

## Publication boundary

The v0.1.0 tag and public history are not rewritten. This v0.2.0 work is locally committed
only; no GitHub push, tag, or release is implied by the attached task document.
