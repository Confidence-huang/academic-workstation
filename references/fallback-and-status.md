# Fallbacks and status

Fallbacks follow a visible state transition:

~~~text
Primary unavailable or failed → reason recorded → compatible fallback selected → all applicable QA repeated → status derived
~~~

Use the following status vocabulary:

- PASS means all required checks passed and no warning or deferred item remains.
- PASS_WITH_WARNING means no required failure remains, but a warning, deferred item, or
  optional unrun check is still visible.
- FAIL means a required check failed or was not run.
- BLOCKED means an external condition prevents the required action.
- NOT_RUN and DEFERRED must remain visible in the evidence.

The producer's declared status is not authoritative. Run derive_status.py over the checks,
warnings, deferred items, and blockers. Run validate_evidence.py to reject a declared status
that disagrees with derivation.
