# Editable diagram route

Route structured diagram sources to an editable diagram specialist. Preserve native shapes,
connectors, labels, and relationships. A flattened PNG is only an explicitly requested
static deliverable.

## Visio acceptance

- Open the VSDX in an isolated Visio instance.
- Count key shapes, connectors, and text-bearing objects.
- Save and reopen the document, then recheck editability and relationships.
- Render a preview only as a visual supplement; it cannot replace the editable source.

If Visio or a commercial license is unavailable, mark the native gate NOT_RUN or BLOCKED
with the reason. Do not claim acceptance from a file extension or a static XML inspection.

## v0.2.0 synthetic pilot

`scripts/native_acceptance.ps1 -Artifact visio` creates six labeled shapes and five arrowed
connectors, saves VSDX, reopens it, counts `OneD` connectors and text objects, exports PDF,
renders a preview, and requires `visio.json` page observations. COM API differences are
recorded as explicit fallbacks; the pilot never flattens a diagram to make a structural check
look successful.
