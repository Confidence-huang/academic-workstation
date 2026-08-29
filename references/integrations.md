# Integrations and license boundaries

The Skill is capability-first. Integration names are implementation choices behind a route,
not promises that every host has every specialist installed.

## Capability families

| Capability | Possible target application | Acceptance boundary |
| --- | --- | --- |
| Editable presentation generation | PowerPoint specialist | Native PowerPoint round-trip when required |
| Document generation | Word specialist | Native Word open/save/reopen when required |
| Spreadsheet generation | Excel specialist | Native Excel structured-value round-trip when required |
| Editable diagram generation | Visio specialist | Native shape and connector checks when required |
| PDF understanding and rendering | PDF tools | Target PDF reader plus page-by-page visual QA |
| LaTeX compilation | TeX toolchain | Compile log plus rendered-page inspection |

## Audited source boundary

The originating workstation audit identified existing specialist names and historical pilot
records, including presentation, document, spreadsheet, PDF, diagram, and template Skills.
Those records are historical evidence; this repository does not copy their source, assets,
scripts, or private outputs. Recheck the current host before routing.

The source audit recorded MIT attribution for the upstream presentation source used as a
reference and found no need to vendor it here. Any future copied code, asset, font, template,
or example must undergo a fresh license and provenance review before inclusion.
