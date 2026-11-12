> Superseded by HARDENING.md (hardening iteration): the evaluator, data and experiments described below were replaced.

# Train/Test Evaluation Design Notes

Checked the existing split for copy-paste errors, hardcoded method defaults, paper-agreement metrics, train/test leakage, method detachment, and missing score stubs.

Changes made:

- Replaced implicit even/odd splitting with explicit per-slice problem IDs in `eval/train/evaluate_outputs.py` and `eval/test/evaluate_outputs.py`.
- Fixed a leakage issue where train validation required solver outputs for every benchmark row, including held-out rows. Each slice now requires coverage only for its own IDs and ignores extra rows.
- Added `upper_band_solve_rate` and `difficulty_weighted_solve_rate` for `hageo409_low_difficulty` in both evaluators. These make it harder to game the visible aggregate by targeting only the easiest low-difficulty cases.
- Added required `description` fields for every metric in `scoring/reference.json`, and registered the new difficulty-triangulation metrics.
- Confirmed the train/test shell wrappers point to their own eval directories and output to `scoring/scores_train.json` and `scoring/scores_test.json`.

Runtime concerns for the next runner iteration:

- Do not expect `auxiliary_core` to be a meaningful held-out data split: it contains one problem, so it remains a sanity/constraint check rather than a strong anti-shortcut signal.
- The main train/test discrimination now comes from `hageo409_low_difficulty`, but that slice is still only 12 total problems. Watch for saturation or high variance in the six-problem train and test halves.
- The evaluators remain artifact-based and method-agnostic, reading `outputs/*_<stem>.jsonl`; a future method must still emit rows for the held-out IDs before `scripts/evaluate_test.sh` can score it.
- The new metrics are computed from the `difficulty` field in solver output rows. If a future output omits difficulty, the metrics will fall back to zero difficulty and lose their intended signal; the runner should verify method outputs preserve benchmark metadata.

Fixed problem patterns:

- Full-benchmark coverage requirement in the visible train evaluator leaked held-out IDs.
- Single aggregate solve-rate on the small HAGeo slice was too easy to game by targeting easier visible cases.
- Metric schema entries were missing the required human-readable descriptions.
