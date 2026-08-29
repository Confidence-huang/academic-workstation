# Case study: LaTeX/PDF acceptance

`examples/latex/` is a public synthetic fixture containing `main.tex`, `references.bib`, and
`figure.tex`. The source includes a title, abstract, sections, equation, table, figure, BibTeX
citation, labels, cross-references, and four pages of content.

`scripts/compile_latex.py` discovers `latexmk`, `tectonic`, `xelatex`, `lualatex`, and
`pdflatex`, prefers `latexmk-xelatex`, captures the command and log, and classifies the final
TeX log so first-pass unresolved references do not become false failures. It treats undefined
references/citations, missing figures/fonts, and fatal errors as hard failures; overfull and
underfull boxes remain visible as layout diagnostics.

`scripts/pdf_qa.py` then checks PDF structure and geometry, renders every page with Poppler, and
requires one visual observation per page. The private current run used TeX Live 2026
`latexmk-xelatex`, produced 4 pages, and passed structure, rendering, and visual review.
With the project recovery record attached, the matrix row closes at L6.
