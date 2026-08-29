# Spreadsheet route

Keep data tables, formulas, number formats, and chart series structured. A rendered image
may illustrate the result but is not a spreadsheet substitute.

## Checks

- Validate workbook and worksheet names, dimensions, formulas, cached values, and chart data.
- Open in an isolated Excel instance and inspect the key cells and objects.
- Save, close, reopen, and compare the same structured values.
- Render or export only after the round-trip succeeds, then inspect the visible result.

Synthetic spreadsheet pilots must label their data and avoid implying that generated numbers
are research observations. Record calculation mode, locale-sensitive formulas, and any
unsupported feature as a warning or blocker.

## v0.2.0 synthetic pilot

The Windows runner creates `Data`, `Analysis`, and `Dashboard` sheets. The fixture has 25 data
rows, numeric/date/percentage/blank values, `SUM`, `AVERAGE`, `MIN`, `MAX`, `COUNT`, and `IF`
formulas, plus an editable native chart. It saves and reopens a roundtrip workbook, selects only
`Dashboard` for the PDF derivative, removes stale render pages before counting, and requires
an explicit page review. A chart fallback may preserve editable native shapes, but it never
claims the native chart gate passed.
