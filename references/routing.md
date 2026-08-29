# Routing

Routing answers one question first: which capability matches the requested artifact shape?
Integration names are selected only after the capability is known.

For a PPT request entered as ordinary natural language, the user-level orchestration Skill
`ppt-standard-workflow-skill` converts the source-shape decision into a route record before this
project consumes acceptance evidence. Its main trunk is presentation generation; structured and
image specialists are page-level conditional routes, not competing whole-deck owners.

## Precedence

1. Preserve the user's target format and explicitly requested tool.
2. Preserve structured input when the target can represent it.
3. Prefer a native acceptance route when the user requires editability or native fidelity.
4. Use a fallback only when the primary capability is unavailable, fails, or would cause clear loss.
5. Record the reason, fallback capability, and downstream checks that were repeated.

schemas/route-request.schema.json defines the machine-readable request. The route command
prints a record containing the chosen capability, route steps, target-preservation flag,
structured-source flag, warnings, and blockers.

## Academic paper route

Paper route precedence is explicit user format, official template, explicit delivery constraint,
and then evidence-driven default. A formula-heavy, data-heavy, citation-dense, structurally
complex, or PDF-first paper uses the source-preserving LaTeX route. An explicit DOCX requirement
or Word template uses the native Word route. The paper-standard-workflow-skill records this
decision before Academic Workstation consumes the acceptance evidence.

## Shape examples

| Input shape | Target | Preferred capability |
| --- | --- | --- |
| Structured SVG | Editable PPTX | Structured SVG to presentation |
| Existing PPTX | PPTX | Template-preserving presentation editing |
| CSV or JSON data | XLSX | Spreadsheet generation with structured data |
| DOCX source | DOCX | Document generation and native Word acceptance |
| TeX source | PDF | LaTeX compilation followed by PDF QA |
| Image screenshot | Editable PPTX | Screenshot-to-editable route, with a loss warning |

Rasterization, OCR, or flattening is not a neutral format conversion. It is permitted only
when the user requests it or the target cannot preserve the source shape, and the evidence
must say what was lost.
