# Verification Report

## Initial Assessment

The workspace started at milestone `core_claim`, with a completed CPU job and artifact-based scores. The milestone is justified: on `auxiliary_core`, the base prover solves 0/1 while the submitted CPU-only method solves 1/1 with `neural_inference_used` equal to 0. The HAGeo-409 low-difficulty extension is present but does not support a higher milestone because the submitted method trails the matched stochastic baseline.

## Issues Found

- **Minor:** `data/benchmarks/auxiliary_core.jsonl` contained a metadata note that described the solution-relevant construction. This leaked solution-side information to from-scratch agents.
- **Minor:** Strict method-agnostic docs used solution/baseline names and phrasing that revealed more about the paper's method family than needed.

## Fixes Applied

- Replaced the solution-revealing `auxiliary_core` note in both `data/benchmarks/auxiliary_core.jsonl` and `data/prepare_benchmarks.py` with neutral benchmark metadata.
- Rephrased `briefing/problem.md`, `briefing/evaluation.md`, and `scoring/EXPERIMENTS.md` to describe the task, reference levels, and experiment purposes without naming the paper's algorithmic mechanism in the strict method-agnostic files.
- Re-ran `bash scripts/evaluate.sh`, `bash scripts/evaluate_train.sh`, `bash scripts/evaluate_test.sh`, and `python validate.py --compare`; all checks passed.
- Verified both URLs in `scripts/download.sh` with `curl -I -L --max-time 15`; both resolve to HTTP 200.

## Final Judgment

The workspace is ready as a partial research gym at `core_claim`. Improve-mode agents can run and modify the existing method, while from-scratch agents can use the data and evaluation code without importing from `method/`. The key limitation is scale: the full paper settings are not reproduced, and the scored extension currently shows the submitted method underperforming the matched stochastic baseline.

- Milestone: core_claim
- Ready for gym use: partial
- Confidence: medium
- Key limitation: scaled reproduction with a one-problem core target and a negative low-difficulty extension.
