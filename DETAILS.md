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

This benchmark is about automated Euclidean geometry theorem proving with auxiliary constructions. Each problem is stated in AlphaGeometry's point-construction language: a list of premises that construct points, and a goal (collinearity, concyclicity, equal angles, equal lengths, ...). A fixed symbolic prover (deductive database + algebraic reasoning, "DDAR") closes the premises under its rules. For every problem in the scored sets, that closure does **not** contain the goal: the prover saturates without proving it. Adding well-chosen new points (auxiliary constructions) to the premises can make the goal derivable.

## Task

A submission is a *proposer*: given a problem's premises (without the goal) and a numerical drawing of the configuration, it returns up to 16 attempts, each a short list (at most 3) of auxiliary point constructions. The evaluator adds each attempt to the premises and runs its own prover. A problem counts as solved when some attempt within the budget lets the prover derive the goal.

## Research Question

Which auxiliary constructions should be tried, and in what order, so that a fixed CPU-only prover proves as many problems as possible within a small attempt budget, without neural inference and without seeing the goal?

## Why It Matters

Auxiliary constructions are the creative step in olympiad geometry: symbolic provers are complete over a fixed configuration but cannot invent new points. A proposer that finds useful constructions with few attempts makes symbolic proving both stronger and cheaper. The scored problems come from public olympiad collections with human difficulty ratings and from a classic textbook-theorem benchmark.

## Success Criteria

Prove more held-out problems within the attempt budget, prove them with fewer attempts, and do so on the harder problems too, while every construction is a legitimate definition of a new point (no extra assumptions) and the proposer stays within its compute limit.

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

## Reference Implementation in This Gym

