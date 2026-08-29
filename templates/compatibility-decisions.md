# Compatibility decisions

## Decision record

| Primary path | Observed result | Fallback | Repeated checks | Status |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Rules

Do not replace a structured source with a raster image without a stated loss decision.
Do not call a compatibility renderer native acceptance. Preserve the original error class
and message in private evidence, then publish only a sanitized summary.
