# Reproduction Milestones

**Current: core_claim**

<!-- Milestone levels (update "Current" above as you progress):
  none             — just started, no meaningful progress yet
  method_runs      — the paper's method executes end-to-end without errors
  core_claim       — minimum experiment supports the paper's central claim
  core_claim_plus  — core claim reproduced on additional settings
  secondary_claims — secondary results or contributions reproduced
  majority         — more than half of reported results reproduced
  near_complete    — most results reproduced, only minor gaps remain
  full             — all reported results reproduced
-->

## Progress Log

### [2026-06-02 17:55] - method_runs
- Read the HAGeo paper and identified the core method: DDAR theorem proving followed by CPU-only heuristic auxiliary construction attempts.
- Verified the released HAGeo GitHub repository currently lacks solver source code; it contains only README/assets, so the reproduction vendors AlphaGeometry's public DDAR engine and implements HAGeo-style heuristic auxiliary search around it.
- Downloaded the public HAGeo-409 parquet benchmark and prepared fixed JSONL benchmark slices.
- Implemented DDAR-only baseline, HAGeo-style method runner, method-agnostic evaluator, scripts, and scoring reference.
- Local smoke run solved `auxiliary_core` with HAGeo-style auxiliary construction while DDAR-only failed; `python validate.py --compare` passes.

### [2026-06-02 17:59] - core_claim
- Compute-node CPU smoke job `9b3c9005-1b5` exited successfully.
- The packaged environment reproduced the central auxiliary-construction claim on `auxiliary_core`: DDAR-only solved 0/1, while the HAGeo-style auxiliary construction runner solved 1/1 using one constructed point.
- `python validate.py --compare` passes after the compute-node run, and `eval/` remains independent of `method/`.

### [2026-06-02 18:25] - core_claim
- Cancelled the first `hageo409_small` expansion job after DDAR-only completed but HAGeo-style method output remained empty.
- Added a hard wall-clock timeout around every DDAR invocation and row-level progress logging, then bounded the HAGeo-409 retry attempts.

### [2026-06-02 18:38] - core_claim
- Compute-node job `2dffc44e-9ee` completed `hageo409_small` without hanging.
- DDAR-only and the bounded HAGeo-style method both solved 2/12 on this slice, so `core_claim_plus` is not yet met.
- Improved auxiliary candidate generation to avoid predicate tokens and interleave multiple HAGeo construction categories before submitting another bounded expansion attempt.

## Stop Justification
- Not stopped; submitting a CPU job to expand coverage to the prepared `hageo409_small` slice.
