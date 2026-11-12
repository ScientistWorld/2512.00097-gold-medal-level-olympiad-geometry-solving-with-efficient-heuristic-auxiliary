# Evaluation Targets

Two scored experiments, `hageo409_aux` (weight 0.5) and `jgex231_aux` (weight 0.5), both produced by the same evaluator from its own DDAR proof runs. Run with:

```bash
bash scripts/evaluate_train.sh     # visible problems -> scoring/scores_train.json
bash scripts/evaluate_test.sh      # held-out problems -> scoring/scores_test.json (hidden evaluation)
python validate.py
```

## PRIMARY: hageo409_aux

What it tests: on held-out HAGeo-409 problems that DDAR alone cannot prove (it saturates without the goal), the fraction proved after adding the submitted auxiliary constructions, within 16 attempts of at most 3 points each.

- **Primary metric:** `solve_rate` (pass@16), higher is better. Reference (HAGeo heuristic) 0.079 = 3/38 on the hidden test, 0.12 on train.
- **Other scored metrics:** `hard_solve_rate` (difficulty ≥ 3; reference 0.0 test / 0.077 train), `pass_auc` (mean pass@k, k = 1..16; reference 0.059 test / 0.102 train).

## PRIMARY: jgex231_aux

What it tests: the same question on held-out JGEX-231 problems that DDAR alone cannot prove.

- **Primary metric:** `solve_rate`, higher is better. Reference 0.667 = 12/18 on the hidden test, 0.417 on train.
- **Other scored metric:** `pass_auc` (reference 0.458 test / 0.208 train).

## CONSTRAINT (both experiments)

What must be maintained: the paper's claim is a gain *without neural inference and within a fixed search budget, with valid proofs*. These are enforced as gates; violating any of them scores the run as failed (0 in every metric of every experiment):

- at most 16 attempts per problem and at most 3 auxiliary clauses per attempt;
- every clause is a legitimate definition of one fresh point (one point construction or exactly two loci from the allowlist; no over-determined clauses, no explicit coordinates, no redefinition), so no unproved incidence enters the premises;
- the proof is DDAR's, run by the evaluator under a fixed per-problem CPU-time limit on the evaluator's own premises and goal;
- the proposer finishes within 30 s per problem in total and is not given the goal.

## ABLATION / BASELINES (both experiments)

- `ddar`: no auxiliary construction. 0 on every scored problem by construction of the problem sets.
- `random_aux`: the paper's random auxiliary-construction baseline at the same budget. Hidden test: 0.053 (2/38) on HAGeo-409 and 0.389 (7/18) on JGEX-231, below the reference on both. On the small train sets it is 0.04 vs 0.12 (HAGeo-409) and 0.5 vs 0.417 (JGEX-231).

## Paper numbers (not on this scale)

HAGeo-409 Table 1 (HAGeo 263/409 vs random 204/409 at K = 2048, N = 6) and IMO-30 Table 2 (HAGeo 28, random 25, AlphaGeometry 24, DDAR 15) are kept under `scoring/reference.json → experiments.hageo409_aux._paper_reported`. They use a different prover, a 128× larger budget and include problems DDAR solves alone, so they are context, not targets.
