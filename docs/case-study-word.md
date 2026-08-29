# Case study: Word/DOCX native acceptance

The v0.2.0 Word pilot uses synthetic English text, a table, an embedded marker image, headers,
footers, and explicit page breaks. It exercises the editable DOCX rather than treating a PDF as
the source.

The Windows runner performs this chain:

```text
create DOCX → Word open → SaveAs2 roundtrip → reopen and inspect
→ Word PDF export → pdfinfo → pdftoppm → page observations → hashes
```

The private current run reached L5 with Word 16.0: 3 pages, 1 table, 1 embedded picture, a
successful roundtrip, PDF export, and a review record for every rendered page. No user document
or existing Word process is part of the public fixture. With the project recovery record
attached, the matrix row closes at L6.
