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
completed cases. Set `REDTEAM_RERUN=1` to rerun a case. Each folder keeps
`scores_test.json`, `scores_train.json`, `status.json`, and the solver artifacts.
Rejected tests keep a failure status instead of a fabricated score.

`shortcut_*` directories are intentionally invalid research submissions or
score-equivalent shortcuts, including the auxiliary-free weak ablation if
the hidden test cannot distinguish it from the reproduced method. Their
purpose is to expose what the test actually rewards.
