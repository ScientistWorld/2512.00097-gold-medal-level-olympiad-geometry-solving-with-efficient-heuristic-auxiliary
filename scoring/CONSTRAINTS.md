# Scientist Constraints

These constraints define what must remain fixed when a future scientist tries to improve on this benchmark. They are intended to keep comparisons focused on automated Euclidean geometry reasoning under the paper's resource assumptions.

## Problem Sets

The scientist must evaluate on the provided formal IMO-30 and HAGeo-409 problem files without editing premises, conclusions, difficulty labels, or problem inclusion. The paper's benchmark claim depends on fixed geometry instances, especially the HAGeo-409 difficulty distribution. Removing hard problems, correcting only favorable translations, or adding alternative versions changes the task.

## Data

No additional geometry problem corpora, theorem databases, proof traces, contest archives, or human-written solution sets may be used for training, tuning, retrieval, or rule mining. The scientist may use only the provided benchmark data and any data shipped in the reproduction environment. This prevents improvements that come from importing more geometry knowledge rather than improving the benchmarked reasoning approach.

## Inference Resources

Compliant evaluation must run without GPU computation, neural model inference, LLM calls, or online services. The paper's central claim is CPU-only geometry proving without neural auxiliary proposal at inference time. A method that uses an LLM, a neural guidance model, or a remote prover may be scientifically interesting, but it is not a compliant improvement for this benchmark.

## Attempt and Time Budgets

The scientist must keep the configured attempt budgets and wall-clock limits fixed for each reported experiment. HAGeo-409 comparisons should use the declared K=2,048 and K=8,192 settings, and IMO-30 should follow the reproduction's declared benchmark budget. Solves found after the budget expires must be excluded from compliant scores.

## Evaluation Procedure

All methods must use the same evaluator and proof-validity criteria. A problem is solved only when the evaluator accepts the conclusion as proved. Manual inspection may be reported as an audit, but it must not replace the automated scoring path unless the reproduction explicitly defines that audit as part of the metric for every method.

## Problem Representation

Evaluation must use the fixed formal construction representation supplied with the benchmark. The scientist must not retranslate natural-language problems, add missing assumptions, simplify conclusions, or expose answer-specific hints during evaluation. Any preprocessing must be deterministic and applied uniformly to all methods.

## Compliance Checklist

- [ ] IMO-30 and HAGeo-409 problem files are unchanged.
- [ ] HAGeo-409 difficulty labels and band assignments are unchanged.
- [ ] No external geometry datasets, proof traces, theorem databases, contest archives, or solution collections are used.
- [ ] No GPU computation, neural model inference, LLM calls, or online services are used during evaluation.
- [ ] Attempt budgets match the reported experiment settings.
- [ ] Wall-clock limits are enforced and over-budget solves are excluded.
- [ ] The same evaluator/proof-validity criteria are used for all compared methods.
- [ ] Formal problem representations are not retranslated or manually edited for evaluation.