`proposers/hageo.sh` → `method/hageo/propose.py` implements the paper's auxiliary-construction procedure (Section 4.5) on top of AlphaGeometry's public DD+AR prover (the paper's optimized engine is not released):

- From the evaluator's numerical drawing it computes lines through pairs of points and circles through triples of points or centred at a point, and builds the paper's candidate categories: intersections of two lines through which a further line or circle passes, line/circle and circle/circle second intersections lying on a further object, midpoints and point reflections lying on a further line or circle, and feet of perpendiculars lying on a further line, plus a share of random constructions. The favourable incidence is only the reason to pick a point; each emitted clause states just the defining construction.
- Each of the K = 16 attempts has N = 2 rounds; in every round the candidate set of the current (augmented) diagram is recomputed and one point is chosen at random (the first round walks a random permutation so attempts start from different points). The evaluator runs DDAR once per attempt.
- Scaled settings: K = 16 (paper 2048/8192), N = 2 (paper 6), per-attempt CPU limits of 6-20 s (paper 60 s). The identical-point heuristic is omitted because the public prover rejects coincident points.
- `baseline/random_aux.py` is the paper's random baseline at the same budget.

---

# Evaluation

Scoring runs every proposer registered as `proposers/<name>.sh` (see `proposers/README.md` for the input/output contract) and verifies every attempt with the evaluator's own copy of the AlphaGeometry DD+AR prover. Nothing a proposer reports about its own success is used.

## Protocol

For each experiment and each problem:

1. The proposer receives the premises (no goal), the point names, a fixed numerical drawing of the configuration, the problem's human difficulty (HAGeo-409 only), and the budget: at most **16 attempts**, each of **1 to 3 auxiliary clauses**.
2. Every clause must define one fresh point from already defined points, either by one point construction (midpoint, mirror, foot, circumcenter, incenter, excenter, orthocenter, reflect, eq_triangle, psquare, nsquare, shift, intersection_*) or by exactly two loci (on_line, on_circle, on_tline, on_pline, on_bline, on_dia, on_circum, angle_bisector, angle_mirror, eqdistance, lc_tangent, on_aline). Over-determined clauses, explicit coordinates and redefined points are rejected.
3. The evaluator draws premises + attempt with a fixed seed and runs DDAR under a fixed per-problem CPU-time limit (6-20 s, set from how long DDAR needs on the premises alone). Attempts are tried in the submitted order; the first proof counts.
4. A run fails, and receives the worst value (0) in every metric of every experiment, if the proposer exits non-zero, exceeds 30 s per problem in total, writes malformed or incomplete output, exceeds the budget, or breaks a clause rule.

## Experiments and metrics

- **hageo409_aux** — 38 held-out HAGeo-409 olympiad problems (25 visible train problems in `data/benchmarks/hageo409_train.jsonl`).
  - `solve_rate`: fraction proved within 16 attempts (pass@16). Higher is better.
  - `hard_solve_rate`: pass@16 on problems with human difficulty ≥ 3. Higher is better.
  - `pass_auc`: mean of pass@k over k = 1..16; rewards proving problems with fewer attempts. Higher is better.
- **jgex231_aux** — 18 held-out JGEX-231 problems (12 visible train problems in `data/benchmarks/jgex231_train.jsonl`); `solve_rate` and `pass_auc` as above.

Fixed reference points computed by the evaluator: DDAR alone (0 on every problem by construction) and random auxiliary constructions at the same budget.

## Running

```bash
bash scripts/evaluate_train.sh   # visible problems -> scoring/scores_train.json
bash scripts/evaluate.sh         # same, writes scoring/scores.json
```

The held-out problems are scored the same way by a separate hidden evaluation. Verification is CPU-only and deterministic up to the CPU-time limits; a full run of one proposer takes roughly 30-60 CPU-minutes.

## Rules

Proposers must not use neural or LLM inference, network access, external proof or problem databases (including the public benchmark files' goals), or any file under `eval/`. The goal of each problem is deliberately withheld.

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

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 19m | **GPU**: 0.0h
- **Jobs**: 5 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-02 00:00] - core_claim_plus
- Audited the existing reproduction code and verified it implements a DDAR prover plus HAGeo-style auxiliary construction search, not a generic surrogate.
- Verified `eval/` remains independent of `method/` and reads solver output artifacts from `outputs/*.jsonl`.
- Ran `python validate.py --compare`; scoring and import-separation checks pass.
- Restored `core_claim_plus` based on the existing compute-node result: on `hageo409_small`, DDAR solved 2/12 and the HAGeo-style method solved 3/12.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim` | **Status**: error
- **Working time**: 1.3h | **GPU**: 0.0h
- **Jobs**: 16 total (12 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 41m | **GPU**: 0.0h
- **Jobs**: 18 total (13 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 18 total (13 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 18 total (13 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 20 total (15 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 3m | **GPU**: 0.0h
- **Jobs**: 20 total (15 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 20 total (15 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-06-04 13:39] - core_claim
- Final verification found and removed a solution-revealing note from the method-agnostic benchmark data.
- Rephrased strict method-agnostic documentation to avoid unnecessary solution-method leakage.
- Verified download URLs and reran `evaluate.sh`, `evaluate_train.sh`, `evaluate_test.sh`, and `validate.py --compare`; all checks passed.

</details>

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 9m | **GPU**: 0.0h
- **Jobs**: 20 total (15 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-06-04 13:39] - core_claim
- Final verification found and removed a solution-revealing note from the method-agnostic benchmark data.
- Rephrased strict method-agnostic documentation to avoid unnecessary solution-method leakage.
- Verified download URLs and reran `evaluate.sh`, `evaluate_train.sh`, `evaluate_test.sh`, and `validate.py --compare`; all checks passed.

### [2026-06-04 13:44] - core_claim
- Continued beyond the previous wrap-up after auditing the workspace and subagent findings.
- Fixed `scripts/run.sh` so compute jobs regenerate solver artifacts and refresh canonical `scoring/scores.json` before train/test scoring.
- Proposed a small-K HAGeo scheduling change, but it was not verified by a completed job before final verification.

### [2026-06-04 13:46] - core_claim
- Final verification reverted the unverified scheduling change so `scoring/scores.json` remains consistent with the method code and completed job artifacts.
- Tightened method-agnostic evaluation documentation and experiment descriptions.
- Verified `python validate.py --compare`, import separation, artifact-based evaluation, and download URL availability.
- Retained `core_claim`: the controlled core experiment is valid, while the HAGeo-409 extension remains a negative result for higher milestones.

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 15m | **GPU**: 0.0h
- **Jobs**: 20 total (15 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-06-04 13:39] - core_claim
- Final verification found and removed a solution-revealing note from the method-agnostic benchmark data.
- Rephrased strict method-agnostic documentation to avoid unnecessary solution-method leakage.
- Verified download URLs and reran `evaluate.sh`, `evaluate_train.sh`, `evaluate_test.sh`, and `validate.py --compare`; all checks passed.

### [2026-06-04 13:44] - core_claim
- Continued beyond the previous wrap-up after auditing the workspace and subagent findings.
- Fixed `scripts/run.sh` so compute jobs regenerate solver artifacts and refresh canonical `scoring/scores.json` before train/test scoring.
- Proposed a small-K HAGeo scheduling change, but it was not verified by a completed job before final verification.

### [2026-06-04 13:46] - core_claim
- Final verification reverted the unverified scheduling change so `scoring/scores.json` remains consistent with the method code and completed job artifacts.
- Tightened method-agnostic evaluation documentation and experiment descriptions.
- Verified `python validate.py --compare`, import separation, artifact-based evaluation, and download URL availability.
- Retained `core_claim`: the controlled core experiment is valid, while the HAGeo-409 extension remains a negative result for higher milestones.

</details>

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 52m | **GPU**: 0.0h
- **Jobs**: 25 total (18 completed, 2 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-06-04 13:39] - core_claim
- Final verification found and removed a solution-revealing note from the method-agnostic benchmark data.
- Rephrased strict method-agnostic documentation to avoid unnecessary solution-method leakage.
- Verified download URLs and reran `evaluate.sh`, `evaluate_train.sh`, `evaluate_test.sh`, and `validate.py --compare`; all checks passed.

### [2026-06-04 13:44] - core_claim
- Continued beyond the previous wrap-up after auditing the workspace and subagent findings.
- Fixed `scripts/run.sh` so compute jobs regenerate solver artifacts and refresh canonical `scoring/scores.json` before train/test scoring.
- Proposed a small-K HAGeo scheduling change, but it was not verified by a completed job before final verification.

### [2026-06-04 13:46] - core_claim
- Final verification reverted the unverified scheduling change so `scoring/scores.json` remains consistent with the method code and completed job artifacts.
- Tightened method-agnostic evaluation documentation and experiment descriptions.
- Verified `python validate.py --compare`, import separation, artifact-based evaluation, and download URL availability.
- Retained `core_claim`: the controlled core experiment is valid, while the HAGeo-409 extension remains a negative result for higher milestones.

### [2026-11-12] - core_claim (hardening iteration)
- Rebuilt the measurement: methods are proposers of auxiliary constructions; the evaluator withholds goals, verifies every attempt with its own DD+AR prover under CPU-time limits, enforces a validity gate (exactly-determined fresh points, no coordinates, 16x3 budget) and scores failures as worst values.
- Restored the paper's HAGeo procedure (single defining constructions chosen for favourable incidences, N rounds per attempt, one DDAR run per attempt); the old clauses were over-determined and mostly undrawable.
- Hidden test (problems DDAR alone cannot prove): HAGeo 3/38 vs random 2/38 vs DDAR 0 on HAGeo-409; HAGeo 12/18 vs random 7/18 vs DDAR 0 on JGEX-231. Details in HARDENING.md.

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
