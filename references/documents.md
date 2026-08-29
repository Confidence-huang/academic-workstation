# Document route

For DOCX work, keep the document model and source assets available. Structural parsing can
check headings, tables, fields, relationships, and embedded media, but it cannot prove Word
rendering or save behavior.

## Native Word route

1. Build a synthetic or authorized artifact in a staging directory.
2. Open it in an isolated Word instance without closing user-owned instances.
3. Inspect key paragraphs, tables, fields, and page-related content.
4. Save a copy to a local staging path when a network or WSL path causes Protected View or
   SaveCopyAs problems.
5. Reopen the staged copy, record the actual format, and repeat the content checks.

If SaveCopyAs rejects the destination, record the exact error and use a local staging copy
plus the installed SaveAs2 format constant. Never treat a compatibility renderer as native
Word acceptance.
