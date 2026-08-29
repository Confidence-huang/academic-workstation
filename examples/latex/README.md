# Synthetic LaTeX fixture

This directory is a public, non-research fixture for the LaTeX/PDF acceptance route. It
contains a bibliography entry, an input figure, a table, an equation, citations, labels, and
explicit page breaks so the compiler and PDF QA stages exercise the same evidence gates used by
the Office runners.

Run it from the repository root with an installed TeX engine and Poppler:

```bash
python scripts/compile_latex.py \
  --source examples/latex/main.tex \
  --output-dir private-evidence/latex \
  --output private-evidence/latex-evidence.json
python scripts/pdf_qa.py \
  --pdf private-evidence/latex/main.pdf \
  --root private-evidence/latex \
  --visual-review private-evidence/latex-visual-review.json \
  --source-artifact-type latex \
  --output private-evidence/latex-pdf-qa.json
```

The fixture is synthetic and must not be presented as research evidence.
