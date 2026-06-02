# Evaluation Targets

## PRIMARY: auxiliary_core

Tests whether adding a useful auxiliary construction lets a DDAR prover solve a theorem that the DDAR-only baseline does not solve.
- **Metric:** solve_rate (higher is better)
- **Companion metrics:** solved_count and problem_count
- **Constraint metrics:** mean_auxiliary_count and mean_attempt_index should remain small enough that improvements do not come only from unbounded construction spam.
- **How to run evaluation:** run `scripts/reproduce.sh` or the paired `scripts/baseline.sh` and `scripts/method.sh` commands on `data/benchmarks/auxiliary_core.jsonl`, then run `scripts/evaluate.sh`.

## PRIMARY: hageo409_small

Tests theorem-proving performance on a small fixed slice of the public HAGeo-409 benchmark using the same formal problem representation for all methods.
- **Metric:** solve_rate (higher is better)
- **Companion metrics:** solved_count and problem_count
- **Constraint metrics:** mean_auxiliary_count and mean_attempt_index capture construction/search budget use.
- **How to run evaluation:** run `scripts/reproduce.sh` after `scripts/download.sh` has prepared the public parquet benchmark, then run `scripts/evaluate.sh`.
