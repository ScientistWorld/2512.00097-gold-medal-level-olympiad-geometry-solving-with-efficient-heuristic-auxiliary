> Superseded by HARDENING.md (hardening iteration).

# Verification Report

## Initial Assessment

The workspace started at milestone `core_claim`. That milestone is justified by the completed artifact set: on `auxiliary_core`, the base reference solver solves 0/1 while the submitted CPU-only method solves 1/1 with `neural_inference_used` equal to 0. The HAGeo-409 low-difficulty extension is valid but negative for a higher milestone because the submitted method trails the matched stochastic baseline on that slice.

The main risks at handoff were workspace consistency rather than a broken reproduction: `action.yaml` still requested a follow-up job, and one method scheduling change had not been verified by a completed run. I treated the completed artifacts as the source of truth for final verification.

## Issues Found

- **Minor:** A pending `action.yaml` submit request and an unverified method scheduling patch could have produced stale-score drift between the committed method and `scoring/scores.json`.
- **Minor:** Strict method-agnostic documentation used solution-adjacent wording such as construction-search phrasing and wall-clock-speed language that could mislead from-scratch agents or create hardware-dependent scoring expectations.
- **Minor:** The main evaluator originally scored only declared method outputs for the optional HAGeo-409 extension, so additional compatible method artifacts could be ignored unless train/test evaluators were used.
- **Minor:** Earlier verification had already found and fixed a solution-revealing note in the controlled benchmark metadata.

No critical integrity issue remains: evaluation reads artifacts rather than rerunning the method, `eval/` and `data/` do not import from `method/`, and no scored metric measures deviation from the paper's published values.

## Fixes Applied

- Reverted the unverified scheduling patch so the final method code matches the completed job artifacts used in `scoring/scores.json`.
- Rephrased `briefing/evaluation.md` and `scoring/EXPERIMENTS.md` to keep strict method-agnostic files focused on task, budgets, and high-level experiment purpose.
- Updated `eval/evaluate_outputs.py` to discover compatible output artifacts under `outputs/` while still requiring the core artifacts needed for `core_claim`.
- Regenerated `scoring/scores.json` from existing artifacts and re-ran `bash scripts/evaluate.sh`, `bash scripts/evaluate_train.sh`, `bash scripts/evaluate_test.sh`, and `python validate.py --compare`; all checks passed.
- Verified both URLs in `scripts/download.sh` with `curl -L --max-time 15`; both resolved to HTTP 200.
- Confirmed there are no committed `shared/` references in `method/`, `eval/`, `baseline/`, `scripts/`, `data/`, `scoring/`, `briefing/`, or `environment/`.

## Final Judgment

The workspace is ready as a partial research gym at `core_claim`. Improve-mode agents can run and modify the existing method, and from-scratch agents can use the problem definition, data, and artifact-based evaluator without importing from `method/`. The benchmark is meaningful but limited: the controlled core case supports the paper's central mechanism, while the scaled HAGeo-409 extension is a documented negative result rather than a broader reproduction.

- Milestone: core_claim
- Ready for gym use: partial
- Confidence: medium
- Key limitation: scaled reproduction with a one-problem core target, public AlphaGeometry DDAR in place of the unreleased optimized solver, and a negative low-difficulty extension.
