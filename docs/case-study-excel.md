# Case study: Excel/XLSX native acceptance

The synthetic workbook has three editable sheets: `Data`, `Analysis`, and `Dashboard`. `Data`
contains 25 rows with text, numeric, date, percentage, and blank cells. `Analysis` keeps
`SUM`, `AVERAGE`, `MIN`, `MAX`, `COUNT`, and `IF` formulas. `Dashboard` contains KPI cells and
an editable native chart with four categories.

The Windows runner recalculates, saves an XLSX roundtrip, reopens it, checks formulas and cached
values, selects only `Dashboard` for PDF export, renders the one-page derivative, and requires
an explicit visual observation. LibreOffice is not used as the final Excel acceptance authority.

The private current run reached L5 with Excel 16.0: three worksheets, formula cache `700`, an
editable chart object, one Dashboard PDF page, and no visual flags.
