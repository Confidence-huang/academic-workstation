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
