# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-02 20:55] - none
- Re-audited the existing implementation after subagent review.
- Previous `core_claim` claim was withdrawn at that time because the prior runner used syntactic auxiliary enumeration rather than HAGeo's numerically driven heuristic.

### [2026-06-02 21:40] - core_claim
- Continuing-agent audit found the same main gaps: scoring covered only a smoke target, the random auxiliary baseline was missing, and output validation was too permissive.
- Added the paper's random auxiliary-construction baseline for scaled HAGeo-409 evaluation.
- Added HAGeo's random-construction category after the numerically favorable heuristic categories.
- Hardened `eval/` to validate problem coverage and score both `auxiliary_core` and `hageo409_scaled`.
- Submitting a CPU test job to verify the patched method and determine whether `core_claim_plus` is supported.
