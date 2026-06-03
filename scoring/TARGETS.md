# Evaluation Targets

The final scored target is `auxiliary_core`, the minimum experiment that supports the paper's central claim: a CPU-only geometry prover can solve a theorem that DDAR alone misses by adding a useful auxiliary construction, without neural proposal models.

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
