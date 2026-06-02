# Experiment Overview

This file describes what each expected scoring experiment is trying to establish. It intentionally avoids describing any method internals.

## imo30_solve_rate

Tests whether the system reaches strong performance on the established 30-problem Olympiad geometry benchmark. This experiment supports comparison to prior work on the familiar headline setting, but it should not be treated as sufficient by itself because the benchmark is small.

## hageo409_solve_rate_k2048

Tests overall theorem-proving success on the larger 409-problem benchmark at the main attempt budget. This is the central broad-coverage evaluation because it uses more problems and includes a wider range of human-rated difficulty.

## hageo409_solve_rate_k8192

Tests whether the system continues to make useful progress when the allowed search budget is increased. The purpose is to measure scalable problem-solving performance under a fixed larger budget, not to give unlimited computation.

## hageo409_difficulty_band_rates

Tests whether benchmark performance holds across easy, medium, and hard geometry problems. This experiment helps identify systems that improve aggregate scores mostly by solving easy instances while failing to advance on harder ones.

## proof_validity

Tests whether claimed solves are actually accepted as valid proofs or certificates. This protects the benchmark from inflated solve rates caused by unsupported conclusions or evaluator mismatches.

## cpu_only_non_neural_inference

Tests whether the run preserves the resource setting needed for the paper's central comparison. The purpose is to distinguish compliant CPU-only theorem proving from systems that use neural inference or external services.

## runtime_budget

Tests whether reported solves occur within the declared wall-clock and attempt limits. This keeps comparisons focused on reasoning quality and efficiency under the benchmark budget.

## better_than_random_baseline

Tests whether the submitted system improves over a generic randomized-search reference under the same benchmark conditions. This helps establish that score gains reflect more than simply spending the same number of attempts without useful guidance.
