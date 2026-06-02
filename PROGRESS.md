# Progress

## What Works

- Paper analysis is complete for the central claim: HAGeo is a CPU-only theorem prover that couples DDAR with heuristic auxiliary constructions rather than neural proposal models.
- The public HAGeo repository has been checked. It currently contains README/assets only, so this workspace vendors AlphaGeometry's public DDAR implementation and implements a scaled HAGeo-style auxiliary-construction search locally.
- Public benchmark data from `HAGeo-IMO/HAGeo-409` is downloaded into `data/downloads/` and converted into JSONL slices by `data/prepare_benchmarks.py`.
- The method now generates numerically guided auxiliary candidates for the paper's main heuristic categories: multi-line intersections, mixed line/circle intersections, circle/circle intersections, midpoint incidences, point reflections, perpendicular feet, and a final random-construction pool.
- A scaled random auxiliary-construction baseline has been added for HAGeo-409 comparison.
- `eval/` is method-independent. It reads output artifacts, validates problem IDs against the fixed benchmark files, rejects duplicate/missing/extra rows, and scores both `auxiliary_core` and `hageo409_scaled`.

## Results

- Previous stale outputs show the old HAGeo-style runner solved `auxiliary_core` where DDAR failed, and solved 3/12 on an exploratory HAGeo-409 slice versus DDAR's 2/12. Those outputs are useful history but are not accepted as final evidence for the patched implementation.
- The current patched method, random baseline, and hardened evaluator have passed lightweight syntax and reference validation on the login node.
- CPU test job `ba58a10a-3a5` failed before the method stage because `scripts/baseline.sh` evaluated immediately after writing the first fresh output, while stale HAGeo-409 outputs from an older 12-problem benchmark were still present. The evaluator correctly rejected the stale output coverage.
- Partial runner scripts now support `EVALUATE=0`, and `scripts/run.sh`/`scripts/reproduce.sh` remove stale outputs before regenerating all artifacts and running one final evaluation.
- CPU test job `e113a384-f00` completed successfully. The method still supports `core_claim` on `auxiliary_core` (DDAR 0/1, HAGeo 1/1), but the first-four HAGeo-409 slice was uninformative because both scaled random auxiliary search and HAGeo scored 0/4.
- Benchmark preparation now supports a reproducible difficulty-sorted HAGeo-409 slice. The next job uses the six easiest formal problems with a larger declared CPU budget to test whether `core_claim_plus` is supported on an additional paper benchmark setting.

## Remaining

- Inspect the next CPU job result. If HAGeo beats the random auxiliary baseline on `hageo409_scaled` while passing `auxiliary_core`, update `scores.json`, `MILESTONES.md`, and `PROGRESS.md` to `core_claim_plus`.
- If the scaled HAGeo-409 result does not beat random, tune the candidate ordering/budget within the declared scaled protocol and resubmit.
- A fuller reproduction would require implementing the paper's optimized DDAR engine, identical-point DD support, and full-scale K=2048/8192 HAGeo-409 or K=4096 IMO-30 runs.

## Issues

- The official HAGeo solver source is not publicly released; the public GitHub repository says the full code is pending release.
- This reproduction uses AlphaGeometry's DDAR engine rather than the paper's optimized DDAR implementation. That preserves the DDAR-plus-auxiliary-construction procedure but does not reproduce the paper's speedup claim.
- The submitted run is intentionally scaled to a four-problem HAGeo-409 slice and 24 attempts for CPU test-node validation. It is not a full Table 1 reproduction.
- The login node lacks the container Python dependencies, so functional solver validation must run through scheduled jobs.
- Broad root-level git operations can fail because `README.md` and `manifest.json` are character devices in this worktree. Path-specific git commands work.
- Job `ba58a10a-3a5` exposed a stale-artifact hazard rather than a solver failure; strict coverage validation is kept, and coordinated runs now clean/rebuild outputs before scoring.
- Job `e113a384-f00` showed that the original first-four HAGeo-409 slice and 24-attempt budget did not distinguish the heuristic from random. This is not counted as `core_claim_plus`.

## Deviations from Paper

- Full paper settings: HAGeo-409 uses K=2048/8192 and N=6; IMO-30 uses K=4096. The current CPU-scaled runner uses a low-difficulty HAGeo-409 slice, K=48, and N=1 to fit a CPU validation run.
- Full paper method: optimized DDAR, matrix-level AR improvements, and identical-point support are not yet implemented.
- Current paper-claim-facing score compares scaled HAGeo-style auxiliary search against a scaled random auxiliary baseline using the same budget, with the paper's Table 1 rates retained as reference context.
