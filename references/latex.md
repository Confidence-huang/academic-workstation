# LaTeX route

LaTeX is a source-preserving route: keep the .tex files, bibliography, figures, and
compile log with the evidence record. Compilation success is L0-L1 evidence; it is not
visual proof.

## Checks

- Compile in a controlled environment with a bounded command and captured stdout/stderr.
- Check page count, equation or bibliography markers, missing-reference warnings, and output hash.
- Render or open every page and inspect margins, overfull boxes, fonts, figures, and labels.
- Keep source assets and the final PDF together in the private evidence record.

Do not silently replace a missing TeX engine with a different document generator. Record the
fallback and its acceptance depth.

## Platform boundary and repair

The route may run Windows TeX Live from WSL when the installed engine is exposed as a .exe.
The compiler converts the WSL output directory to a Windows UNC path for the native process,
while keeping the authoritative source and evidence in the WSL project. This is a recorded
platform fallback, not a silent change of document generator.

If content or layout QA finds a real issue, repair the .tex, bibliography, or source-owned
figure, record source hashes, recompile, and rerun PDF QA. Do not edit the derivative PDF.

## v0.2.0 executable route

Use `scripts/compile_latex.py` to discover the installed engine and prefer `latexmk-xelatex`.
The compiler records the selected command, hashes `compile.log` and the PDF, and classifies the
final TeX log. Undefined references/citations, missing figures/fonts, and fatal errors are hard
failures; overfull and underfull boxes are layout diagnostics. Follow compilation with the
shared `scripts/pdf_qa.py` and one visual observation for every rendered page.
