# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-06-02 00:00] - core_claim_plus
- Audited the existing reproduction code and verified it implements a DDAR prover plus HAGeo-style auxiliary construction search, not a generic surrogate.
- Verified `eval/` remains independent of `method/` and reads solver output artifacts from `outputs/*.jsonl`.
- Ran `python validate.py --compare`; scoring and import-separation checks pass.
- Restored `core_claim_plus` based on the existing compute-node result: on `hageo409_small`, DDAR solved 2/12 and the HAGeo-style method solved 3/12.

## Stop Justification
- Completed at milestone `core_claim_plus`.
