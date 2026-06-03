# Scientist Constraints

Future agents should improve valid solve behavior without changing the task definition or winning by adding resources outside the paper's approach family.

## Fixed Scored Dataset

Use `data/benchmarks/auxiliary_core.jsonl` exactly as provided for the final scored experiment. Do not edit the construction statement, theorem goal, problem ID, or metadata.

## Fixed Baseline and Output Contract

Keep the DDAR-only baseline result in `outputs/baseline_auxiliary_core.jsonl` comparable to the proposed solver output in `outputs/hageo_auxiliary_core.jsonl`. Solver outputs must be JSONL rows containing at least `problem_id`, `solved`, `status`, `seconds`, `auxiliary_clauses`, `attempt_budget`, `rounds`, `timeout_seconds`, and `neural_inference_used`.

## Fixed Evaluation

`scripts/evaluate.sh` must remain method-agnostic and must read output artifacts from `outputs/*.jsonl`. Evaluation code must not import from `method/`, and it must reject missing, duplicate, or extra problem IDs.

## Resource and Method Constraints

The scored run is CPU-only and non-neural. Do not use GPU inference, LLM calls, online services, pretrained neural proposal models, or external proof databases during evaluation. Report the configured attempt count, auxiliary rounds, and timeout; solves found outside the declared budget should not be counted.

## Optional Extension Data

The workspace also contains a difficulty-sorted 12-problem HAGeo-409 slice and output artifacts from attempted extensions. Those runs are documented in `PROGRESS.md` but are not part of final `scores.json` because their solve rates are not directly comparable to the paper's full 409-problem Table 1 reference.
