# Evaluation

Scoring runs every proposer registered as `proposers/<name>.sh` (see `proposers/README.md` for the input/output contract) and verifies every attempt with the evaluator's own copy of the AlphaGeometry DD+AR prover. Nothing a proposer reports about its own success is used.

## Protocol

For each experiment and each problem:

1. The proposer receives the premises (no goal), the point names, a fixed numerical drawing of the configuration, the problem's human difficulty (HAGeo-409 only), and the budget: at most **16 attempts**, each of **1 to 3 auxiliary clauses**.
2. Every clause must define one fresh point from already defined points, either by one point construction (midpoint, mirror, foot, circumcenter, incenter, excenter, orthocenter, reflect, eq_triangle, psquare, nsquare, shift, intersection_*) or by exactly two loci (on_line, on_circle, on_tline, on_pline, on_bline, on_dia, on_circum, angle_bisector, angle_mirror, eqdistance, lc_tangent, on_aline). Over-determined clauses, explicit coordinates and redefined points are rejected.
3. The evaluator draws premises + attempt with a fixed seed and runs DDAR under a fixed per-problem CPU-time limit (6-20 s, set from how long DDAR needs on the premises alone). Attempts are tried in the submitted order; the first proof counts.
4. A run fails, and receives the worst value (0) in every metric of every experiment, if the proposer exits non-zero, uses more CPU time than its allowance (whole process tree; 6 s per problem for `hageo409_aux`, 2 s per problem for `jgex231_aux`, at least 120 s per experiment), writes malformed or incomplete output, exceeds the budget, or breaks a clause rule. Limits are CPU time, not wall-clock time, so results do not depend on machine load; numerical libraries run single-threaded.

## Experiments and metrics

- **hageo409_aux** — 38 held-out HAGeo-409 olympiad problems (25 visible train problems in `data/benchmarks/hageo409_train.jsonl`).
  - `solve_rate`: fraction proved within 16 attempts (pass@16). Higher is better.
  - `hard_solve_rate`: pass@16 on problems with human difficulty ≥ 3. Higher is better.
  - `pass_auc`: mean of pass@k over k = 1..16; rewards proving problems with fewer attempts. Higher is better.
- **jgex231_aux** — 18 held-out JGEX-231 problems, each presented as 8 independent instances (different point names and drawing, separate id), 144 scored instances (visible train: 12 problems × 8 = 96 instances in `data/benchmarks/jgex231_train.jsonl`); `solve_rate` and `pass_auc` as above, averaged over instances. The instances average out the proposer's own randomness; they do not add distinct problems.

Fixed reference points computed by the evaluator: DDAR alone (0 on every problem by construction) and random auxiliary constructions at the same budget.

## Running

```bash
bash scripts/evaluate_train.sh   # visible problems -> scoring/scores_train.json
bash scripts/evaluate.sh         # same, writes scoring/scores.json
```

The held-out problems are scored the same way by a separate hidden evaluation. Verification is CPU-only and deterministic up to the CPU-time limits; a full run of one proposer takes roughly 30-60 CPU-minutes for HAGeo-409 and 15-30 CPU-minutes for the JGEX-231 instances.

## Rules

Proposers must not use neural or LLM inference, network access, external proof or problem databases (including the public benchmark files' goals), or any file under `eval/` (the held-out directory is made unreadable while a proposer runs). The goal of each problem is deliberately withheld.
