# Architecture

The Skill follows a visible data flow:

~~~text
User request → route command → specialist build → structural checks
→ native acceptance → render and visual checks → evidence record → derived status
~~~

The route command decides capability and preserves target intent. Specialist tools own
artifact creation. Check scripts read artifacts and emit structured records. Evidence keeps
origins, relative paths, hashes, and warnings explicit. Status derivation is the only final
decision point.

No script in this repository starts Office, edits a registry, changes a license, changes a
proxy, or mutates a shared Skill. Native pilots belong to an isolated environment-specific
runner and are evidence inputs to this data flow.
