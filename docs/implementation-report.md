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
| DOCX | Word 16.0 generated, reopened, round-tripped, exported 3 PDF pages, and passed visual review | `PASS_WITH_WARNING` | Private Windows runner; recovery remains separate |
| XLSX | Excel 16.0 generated 3 sheets/25 data rows/formulas and an editable chart, exported the 1-page Dashboard, and passed visual review | `PASS_WITH_WARNING` | Private Windows runner; recovery remains separate |
| VSDX | Visio 16.0 preserved 6 labeled shapes and 5 connectors, round-tripped, exported, and passed visual review | `PASS_WITH_WARNING` | Private Windows runner; recovery remains separate |
| LaTeX/PDF | TeX Live 2026 `latexmk-xelatex` compiled 4 pages; PDF structure, render, and visual review passed | `PASS_WITH_WARNING` | Private Windows compiler/PDF QA; recovery remains separate |

The row warning is intentional: the aggregate matrix does not silently promote a missing
recovery gate, and the legacy PPTX evidence predates the v0.2.0 gate-map shape. The individual
Word, Excel, Visio, and LaTeX/PDF native/derivative gates are complete at L5 in the private
run. L6 requires the release backup/restore and reproducibility record to be attached to the
same matrix decision.

## Verification commands

Run the Python checks from a WSL-native checkout:

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
uv run python tests/runtime.py
uv run python tests/behavior.py
uv run python scripts/scan_public_repo.py --root . --strict
```

Run the native boundary on Windows with a private output root, inspect every PNG, then rerun
with `-VisualReviewRoot`. Compile the public LaTeX fixture with `compile_latex.py`, run
`pdf_qa.py`, and finally merge all JSON records with `acceptance_matrix.py`.

## Publication boundary

The v0.1.0 tag and public history are not rewritten. This v0.2.0 work is locally committed
only; no GitHub push, tag, or release is implied by the attached task document.
