# Evaluation Targets

These targets define what future scientist agents should optimize and what constraints they must preserve. They are high-level and should correspond to experiments recorded in `scores.json`.

## PRIMARY: imo30_solve_rate

Tests headline performance on the standard IMO-30 Olympiad geometry benchmark.
- **Metric:** solve_rate (higher is better)
- **Companion metric:** solved_count (higher is better)
- **How to run evaluation:** run the compliant prover on the fixed IMO-30 formal problem set under the benchmark time and resource budget; count only evaluator-accepted proofs.

## PRIMARY: hageo409_solve_rate_k2048

Tests overall performance on the larger HAGeo-409 benchmark at the main attempt budget.
- **Metric:** solve_rate (higher is better)
- **Companion metric:** solved_count (higher is better)
- **How to run evaluation:** run the compliant prover on all fixed HAGeo-409 problems with K=2,048 attempts; count only evaluator-accepted proofs.

## PRIMARY: hageo409_solve_rate_k8192

Tests scaling of task success when the attempt budget is increased.
- **Metric:** solve_rate (higher is better)
- **Companion metric:** solved_count (higher is better)
- **How to run evaluation:** run the compliant prover on all fixed HAGeo-409 problems with K=8,192 attempts; count only evaluator-accepted proofs.

## PRIMARY: hageo409_difficulty_band_rates

Tests whether the system improves across the benchmark difficulty distribution rather than only on easy problems.
- **Metric:** mean_band_solve_rate (higher is better)
- **Companion metrics:** solve_rate for [1,3), [3,4), [4,5), [5,6), and [6,7] difficulty bands (higher is better)
- **How to run evaluation:** compute solved counts and solve rates separately for each fixed HAGeo-409 difficulty band using the same run outputs as the corresponding HAGeo-409 evaluation.

## CONSTRAINT: proof_validity

Tests whether claimed solutions are accepted as valid geometry proofs or certificates.
- **Metric:** valid_claim_rate (higher is better)
- **Failure rule:** invalid or unchecked claimed solves must not count toward solve-rate metrics.
- **How to run evaluation:** pass every claimed solve through the evaluator or proof-checking procedure and report accepted claims divided by total claimed solves.

## CONSTRAINT: cpu_only_non_neural_inference

Tests whether the central resource claim is preserved: inference must not rely on neural proposal models or GPU computation.
- **Metric:** violation_count (lower is better)
- **Failure rule:** any GPU-backed inference, neural model inference, or external online service use during evaluation makes the run non-compliant.
- **How to run evaluation:** record runtime configuration, dependencies, hardware usage, and method logs for the evaluation run.

## CONSTRAINT: runtime_budget

Tests whether improvements come from better reasoning under the benchmark budget rather than unbounded computation.
- **Metric:** wall_clock_seconds (lower is better when solve rate is comparable)
- **Failure rule:** solves obtained after the declared time or attempt limit must not count in the compliant score.
- **How to run evaluation:** measure elapsed wall-clock time for each benchmark run and enforce the configured per-problem and total budgets.

## ABLATION: better_than_random_baseline

Tests whether the system's improvements are not merely due to spending attempts on generic randomized search.
- **Metric:** solve_rate_gap_vs_random (higher is better)
- **How to run evaluation:** compare the compliant system against the fixed random baseline at the same benchmark, attempt budget, and resource setting.
