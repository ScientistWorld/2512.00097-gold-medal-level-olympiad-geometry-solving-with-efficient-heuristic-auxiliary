# Progress

## What Works

- Paper analysis is complete for the central claim: HAGeo is a CPU-only theorem prover that couples DDAR with heuristic auxiliary constructions rather than neural proposal models.
- The public HAGeo repository has been checked. It currently contains README/assets only, so this workspace vendors AlphaGeometry's public DDAR implementation and implements a scaled HAGeo-style auxiliary-construction search locally.
- Public benchmark data from `HAGeo-IMO/HAGeo-409` is downloaded into `data/downloads/` and converted into JSONL slices by `data/prepare_benchmarks.py`.
- The method now generates numerically guided auxiliary candidates for the paper's main heuristic categories: multi-line intersections, mixed line/circle intersections, circle/circle intersections, midpoint incidences, point reflections, perpendicular feet, and a final random-construction pool.
- A scaled random auxiliary-construction baseline has been added for HAGeo-409 comparison.
- `eval/` is method-independent. It reads output artifacts, validates problem IDs against the fixed benchmark file, rejects duplicate/missing/extra rows, and scores the final `auxiliary_core` experiment.

## Results

- Previous stale outputs show the old HAGeo-style runner solved `auxiliary_core` where DDAR failed, and solved 3/12 on an exploratory HAGeo-409 slice versus DDAR's 2/12. Those outputs are useful history but are not accepted as final evidence for the patched implementation.
- The current patched method, random baseline, and hardened evaluator have passed lightweight syntax and reference validation on the login node.
- CPU test job `ba58a10a-3a5` failed before the method stage because `scripts/baseline.sh` evaluated immediately after writing the first fresh output, while stale HAGeo-409 outputs from an older 12-problem benchmark were still present. The evaluator correctly rejected the stale output coverage.
- Partial runner scripts now support `EVALUATE=0`, and `scripts/run.sh`/`scripts/reproduce.sh` remove stale outputs before regenerating all artifacts and running one final evaluation.
- CPU test job `e113a384-f00` completed successfully. The method still supports `core_claim` on `auxiliary_core` (DDAR 0/1, HAGeo 1/1), but the first-four HAGeo-409 slice was uninformative because both scaled random auxiliary search and HAGeo scored 0/4.
- Benchmark preparation now supports a reproducible difficulty-sorted HAGeo-409 slice. The next job uses the six easiest formal problems with a larger declared CPU budget to test whether `core_claim_plus` is supported on an additional paper benchmark setting.
- CPU test job `09e02880-313` failed during the random auxiliary baseline on the first difficulty-sorted HAGeo-409 problem. DDAR had timed out before returning a graph, and fallback candidate generation rebuilt the full problem including a `cyclic` theorem goal that AlphaGeometry's numeric checker cannot parse in that path.
- Candidate fallback generation now rebuilds only the construction setup with a harmless dummy goal, and DDAR timeout paths retain any graph that had already been built.
- CPU test job `675c93ff-642` completed successfully on the six easiest HAGeo-409 problems. HAGeo and random auxiliary search both solved 3/6, so this does not support `core_claim_plus`; two of those solves were DDAR-only for both methods, and each auxiliary method solved one additional problem.
- The HAGeo attempt order now interleaves ranked heuristic candidates with shuffled exploration, and the next run expands the fixed low-difficulty slice to 12 problems to reduce variance from single random auxiliary hits.
- CPU job `4cb60e78-0c8` completed successfully on the 12-problem slice. HAGeo and random auxiliary search again tied at 8/12; most solves were DDAR-only, so this still does not establish the paper's random-vs-heuristic improvement on HAGeo-409.
- The next run keeps the 12-problem slice and K=48 but raises the construction depth from N=1 to N=2, matching the paper's multi-round search procedure more closely while keeping random under the same budget.
- CPU job `4db0ca3b-381` completed successfully with N=2, but random solved 9/12 while HAGeo solved only 6/12. Inspection showed the N=2 implementation checked DDAR only after both auxiliaries were inserted, so useful one-auxiliary proofs could be destroyed by a second construction.
- The method and random baseline now rerun DDAR after every added auxiliary within an attempt, which better matches iterative auxiliary-construction search and preserves successful intermediate states.
- CPU job `036b6af6-cfc` completed successfully with the corrected iterative N=2 check. `auxiliary_core` still supports the core claim (DDAR 0/1, HAGeo 1/1), while the scaled HAGeo-409 comparison tied again at 8/12 for both HAGeo and random auxiliary search.
- Per-problem inspection showed that HAGeo missed one auxiliary problem solved by random, and that the HAGeo runner's N=2 candidate indexing used only every other first-round candidate. The method now indexes first-round candidates across the full declared K=48 budget and adds the paper's identical-point auxiliary category.
- CPU job `49edf3e0-664` was cancelled after the HAGeo stage stayed on `2019G1` for roughly twenty minutes. The partial logs show random completed normally, so the stall was isolated to HAGeo candidate generation after adding identical-point candidates.
- Identical-point enumeration is now bounded, and HAGeo candidate generation is wrapped in the same hard timeout mechanism used for DDAR calls. If candidate generation times out for a second-round state, that attempt fails fast instead of blocking the whole run.
- CPU job `299ca567-06f` completed successfully with those timeout guards. `auxiliary_core` remains reproduced, but the scaled HAGeo-409 comparison still did not support a higher milestone: HAGeo solved 8/12 while the matched random auxiliary baseline solved 10/12 at K=48, N=2, timeout=5.
- Inspection of the per-problem outputs showed that HAGeo was still brittle in two-round search: regenerated candidate lists could reuse local constructed-point names such as `x0`, and attempts could stop when second-round candidate regeneration timed out even though the initial HAGeo candidate pool remained valid. Auxiliary insertions now freshen constructed-point names in both HAGeo and the random baseline, and HAGeo falls back to its initial heuristic pool when second-round regeneration is unavailable.
- CPU job `1568a310-592` completed successfully with fresh auxiliary names, second-round fallback, and matched K=64 budgets. `auxiliary_core` still supports `core_claim`: DDAR solved 0/1 and HAGeo solved 1/1 with `neural_inference_used=0`.
- The K=64 HAGeo-409 extension still did not support `core_claim_plus`: random auxiliary search solved 10/12, while HAGeo solved 8/12 on the low-difficulty 12-problem slice.
- Final `scoring/scores.json` includes only `auxiliary_core`. The HAGeo-409 slice is documented as an attempted extension because its low-difficulty selection makes its solve rates incompatible with the paper's full 409-problem reference rates.
- Continuing-agent audit on 2026-06-04 confirmed that the official HAGeo GitHub repository still contains only README/assets and says the full code is pending release. The workspace therefore remains a scaled implementation of the paper's computation pattern using AlphaGeometry's public DDAR plus HAGeo-style CPU auxiliary generation.
- The evaluator now fails if required `auxiliary_core` benchmark or output artifacts are missing, and it scores the fixed low-difficulty HAGeo-409 slice as `hageo409_low_difficulty` against the paper's Table 1 [1,3) reference band.
- Current artifact scores after the audit are: `auxiliary_core` DDAR 0/1 and HAGeo 1/1; `hageo409_low_difficulty` random auxiliary 10/12 and HAGeo 8/12 at K=64, N=2, timeout=5. This extension is scored but does not yet justify `core_claim_plus`.
- The next submitted CPU job raises the matched low-difficulty extension budget to K=256, N=2 while retaining CPU-only, non-neural inference.

