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
