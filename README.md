# Overview

- **Paper ID:** 2512.00097
- **Title:** Gold-Medal-Level Olympiad Geometry Solving with Efficient Heuristic Auxiliary Constructions
- **Domain:** Automated Theorem Proving / Euclidean Geometry
- **TL;DR:** The paper shows that a CPU-only geometry theorem prover can solve Olympiad-level geometry problems at gold-medal level by combining a fast deductive-algebraic prover with targeted auxiliary constructions.

## Short Summary

This paper studies automated theorem proving for Euclidean geometry, especially International Mathematical Olympiad-level problems where auxiliary constructions are often essential. It proposes HAGeo, a non-neural system that repeatedly augments a formal geometry problem with promising auxiliary constructions and reruns a deductive-algebraic proof engine. The paper also introduces HAGeo-409, a 409-problem benchmark with human difficulty ratings intended to be larger and more discriminating than IMO-30. Reported results show HAGeo outperforming AlphaGeometry and random auxiliary construction baselines while running entirely on CPUs.

## Key Results

- HAGeo solves 28 of 30 problems on IMO-30, compared with 24 for the paper's corrected AlphaGeometry count, 25 for a random auxiliary-construction baseline, and 15 for DDAR alone.
- On HAGeo-409, HAGeo solves 263/409 problems at 2,048 attempts and 287/409 at 8,192 attempts, outperforming both AlphaGeometry and random auxiliary construction across difficulty bands.
- The paper reports an optimized DDAR engine with roughly 20x faster average inference than AlphaGeometry's DDAR implementation under the compared CPU setting.

---

# Problem Definition

This benchmark is about automated Euclidean geometry theorem proving. A system receives a geometry problem expressed in a formal construction language and must determine whether the target conclusion follows from the premises by producing or internally certifying a valid proof.

## Research Question

Can an automated theorem prover solve challenging Olympiad-level Euclidean geometry problems reliably and efficiently under a fixed formal problem representation and bounded computational budget? The central gap is that existing benchmarks are small or comparatively easy, and prior high-performing systems often require expensive neural inference or very large search budgets.

## Why It Matters

Geometry theorem proving is a long-standing test of mathematical reasoning because successful solutions often require both exact deduction and useful auxiliary constructions. A strong benchmark environment should distinguish genuinely better reasoning systems from methods that only win by using more compute, richer external knowledge, or an easier problem set.

## Success Criteria

A successful system should solve a large fraction of held-out Olympiad-level geometry problems, maintain proof validity, perform well across difficulty bands rather than only on easy instances, and respect the declared resource and evaluation constraints. Efficiency matters because the paper's claim is not only about solving more problems, but doing so without neural inference and within practical CPU budgets.

---

# Paper's Method

## Key Contribution

The paper introduces HAGeo, a CPU-only automated Euclidean geometry theorem prover that replaces neural auxiliary-construction proposal with a heuristic construction strategy guided by numerical geometry checks. It pairs this strategy with an optimized deductive database and algebraic reasoning engine, then evaluates the system on both IMO-30 and a new 409-problem benchmark with difficulty labels.

## Approach

HAGeo first parses each problem into a geometry-specific construction language containing points, lines, circles, and construction actions. The problem is encoded as a deduction graph and passed through a DDAR-style prover: a deductive database applies geometric inference rules, while an algebraic reasoning module derives angle, length, and ratio consequences through matrix-based linear reasoning.

If the initial prover run does not establish the conclusion, HAGeo performs multiple auxiliary-construction attempts. Each attempt builds a short sequence of added constructions, then reruns the prover on the augmented problem. Candidate auxiliary points are generated from geometric configurations that appear promising under numerical checks, including multi-object intersections, midpoints, reflections, perpendicular feet, identical-point opportunities, and random constructions. The numerical checks are used to select valid construction candidates, not to assume the theorem's conclusion.

The paper also modifies DDAR implementation details to improve speed while preserving deductive capacity. These changes include optimized deduction rules, support for identical points, and matrix-level algebraic reasoning optimizations that reduce redundant variables and computation.

## Main Claims

- **Primary claim:** HAGeo achieves gold-medal-level performance on IMO-30 without neural inference, solving 28/30 problems.
- **Primary benchmark claim:** HAGeo substantially outperforms AlphaGeometry and random auxiliary-construction baselines on HAGeo-409, including across human difficulty bands.
- **Constraint claim:** The system's strong solve rate is obtained using CPU-only inference rather than GPU-backed neural proposal models.
- **Efficiency claim:** The optimized DDAR engine is roughly 20x faster than AlphaGeometry's DDAR implementation in the paper's comparison.
- **Benchmark claim:** HAGeo-409 is a more informative evaluation set than IMO-30 because it is larger and includes human-assessed difficulty annotations.

---

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

- **DDAR-only baseline on IMO-30:** 15/30 solved.
- **AlphaGeometry on IMO-30:** 24/30 solved using the paper's corrected count.
- **Random auxiliary-construction baseline on IMO-30:** 25/30 solved.
- **HAGeo target on IMO-30:** 28/30 solved.
- **AlphaGeometry on HAGeo-409:** 177/409 solved.
- **Random baseline on HAGeo-409:** 204/409 solved at 2,048 attempts and 218/409 at 8,192 attempts.
- **HAGeo target on HAGeo-409:** 263/409 solved at 2,048 attempts and 287/409 at 8,192 attempts.

The primary reproduction target is to match the HAGeo solve-rate pattern on HAGeo-409 and IMO-30 while preserving valid proofs and the CPU-only, non-neural inference setting. IMO-30 alone is not sufficient because the paper argues that it is small and difficulty-skewed.

## Evaluation Protocol

Evaluate on the fixed formal benchmark files for IMO-30 and HAGeo-409. The test problems and conclusions must not be edited, filtered, or retranslated during evaluation. Report aggregate solve count and solve rate, and for HAGeo-409 also report each difficulty band.

Use the same attempt budgets when comparing systems: the paper reports HAGeo-409 at K=2,048 and K=8,192, and IMO-30 under the paper's stated time budget. If stochastic search is used, fix and report seeds or run enough repeated evaluations to make the reported pass@K reproducible. A problem counts as solved only if the final conclusion is established by the accepted proof checker or evaluator.

All methods should be evaluated under the declared hardware and time constraints. Methods that use neural inference, external problem data, or additional unlabeled/labeled geometry corpora must be reported separately and should not be compared as compliant improvements to the paper's central claim.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: error
- **Working time**: 46m | **GPU**: 0.0h
- **Jobs**: 5 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-06-02 18:48] - core_claim_plus
- Compute-node job `b2a7bdfd-937` improved the real HAGeo-409 small slice: DDAR-only solved 2/12, while the HAGeo-style auxiliary search solved 3/12.
- The additional solved problem required a constructed midpoint auxiliary, matching the paper's claim that heuristic auxiliary construction can extend DDAR.
- Tightened candidate bookkeeping and increased the bounded small-slice attempt budget for one more expansion run.

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
