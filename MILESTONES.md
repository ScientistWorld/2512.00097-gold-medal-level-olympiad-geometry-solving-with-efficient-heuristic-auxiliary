# Reproduction Milestones

**Current: method_runs**

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

## Stop Justification
- Not stopped; submitting a CPU job to verify the packaged runnable environment.
