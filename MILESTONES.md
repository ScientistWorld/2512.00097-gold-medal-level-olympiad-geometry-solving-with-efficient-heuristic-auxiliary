# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-02 00:00] - core_claim
- Audited the existing reproduction code and verified it implements a DDAR prover plus HAGeo-style auxiliary construction search, not a generic surrogate.
- Verified `eval/` remains independent of `method/` and reads solver output artifacts from `outputs/*.jsonl`.
- Ran `python validate.py --compare`; scoring and import-separation checks pass.
- Fixed scoring so the formal benchmark only contains the validated `auxiliary_core` result instead of comparing a scaled HAGeo-409 slice against full-paper HAGeo-409 reference numbers.
- Kept the small HAGeo-409 run documented as exploratory evidence, but did not claim it as a validated milestone.

## Stop Justification
- Completed at milestone `core_claim`.
