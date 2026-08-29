# Case study: Visio/VSDX native acceptance

The synthetic Visio document contains six labeled editable shapes using the native rectangle
and oval APIs, plus five arrowed connectors. The pilot deliberately records the API limitation
that this Office build does not expose `DrawRoundedRectangle`; the sixth shape remains an
editable rectangle rather than a fake or flattened substitute.

The Windows runner creates VSDX, reopens and counts pages/shapes/connectors/text, saves a
roundtrip, exports PDF, emits a PNG preview, runs shared PDF QA, and requires a page review.
The private current run reached L5 with Visio 16.0: 11 total shapes, 5 connectors, 6 text
objects, one rendered page, and no visual flags.
