# Security policy

## Scope

This repository contains orchestration scripts, schemas, documentation, and synthetic
fixtures. It must not contain credentials, private workstation paths, original research
artifacts, or native application lock files.

The public release excludes local acceptance bundles and specialist implementation sources. Use
relative paths or placeholders in reports and issue examples; do not submit a local profile or
private native-session output.

## Reporting

Please report a suspected vulnerability privately through the repository's GitHub Security
Advisory workflow. Do not open a public issue containing a token, private artifact, or
reproduction data that you are not authorized to disclose.

## Maintainer response

Reports are triaged against the publication scanner, dependency state, path-handling rules,
and native-process boundary. A fix should include a regression test and a release-note
entry when the issue affects users of a published version.

## Safe operation

Capability detection is read-only. Native pilots must use synthetic data, isolated
application instances, bounded timeouts, and explicit cleanup of only the process created
by the pilot. The Skill does not authorize credential entry, licensing changes, registry
changes, system security changes, or destructive artifact operations.
