# Synthetic example

`synthetic-result.txt` is a tiny non-research fixture used to exercise relative hashing,
evidence validation, and the status gate. It deliberately contains the marker
`SYNTHETIC TEST DATA` and must never be presented as a research result.

The example is not a native Office acceptance record. Native application acceptance is
performed against a fresh, isolated synthetic artifact and is recorded separately from
historical source evidence.

`latex/` is the public LaTeX/PDF fixture. It is synthetic and includes source-level figure,
table, equation, citation, and cross-reference content for the v0.2.0 compiler and PDF QA
chain; generated PDF and review files belong in private evidence directories.
