# Architecture

The v0.2.0 architecture keeps one acceptance vocabulary across five artifact rows: PPTX,
DOCX, XLSX, VSDX, and LaTeX/PDF. PDF is a derivative surface; its QA record is linked back to
the producing source row with `sourceArtifactType`.

The Skill follows a visible data flow:

~~~text
User request → route command → specialist build → structural checks
→ native acceptance → render and visual checks → evidence record → derived status
~~~

The route command decides capability and preserves target intent. Specialist tools own
artifact creation. Check scripts read artifacts and emit structured records. Evidence keeps
origins, relative paths, hashes, and warnings explicit. Status derivation is the only final
decision point.

No script in this repository starts Office, edits a registry, changes a license, changes a
proxy, or mutates a shared Skill. Native pilots belong to an isolated environment-specific
runner and are evidence inputs to this data flow.

## Matrix data flow

~~~text
one artifact evidence set
  ├─ generate / parse
  ├─ native open / roundtrip / export (when applicable)
  ├─ structural QA
  ├─ PDF render + page observations
  ├─ relative artifacts + hashes
  └─ recovery rehearsal
          ↓
scripts/acceptance_matrix.py
          ↓
PPTX | DOCX | XLSX | VSDX | LaTeX/PDF
~~~

The matrix merges only explicit records. A missing row is `UNAVAILABLE`; a missing or unrun
gate is not promoted to `PASS`. LaTeX marks native Office open and roundtrip as
`NOT_APPLICABLE`, while its compiler and PDF QA cover export, structural, visual, and evidence
gates. `scripts/recovery_rehearsal.py` supplies the shared project-level Recovery gate; it is
attached with `acceptance_matrix.py --recovery-evidence` rather than copied into every artifact
record.
