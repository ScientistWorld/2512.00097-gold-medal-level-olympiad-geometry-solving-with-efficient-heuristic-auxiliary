# Evaluation

Evaluation measures whether a submitted geometry prover can solve the benchmark problems under fixed inputs, resource limits, and proof-validity checks. This document intentionally describes only the task-level evaluation, not any particular solution method.

## Metrics

- **Solved count:** number of benchmark problems for which the system proves the requested conclusion within the allotted budget. Higher is better.
- **Solve rate:** solved count divided by the number of evaluated problems. Higher is better.
- **Pass@K:** number or rate of problems solved when the system is allowed up to K independent proof attempts, construction proposals, or search trials under the benchmark's definition of an attempt. Higher is better.
- **Difficulty-band solve rate:** solve rate reported separately for the HAGeo-409 difficulty bands [1,3), [3,4), [4,5), [5,6), and [6,7]. Higher is better, and this guards against only improving easy instances.
- **Proof validity:** fraction of claimed solves whose proof or certificate passes the evaluator's validity checks. Higher is better; invalid proofs must not count as solved.
- **Resource compliance:** wall-clock budget, hardware class, and neural-inference usage are tracked as constraint metrics. Lower time is better when solve performance is comparable, and any violation of the fixed resource policy invalidates comparison.

## Baselines and Targets

Reference levels from the paper:

- **Base symbolic prover on IMO-30:** 15/30 solved.
- **Prior neural-symbolic system on IMO-30:** 24/30 solved using the paper's corrected count.
- **Stochastic construction-search baseline on IMO-30:** 25/30 solved.
- **Paper's proposed CPU-only system on IMO-30:** 28/30 solved.
- **Prior neural-symbolic system on HAGeo-409:** 177/409 solved.
- **Stochastic construction-search baseline on HAGeo-409:** 204/409 solved at 2,048 attempts and 218/409 at 8,192 attempts.
- **Paper's proposed CPU-only system on HAGeo-409:** 263/409 solved at 2,048 attempts and 287/409 at 8,192 attempts.

The primary reproduction target is to match the paper's solve-rate pattern on HAGeo-409 and IMO-30 while preserving valid proofs and the CPU-only, non-neural inference setting. IMO-30 alone is not sufficient because the paper argues that it is small and difficulty-skewed.

## Evaluation Protocol

Evaluate on the fixed formal benchmark files for IMO-30 and HAGeo-409. The test problems and conclusions must not be edited, filtered, or retranslated during evaluation. Report aggregate solve count and solve rate, and for HAGeo-409 also report each difficulty band.

Use the same attempt budgets when comparing systems: the paper reports HAGeo-409 at K=2,048 and K=8,192, and IMO-30 under the paper's stated time budget. If stochastic search is used, fix and report seeds or run enough repeated evaluations to make the reported pass@K reproducible. A problem counts as solved only if the final conclusion is established by the accepted proof checker or evaluator.

All methods should be evaluated under the declared hardware and time constraints. Methods that use neural inference, external problem data, or additional unlabeled/labeled geometry corpora must be reported separately and should not be compared as compliant improvements to the paper's central claim.
