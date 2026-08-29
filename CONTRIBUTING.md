# Contributing

## Small, traceable changes

Keep the route, command, data, side-effect, and feedback boundaries visible. Prefer a
small business-named function over a generic technical wrapper. A change should explain
which invariant it protects and which evidence gate proves it.

## Local checks

~~~bash
uv sync
uv run python -m unittest discover -s tests -p 'test_*.py'
uv run python tests/runtime.py
uv run python tests/behavior.py
uv run python scripts/scan_public_repo.py --root . --strict
~~~

Run native acceptance only when the target application is available and the synthetic
pilot can be isolated from user-owned processes. Static or LibreOffice rendering does not
replace the target application's round-trip check.

## Evidence rules

Use relative paths and SHA-256 digests. Label every record with its evidence origin.
Record warnings and deferred checks rather than deleting them from the report. Never add
real credentials, original research data, private absolute paths, or generated lock files
from a user's Office session.

## Pull requests

Describe the route, acceptance level reached, fallback calls, tests, security scan, license
review, and any unrun native gate. Keep the staged file list narrow and inspect the staged
diff before committing. Public release tags must point at a reviewed commit.
