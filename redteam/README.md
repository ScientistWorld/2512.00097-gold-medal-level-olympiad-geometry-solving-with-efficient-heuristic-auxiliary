Audit submissions live in one directory each. Each `run.sh` restores the
original artifacts, installs `redteam/submission.py` as a real method script,
runs the submission (or reuses the reference artifacts for a scoring-only
check), runs visible train scoring, and calls the exact standalone
`bash scripts/evaluate_test.sh` with no arguments. All child solver processes
exit before that test. Nothing changes the evaluator, Python environment,
imports, or evaluator process. The harness restores the original data,
outputs, and score files after each trial.

`originals/` preserves the initial artifact state for isolation and allowed
reuse. Only the audit harness/report sees the stored test scores and reference
metric definitions. The installed submission reads agent-visible assets only.
The original test reference is `originals/scoring/scores_test.json`, method
`hageo`. It is distinct from the paper's full-band rates in `reference.json`.

Run heavy trials in a compute job. `python redteam/run_case.py --suite` resumes
completed cases. Each case's `run.sh` forces a fresh rerun; direct calls to
the harness can use `REDTEAM_RERUN=1` to do the same. Each folder keeps
`scores_test.json`, `scores_train.json`, `status.json`, and the solver artifacts.
Rejected tests keep a failure status instead of a fabricated score.

`better_systematic` caps the generic elementary enumeration at 64 candidates,
with the reference's five-second DDAR limit and one auxiliary per attempt.
`brute_force` uses the same construction universe with a 4096-candidate cap
and a 300-second per-problem audit cap. Both invoke the real symbolic prover.
`shortcut_fallback_fix` removes coordinates tied to a previous random drawing and
uses basic candidates when heuristic generation fails. Its initial exception
and failed status are preserved separately from the corrected run. This folder
was renamed from `better_fallback` after its completed test tied the reference;
`status.json` records the original execution name. No behavior was changed.

The named-cohort ranks in `summary.json` are diagnostic calculations using
the requested absolute coefficients and population standard deviations.
The normalization cohort for future rankings is unknown. Raw metric vectors,
dominance comparisons, and skipped-value ties are the durable findings.
For the unregistered-method shortcut, the candidate is `shortcut_unregistered`;
the retained `hageo` entry belongs to the original method, not this candidate.

`shortcut_*` directories are intentionally invalid research submissions or
score-equivalent shortcuts, including the auxiliary-free weak ablation if
the hidden test cannot distinguish it from the reproduced method. Their
purpose is to expose what the test actually rewards.
