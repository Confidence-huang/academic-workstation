# Presentation route

## Structured-first rule

For SVG, XML, OOXML, native chart data, tables, and editable shapes, route the structured
representation to the presentation specialist. Do not insert a screenshot merely because it
is visually convenient. If the user asks for a static image, record that as an explicit target.

## Minimum acceptance

- Check slide count, page dimensions, text markers, chart/table presence, and shape editability.
- Open the PPTX in an isolated PowerPoint instance for L2.
- Save, close, reopen, and inspect the same markers and object classes for L3.
- Export a PDF and render every page for L4-L5.
- Inspect all pages, not only the title slide; record any small text or clipping warning.

## PDF export fallback

The preferred PowerPoint call is the installed application's full
ExportAsFixedFormat signature:

~~~text
OutputFileName, FixedFormatType, Intent, FrameSlides, HandoutOrder,
OutputType, PrintHiddenSlides, PrintRange, RangeType, SlideShowName,
IncludeDocProperties, KeepIRMSettings, DocStructureTags,
BitmapMissingFonts, UseISO19005_1, ExternalExporter
~~~

The exact COM binding can vary. If the primary call fails, record the exception type and
message, then use an explicit compatible full-argument invocation or SaveAs with the
PowerPoint PDF format. Re-run PDF open, page-count, render, and visual checks after the
fallback. A PDF created by a fallback is still a fallback result; it must not be described
as a primary export.

## Native safety

Use a fresh synthetic presentation containing SYNTHETIC TEST DATA and NOT RESEARCH RESULTS.
Create a separate application instance, set the applicable automation security to its
highest safe setting, avoid task termination, and close only objects created by the pilot.

## Standard natural-language PPT workflow interface

The user-level entry for an ordinary PPT request is the external orchestration Skill
`ppt-standard-workflow-skill`. The user may provide only “帮我做 PPT，按标准流程。”; the
orchestrator records the source-shape decision and keeps the following ownership:

- the presentation artifact generator owns narrative, ordinary content, layout, and deck assembly;
- the structured-page specialist is conditional for data, charts, tables, SVG, and complex connected
  pages; it does not replace the main deck owner;
- the image-reconstruction specialist is conditional for raster, screenshot, flattened, and
  reference-image pages; the original image is retained as provenance;
- every final PPTX enters the native PowerPoint round-trip gate, then this project consumes its
  common evidence shape through `scripts/derive_status.py` and `scripts/pdf_qa.py`;
- an observed defect requires an actual edit followed by a second native round-trip and a second
  page-by-page PDF/visual review; a report-only change is not a repair;
- WSL formal outputs and a Windows-local preview/delivery copy are separate evidence surfaces and
  both hashes are recorded.

This interface is a companion contract, not a copy of the specialist implementations. Its route
record should expose `mainTrunk`, `conditionalRoutes`, `nativeGate`, `qaInterface`, `repairLoop`,
and `previewDelivery`, while the final status still comes from actual evidence.
