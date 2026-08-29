# Skill lifecycle

This Skill can coordinate lifecycle work, but it does not silently mutate an existing
third-party Skill.

## Lifecycle gates

~~~text
Discover → Source and license audit → Stage → Static verify → Security scan
→ Synthetic pilot → Native verify → Backup → Promote → Post-promote verify → Restore rehearsal
~~~

Use a complete source repository when long-term review, references, history, submodules, or
shared assets matter. Use a package only when the entrypoint is self-contained and its
provenance is adequate. Keep source, staging, and active roots distinct.

## Recovery

Before any authorized overwrite or promotion, create a manifest with relative paths and
SHA-256 hashes. A restore rehearsal must compare missing, unexpected, link, size, and hash
differences. A clean comparison is evidence of byte equivalence, not evidence that an
upstream source is trustworthy.

For this repository's build, the new Skill is verified in isolation. Existing shared Skills
and global configuration are outside the mutation scope. If an external manager is used,
run its preview/read-only checks first, then target only this staged Skill.
