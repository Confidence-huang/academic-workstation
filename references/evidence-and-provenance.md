# Evidence and provenance

Every evidence record separates the claim from the source that supports it.

## Origins

| Origin | Meaning |
| --- | --- |
| CURRENT_RUN | Observed during this execution on the current host. |
| HISTORICAL_SOURCE | Read from an earlier project record; not rerun now. |
| SYNTHETIC_EXAMPLE | Deliberately generated fixture or pilot data. |
| USER_SUPPLIED | Provided by the user and not independently generated here. |

Use relative artifact paths, byte counts where useful, and lowercase SHA-256 digests.
Sanitize tool versions, user names, absolute roots, credentials, and machine-specific
identifiers before a public report. Keep private evidence outside the public repository.

An evidence item should answer what was checked, how it was checked, which artifact proves
it, where the artifact came from, and what remains unrun or uncertain.
