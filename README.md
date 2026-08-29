# Academic Workstation

> An evidence-first orchestration skill for routing, generating, natively validating, visually inspecting, and safely delivering research and Office artifacts.

Academic Workstation coordinates specialist tools around a research or Office deliverable.
It makes the artifact shape, requested target, acceptance depth, fallback reason, provenance,
and final status explicit. It is an orchestrator, not a replacement for PowerPoint, Word,
Excel, PDF, Visio, or LaTeX tooling.

## The operating flow

~~~text
Route → Build → Structural QA → Native Roundtrip → Export/Render → Visual QA → Evidence → Final Status
~~~

Generation is L0. A file is not treated as deliverable evidence until the applicable
structural, native, render, visual, and evidence gates have been run or explicitly marked
NOT_RUN, NOT_APPLICABLE, or BLOCKED.

## What it protects

- The user's requested format and tool take precedence.
- Structured SVG, XML, OOXML, charts, tables, and data remain structured whenever the target supports them.
- Fallbacks are explicit and require repeatable downstream QA.
- Native acceptance uses isolated synthetic artifacts and must not disturb user-owned application processes.
- Evidence uses CURRENT_RUN, HISTORICAL_SOURCE, SYNTHETIC_EXAMPLE, or USER_SUPPLIED provenance.
- NOT_RUN and DEFERRED cannot be silently promoted to PASS.
- Public files contain relative evidence paths, sanitized tool names, and no credentials or private workstation roots.

## Quick start

Run these commands from the repository root. The scripts use only the Python standard
library and can also be invoked through uv run python.

~~~bash
python scripts/route_artifact.py --request path/to/route-request.json
python scripts/derive_status.py --input path/to/evidence.json
python scripts/validate_evidence.py --input path/to/evidence.json --root path/to/artifacts
python scripts/hash_artifacts.py --root path/to/artifacts --output path/to/manifest.json
python scripts/compare_manifests.py --expected path/to/manifest.json --actual path/to/restored.json
python tests/runtime.py
python tests/behavior.py
python -m unittest discover -s tests -p 'test_*.py'
python scripts/scan_public_repo.py --root . --strict
~~~

The capability detector reports conservative signals without launching native applications.
Its output is a discovery hint, never native acceptance evidence.

## Acceptance vocabulary

| Status | Meaning |
| --- | --- |
| PASS | Required checks passed and no open warning/deferred item remains. |
| PASS_WITH_WARNING | No required failure remains, but a warning, deferred item, or unrun optional check remains. |
| FAIL | A required check failed or was not run. |
| BLOCKED | An external blocker prevents the required action. |
| NOT_RUN | A check was not executed; it is not a pass. |
| NOT_APPLICABLE | The check is outside the artifact's accepted scope. |

## Repository map

- SKILL.md — invocation boundary and orchestration contract.
- agents/openai.yaml — Codex display metadata and default prompt.
- scripts/ — deterministic routing, status, hashing, evidence, capability, and publication gates.
- schemas/ — machine-readable request, status, evidence, manifest, and lifecycle shapes.
- references/ — route-specific acceptance and platform rules.
- templates/ — evidence reports that keep claims, artifacts, and provenance separate.
- examples/ — non-research fixtures only.
- tests/ — self-bootstrapping runtime, behavior, unit, security, and restore checks.

## Native application boundary

Native PowerPoint, Word, Excel, Visio, PDF reader, and TeX checks are environment-specific.
The Skill may orchestrate them when available, but it never claims native acceptance from a
static parse, a non-target renderer, or an application path alone. Use the route-specific
references before running a pilot and record the exact fallback if the primary export call
fails.

## Security and licensing

Run the publication scanner and review the license attribution record before release.
This repository contains original orchestration code and synthetic fixtures; it does not
vendor specialist Skill implementations or private source artifacts. See SECURITY.md,
references/integrations.md, and references/evidence-and-provenance.md.

## Development

The project targets Python 3.10 or newer. A normal development loop is:

~~~bash
uv sync
uv run python -m unittest discover -s tests -p 'test_*.py'
uv run python scripts/scan_public_repo.py --root . --strict
~~~

See CONTRIBUTING.md for the publication gate and CHANGELOG.md for release history.
