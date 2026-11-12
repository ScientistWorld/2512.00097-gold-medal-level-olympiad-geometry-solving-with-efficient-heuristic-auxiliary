# Scientist Constraints

Improve how many held-out problems the fixed prover proves with your auxiliary constructions; do not change what is being measured.

## Fixed by the evaluator (do not edit, do not read at run time)

- `eval/` — problem sets, goals, drawings, seeds, per-problem CPU limits, fixed baselines, the validity gate and the prover copy. The held-out problems exist only there. A proposer must not open any file under `eval/`.
- The visible train problems in `data/benchmarks/*.jsonl` may be read for development but must not be edited.
- Budget: 16 attempts per problem, at most 3 auxiliary clauses per attempt, 30 s of proposer time per problem in total.

## Submission contract

A method is an executable `proposers/<name>.sh INPUT OUTPUT` (see `proposers/README.md`). It may use any CPU code (including its own copy of a prover) inside its time limit. Clauses must define exactly one fresh point each, by one point construction or two loci from the allowlist, with no explicit coordinates.

## Out of bounds

- Recovering the withheld goals from anywhere: the evaluator's files, or the public HAGeo-409 / JGEX-231 files (matching a problem to its public statement and goal), or any stored table of known solutions for these benchmarks.
- Neural or LLM inference, network access, external theorem or proof databases.
- Editing `eval/`, `scripts/evaluate*.sh`, the scoring files, or the visible benchmark files.
