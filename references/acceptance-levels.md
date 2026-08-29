# Acceptance levels

Use the shallowest level that satisfies the request, but never report a deeper level without
the corresponding evidence.

| Level | Gate | Evidence |
| --- | --- | --- |
| L0 | Generated | Artifact exists and the producing command returned successfully. |
| L1 | Structural QA | Format parse, required fields, object counts, and source-preservation checks. |
| L2 | Native Open | The target application opens the artifact in an isolated instance. |
| L3 | Native Roundtrip | Open, save, close, reopen, and inspect key content in the target application. |
| L4 | Native Export | Export from the target application with the actual call and output checked. |
| L5 | Render and Visual QA | Render every page/slide and inspect geometry, clipping, markers, and readability. |
| L6 | Evidence Closure | Relative artifacts, hashes, provenance, status derivation, security, license, and release review. |

NOT_RUN, DEFERRED, and BLOCKED are evidence states, not hidden passes. A required unrun
gate makes the derived final status fail; an external blocker produces BLOCKED.
