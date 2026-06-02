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

### [2026-06-02 22:10] - core_claim
- CPU job `ba58a10a-3a5` failed during the first intermediate evaluation because stale 12-problem HAGeo-409 outputs did not match the freshly prepared 4-problem benchmark.
- Fixed the runner scripts so coordinated reproduction disables intermediate evaluation, removes stale artifacts, regenerates all outputs, and then runs one final strict evaluation.

### [2026-06-02 22:35] - core_claim
- CPU job `e113a384-f00` completed end-to-end and wrote `scoring/scores.json`.
- `auxiliary_core` remains reproduced: DDAR solved 0/1 while the HAGeo-style auxiliary search solved 1/1 without neural inference.
- The first-four HAGeo-409 scaled slice did not support `core_claim_plus` because both random auxiliary search and HAGeo solved 0/4.
- Updated benchmark preparation to use a reproducible low-difficulty HAGeo-409 slice and increased the CPU-scaled budget for the next run.
