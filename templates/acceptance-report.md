# Acceptance report

| Gate | Status | Evidence path | Notes |
| --- | --- | --- | --- |
| L0 Generated |  |  |  |
| L1 Structural QA |  |  |  |
| L2 Native Open |  |  |  |
| L3 Native Roundtrip |  |  |  |
| L4 Native Export |  |  |  |
| L5 Render and Visual QA |  |  |  |
| L6 Evidence Closure |  |  |  |

## Required notes

- Keep NOT_RUN, NOT_APPLICABLE, and BLOCKED explicit.
- State whether the artifact is synthetic, historical, user supplied, or current-run evidence.
- State every fallback and whether downstream QA was repeated.
- For the unified v0.2.0 report, attach the five-row matrix and identify any PDF record's
  `sourceArtifactType`; do not list a derivative PDF as a second source artifact.
- Attach the project-level `recovery_rehearsal.py` JSON when Recovery is `PASS`; otherwise leave
  the gate as `NOT_RUN` or `FAIL` and keep the row warning visible.
