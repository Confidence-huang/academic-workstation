# PDF and visual QA

PDF is an output and an evidence surface, not proof that its source remained editable.
Check it with the requested PDF application when native acceptance is in scope, and use a
deterministic renderer for page-by-page inspection.

## Structural checks

- Verify the file opens, page count is correct, and every page has non-zero geometry.
- Check marker text, text extraction, embedded fonts or images where relevant, and page order.
- Hash the final PDF and the rendered image set with relative paths.

## Visual checks

Inspect every rendered page for clipping, overlap, unexpected blank space, font substitution,
small text, axis or label loss, contrast, and page-size drift. A pixel diff can identify a
change but cannot decide whether the change is acceptable; the human-visible report is
still the authority for visual readability.

When a target PDF reader is unavailable, report native acceptance as NOT_RUN or BLOCKED.
Do not substitute a different reader silently.
