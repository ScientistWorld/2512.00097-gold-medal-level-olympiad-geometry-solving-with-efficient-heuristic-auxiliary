# Evaluation Targets

The final scored targets are `auxiliary_core`, the minimum experiment that supports the paper's central claim, and `hageo409_low_difficulty`, a scaled extension on a fixed low-difficulty slice of HAGeo-409.

Run evaluation with:

```bash
bash scripts/evaluate.sh
python validate.py
```

## PRIMARY: auxiliary_core

What it tests: solve the controlled auxiliary-construction theorem in `data/benchmarks/auxiliary_core.jsonl`.

- **Primary metric:** `solve_rate` (higher is better)
- **Reported benefit metrics:** `solved_count`, `problem_count`, `mean_attempt_index`, and `mean_auxiliary_count`
- **Success condition for this reproduction:** `hageo.solve_rate` is 1.0 on the benchmark.

## CONSTRAINT: auxiliary_core

What must be maintained: the solve must remain CPU-only and within the declared search budget.

- **Constraint metrics:** `neural_inference_used`, `attempt_budget`, `rounds`, and `timeout_seconds`
- **Direction:** lower is better for `neural_inference_used`, `attempt_budget`, `rounds`, and `timeout_seconds`; `neural_inference_used` must remain 0.
- **Reason:** the paper's claim is not just that an auxiliary can solve the problem, but that the method avoids neural language-model proposals during proof search.

## ABLATION: auxiliary_core

What breaks when the key idea is removed: DDAR alone should fail on the same theorem.

- **Ablation method:** `ddar`
- **Primary metric:** `solve_rate` (higher is better)
- **Expected reproduced behavior:** `ddar.solve_rate` is 0.0 while `hageo.solve_rate` is 1.0.
- **Reason:** this verifies that the scored solve is due to auxiliary construction rather than the base prover already solving the problem.

## EXTENSION: hageo409_low_difficulty

What it tests: solve the fixed low-difficulty HAGeo-409 slice in `data/benchmarks/hageo409_small.jsonl`.

- **Primary metric:** `solve_rate` (higher is better)
- **Compared methods:** `random_aux_ddar` and `hageo`
- **Constraint metrics:** `neural_inference_used`, `attempt_budget`, `rounds`, and `timeout_seconds`
- **Success condition for a higher milestone:** `hageo.solve_rate` should exceed the matched random auxiliary baseline on this slice while keeping `neural_inference_used` at 0.
- **Paper reference:** Table 1 difficulty band [1,3), where HAGeo@2048 solves 141/161 and Random@2048 solves 127/161.
