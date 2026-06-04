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

### [2026-06-02 22:50] - core_claim
- CPU job `09e02880-313` failed during random auxiliary candidate generation on a HAGeo-409 problem with a `cyclic` goal.
- Fixed candidate fallback generation to ignore theorem goals and build only the construction graph with a dummy goal.
- Retained `core_claim`; the difficulty-sorted HAGeo-409 retry still needs a clean run before any higher milestone can be claimed.

### [2026-06-02 23:15] - core_claim
- CPU job `675c93ff-642` completed successfully on the six easiest HAGeo-409 problems.
- HAGeo and random auxiliary search both solved 3/6 at K=48, so no higher milestone is claimed.
- Updated HAGeo's attempt schedule to interleave ranked heuristic candidates with shuffled exploration and expanded the next fixed HAGeo-409 slice to 12 problems.

### [2026-06-02 23:45] - core_claim
- CPU job `4cb60e78-0c8` completed successfully on the 12 easiest HAGeo-409 problems.
- HAGeo and random auxiliary search both solved 8/12 at K=48, so no higher milestone is claimed.
- Increased the scaled protocol to N=2 construction rounds for the next run, closer to the paper's N=6 multi-round search while keeping random and HAGeo matched.

### [2026-06-02 23:55] - core_claim
- CPU job `4db0ca3b-381` completed successfully with N=2, but random solved 9/12 while HAGeo solved 6/12.
- Found and fixed a multi-round implementation issue: DDAR was checked only after all auxiliaries in an attempt, rather than after each added auxiliary.
- Retained `core_claim`; the corrected iterative N=2 protocol needs a clean run before any higher milestone can be claimed.

### [2026-06-02 22:28] - core_claim
- CPU job `036b6af6-cfc` completed successfully after iterative N=2 checking was fixed.
- The corrected run solved `auxiliary_core`, and HAGeo tied the random auxiliary baseline at 8/12 on the scaled HAGeo-409 slice.
- Added the paper's identical-point auxiliary category and fixed HAGeo's N=2 attempt indexing so the first round covers the full declared K=48 candidate budget.

### [2026-06-02 23:10] - core_claim
- CPU job `49edf3e0-664` was cancelled during the HAGeo phase after no progress beyond problem 2 for roughly twenty minutes.
- Diagnosed the stall as unbounded identical-point candidate enumeration during HAGeo's second-round candidate regeneration.
- Bounded identical-point enumeration and added hard timeouts around HAGeo candidate generation before retrying the same scaled benchmark.

### [2026-06-03 00:07] - core_claim
- CPU job `299ca567-06f` completed successfully with bounded identical-point generation and candidate-generation timeouts.
- `auxiliary_core` still supports the core claim, but scaled HAGeo-409 did not support `core_claim_plus`: random auxiliary search solved 10/12 while HAGeo solved 8/12.
- Fixed two-round auxiliary insertion so generated point names are fresh for both HAGeo and random, and so HAGeo falls back to its initial heuristic pool when second-round candidate regeneration is unavailable.

### [2026-06-03 00:35] - core_claim
- CPU job `1568a310-592` completed successfully with fresh auxiliary names, second-round fallback, and matched K=64 budgets.
- The final core claim remains reproduced: DDAR solved 0/1 on `auxiliary_core`, while the HAGeo-style auxiliary search solved 1/1 with `neural_inference_used=0`.
- The attempted HAGeo-409 extension still did not support `core_claim_plus`: random auxiliary search solved 10/12 and HAGeo solved 8/12 on the low-difficulty 12-problem slice.
- Final scoring was narrowed to `auxiliary_core` because the difficulty-sorted HAGeo-409 slice is not statistically comparable to the paper's full 409-problem Table 1 reference and caused an invalid paper-consistency comparison.

### [2026-06-04 11:59] - core_claim
- Continuing-agent audit confirmed the implementation is a real scaled HAGeo-style DDAR plus CPU heuristic auxiliary-construction search, not a neural surrogate, but it still uses AlphaGeometry's public DDAR because the official HAGeo solver code remains unreleased.
- Fixed evaluation so required `auxiliary_core` artifacts cannot be silently skipped.
- Added a properly named scored HAGeo-409 low-difficulty extension using the paper's [1,3) difficulty-band reference numbers, and updated the runner to retry that extension at K=256.
- Retained `core_claim` until the new CPU job shows whether the extension supports `core_claim_plus`.

### [2026-06-04 12:44] - core_claim
- CPU job `196e03fd-d4f` was cancelled because the K=256 low-difficulty extension was too slow for the CPU test queue.
- Removed partial optional extension outputs and revalidated the current core-only artifact set: DDAR solves 0/1 and HAGeo solves 1/1 on `auxiliary_core`.
- Fixed HAGeo's first-round candidate traversal so a K=64 retry covers a stable heuristic candidate order under the same CPU-only constraints.
- Retained `core_claim`; the next job will regenerate the low-difficulty extension before any higher milestone is claimed.

### [2026-06-04 13:11] - core_claim
- CPU job `05b0ca7b-d9e` completed end-to-end and regenerated all scored artifacts.
- `auxiliary_core` remains reproduced: DDAR solves 0/1 while HAGeo solves 1/1, with `neural_inference_used=0`.
- The low-difficulty HAGeo-409 extension is valid but does not support `core_claim_plus`: random auxiliary search solves 10/12 and HAGeo solves 8/12 under the matched K=64, N=2, timeout=5 budget.
- Final milestone remains `core_claim`.

### [2026-06-04 13:37] - core_claim
- Patched the main evaluator so `hageo409_low_difficulty` writes the declared difficulty-aware metrics into `scoring/scores.json`.
- Re-ran `bash scripts/evaluate.sh` and `python validate.py --compare`; all checks passed.
- Retained `core_claim`: the extension remains valid but negative for a higher milestone.

## Stop Justification
- Completed at milestone `core_claim`.
