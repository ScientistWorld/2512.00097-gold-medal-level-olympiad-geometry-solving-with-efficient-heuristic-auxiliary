# Evaluation Targets

Two scored experiments, `hageo409_aux` (weight 0.3) and `jgex231_aux` (weight 0.7), both produced by the same evaluator from its own DDAR proof runs. Run with:

```bash
bash scripts/evaluate_train.sh     # visible problems -> scoring/scores_train.json
bash scripts/evaluate_test.sh      # held-out problems -> scoring/scores_test.json (hidden evaluation)
python validate.py
```

## PRIMARY: jgex231_aux

What it tests: on held-out JGEX-231 problems that DDAR alone cannot prove (it saturates without the goal), the fraction proved after adding the submitted auxiliary constructions, within 16 attempts of at most 3 points each. Each of the 18 held-out problems is scored as 8 independent instances (fresh point names and drawing; DDAR alone still saturates on each): 144 held-out instances. Train: 12 problems × 8 = 96 instances.

- **Primary metric:** `solve_rate` (pass@16 over instances), higher is better. Reference (HAGeo heuristic) 0.618 (89/144) on the hidden test, 0.469 on train.
- **Other scored metric:** `pass_auc` (mean pass@k, k = 1..16; reference 0.453 test / 0.321 train).
- Resolution: the reference's own seeds score 0.611-0.632 (solve) and 0.453-0.473 (pass_auc); an improved proposer audited during hardening reaches 0.764 / 0.694, so there is headroom well above the noise.

## PRIMARY: hageo409_aux

What it tests: the same question on 38 held-out HAGeo-409 olympiad problems (the paper's benchmark) that DDAR alone cannot prove.

- **Primary metric:** `solve_rate` (pass@16), higher is better. Reference 0.079 = 3/38 on the hidden test, 0.12 = 3/25 on train.
- **Other scored metrics:** `hard_solve_rate` (difficulty ≥ 3; reference 0.0 test / 0.077 train), `pass_auc` (reference 0.059 test / 0.102 train).
- At this scale every method proves 1-3 of 38, so this experiment resolves about one problem; hence its weight 0.3.

## CONSTRAINT (both experiments)

What must be maintained: the paper's claim is a gain *without neural inference, within a fixed search budget, with valid proofs*. These are enforced as gates; violating any of them scores the run as failed (0 in every metric of every experiment):

- at most 16 attempts per problem and at most 3 auxiliary clauses per attempt;
- every clause is a legitimate definition of one fresh point (one point construction or exactly two loci from the allowlist; no over-determined clauses, no explicit coordinates, no redefinition), so no unproved incidence enters the premises;
- the proof is DDAR's, run by the evaluator under a fixed per-problem CPU-time limit on the evaluator's own premises and goal;
- the proposer stays within its CPU allowance (whole process tree: 6 s per problem for `hageo409_aux`, 2 s per problem for `jgex231_aux`, at least 120 s per experiment) and is not given the goal; the held-out files are unreadable while it runs.

## ABLATION / BASELINES

- `ddar`: no auxiliary construction. 0 on every scored problem by construction of the problem sets.
- `random_aux`: the paper's random auxiliary-construction baseline at the same budget. Hidden test: 0.053 (2/38) on HAGeo-409 and 0.479 (69/144) on JGEX-231, below the reference on both. Train: 0.04 vs 0.12 (HAGeo-409) and 0.385 vs 0.469 (JGEX-231).

## Paper numbers (not on this scale)

HAGeo-409 Table 1 (HAGeo 263/409 vs random 204/409 at K = 2048, N = 6) and IMO-30 Table 2 (HAGeo 28, random 25, AlphaGeometry 24, DDAR 15) are kept under `scoring/reference.json → experiments.hageo409_aux._paper_reported`. They use a different prover, a 128× larger budget and include problems DDAR solves alone, so they are context, not targets.
