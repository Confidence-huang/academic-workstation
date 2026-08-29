# Academic paper workflow interface

This reference is the shared QA boundary for the companion paper-standard-workflow-skill.
The companion Skill owns natural-language entry and paper-route selection; Academic Workstation
owns evidence schemas, compiler execution, native Word contract linkage, PDF inspection, and
status derivation.

## Ownership and source identity

| Layer | Contract |
| --- | --- |
| Natural-language entry | paper-standard-workflow-skill |
| LaTeX source | one authoritative .tex source plus bibliography and source-owned figures |
| Word source | one authoritative .docx source and its source-owned assets |
| PDF | derivative acceptance surface, never the editable source |
| Content QA | citation, formula, figure, table, data traceability, and synthetic disclosure |
| Format QA | compile or native Word contract, PDF structure, full-page render, and visual review |

Route precedence is explicit user format, official template, explicit delivery constraint, and
then evidence-driven default. Formula-heavy, data-heavy, structurally complex, citation-dense,
or PDF-first material defaults to LaTeX. An explicit DOCX requirement or Word template defaults
to Word.

## LaTeX interface

Use scripts/compile_latex.py. The command prefers latexmk-xelatex, discovers Windows .exe
engines when they are visible from WSL, translates WSL output paths for a Windows TeX process,
preserves compile logs, and classifies unresolved references, citations, figures, fonts, fatal
errors, and overfull boxes. Follow it with scripts/pdf_qa.py and one observation per rendered
page.

## Word interface

Use scripts/native_acceptance.ps1 for the native Word contract. The route must keep the DOCX
source authoritative, stage a Windows-local copy before native acceptance, use an independent
COM instance, save, close, reopen, inspect key content, export PDF, and then run the shared PDF
gates. A route-contract test may prove linkage without generating a second full paper.

## Repair and delivery

Content QA and format QA remain separate. When a real issue is observed, repair only the
authoritative source, record before/after hashes and attempt count, repeat compile or native
round-trip, then repeat PDF structural and page-by-page visual QA. Never patch the final PDF.

Formal source and evidence stay in the WSL project work or outputs directory. A Windows-local
preview or delivery copy is created for native applications and direct user preview; it is not
the source of truth. Record SHA-256 for both sides and preserve the copy relationship in evidence.

Synthetic pilots must carry SYNTHETIC ACADEMIC WORKFLOW TEST and NOT RESEARCH RESULTS markers,
must not invent research facts or citations, and must keep local fixtures distinguishable from
verified external literature.