## Remaining

- To reach `core_claim_plus`, the scored `hageo409_low_difficulty` extension should show HAGeo beating the matched random auxiliary baseline on the fixed slice, or a future run should use a more representative HAGeo-409 subset with the same artifact-based evaluator.
- A fuller reproduction would require implementing the paper's optimized DDAR engine, identical-point DD support, and full-scale K=2048/8192 HAGeo-409 or K=4096 IMO-30 runs.

## Issues

- The official HAGeo solver source is not publicly released; the public GitHub repository says the full code is pending release.
- This reproduction uses AlphaGeometry's DDAR engine rather than the paper's optimized DDAR implementation. That preserves the DDAR-plus-auxiliary-construction procedure but does not reproduce the paper's speedup claim.
- The submitted run is intentionally scaled to a four-problem HAGeo-409 slice and 24 attempts for CPU test-node validation. It is not a full Table 1 reproduction.
- The login node lacks the container Python dependencies, so functional solver validation must run through scheduled jobs.
- Broad root-level git operations can fail because `README.md` and `manifest.json` are character devices in this worktree. Path-specific git commands work.
- Job `ba58a10a-3a5` exposed a stale-artifact hazard rather than a solver failure; strict coverage validation is kept, and coordinated runs now clean/rebuild outputs before scoring.
- Job `e113a384-f00` showed that the original first-four HAGeo-409 slice and 24-attempt budget did not distinguish the heuristic from random. This is not counted as `core_claim_plus`.
- Job `09e02880-313` was a fallback candidate-generation bug, not a completed scaled benchmark. It produced no valid `hageo409_scaled` score.
- Job `675c93ff-642` was valid but tied the random baseline on the scaled HAGeo-409 slice, so it remains only `core_claim`.
- Job `4cb60e78-0c8` was valid but tied the random baseline on the expanded 12-problem scaled HAGeo-409 slice, so it remains only `core_claim`.
- Job `4db0ca3b-381` exposed an implementation issue in the N=2 runner: checking only after all rounds made HAGeo lose intermediate one-auxiliary solutions.
- Job `036b6af6-cfc` was valid but tied the random baseline at 8/12; it exposed a HAGeo-only attempt-indexing issue and a missing identical-point heuristic category.
- Job `49edf3e0-664` was cancelled because unbounded identical-point candidate generation made HAGeo stall on the second HAGeo-409 problem.
- Job `299ca567-06f` was valid but HAGeo underperformed random on the scaled HAGeo-409 benchmark, so it remains only `core_claim`. It exposed two multi-round search issues: non-fresh generated auxiliary names and overly strict aborts when second-round candidate regeneration was unavailable.
- Job `1568a310-592` was valid but again HAGeo underperformed random on the low-difficulty HAGeo-409 slice at K=64. This confirms the extension is not sufficient for `core_claim_plus`.
- The validator rejected scoring the low-difficulty HAGeo-409 slice under the `hageo409_scaled` full-benchmark reference name because the random baseline's 10/12 solve rate was far from the paper's full-benchmark 204/409 reference. This has been fixed by renaming the scored extension to `hageo409_low_difficulty` and comparing it with the paper's [1,3) difficulty band.

## Deviations from Paper

- Full paper settings: HAGeo-409 uses K=2048/8192 and N=6; IMO-30 uses K=4096. CPU-scaled extension runs use a low-difficulty 12-problem HAGeo-409 slice with smaller K and N=2, and are compared only with the paper's low-difficulty [1,3) band.
- Full paper method: optimized DDAR, matrix-level AR improvements, and HAGeo's optimized identical-point DD support are not yet implemented. The auxiliary generator now proposes identical-point constructions, but the upstream AlphaGeometry DDAR engine may reject or fail to exploit some of them.
- The final paper-claim-facing score is the controlled `auxiliary_core` ablation: DDAR alone fails and HAGeo-style auxiliary construction succeeds within a declared CPU-only budget.
