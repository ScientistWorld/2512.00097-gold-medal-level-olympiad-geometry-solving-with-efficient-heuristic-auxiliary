# Evaluation Targets

## PRIMARY: hageo409_scaled

Scores a fixed HAGeo-409 slice against the paper's central comparison: CPU-only HAGeo-style heuristic auxiliary construction should outperform a random auxiliary-construction baseline under the same declared attempt, round, timeout, and seed budget.

- **Benefit metric:** `solve_rate` (higher is better)
- **Companion metrics:** `solved_count` and `problem_count`
- **Constraint metrics:** `attempt_budget`, `rounds`, `timeout_seconds`, and `neural_inference_used`
- **Paper reference:** Table 1 total rates for Random@2048 (204/409, 49.9%) and HAGeo@2048 (263/409, 64.3%)
- **Current scale:** the runnable job uses the prepared `data/benchmarks/hageo409_small.jsonl` slice and a smaller budget for CPU smoke validation.

## SECONDARY: auxiliary_core

Checks that the environment can distinguish a DDAR-only prover from a prover that uses a useful auxiliary construction on a controlled theorem.

- **Benefit metric:** `solve_rate` (higher is better)
- **Companion metrics:** `solved_count`, `problem_count`, `mean_attempt_index`, and `mean_auxiliary_count`
- **Constraint metrics:** `attempt_budget`, `rounds`, `timeout_seconds`, and `neural_inference_used`
