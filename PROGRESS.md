# Progress

## What Works

- Audit on 2026-06-02 confirmed the existing implementation and scoring are structurally trustworthy: the method code runs DDAR with auxiliary construction attempts, while `eval/` only reads output artifacts and does not import `method/`.
- Paper analysis is complete for the central claim: HAGeo uses CPU-only DDAR plus heuristic auxiliary constructions rather than neural inference.
- Public benchmark data from `HAGeo-IMO/HAGeo-409` is downloaded into `data/downloads/` and converted into tracked JSONL slices by `data/prepare_benchmarks.py`.
- The DDAR-only baseline runs through `scripts/baseline.sh`.
- The HAGeo-style method runner runs through `scripts/method.sh`: initial DDAR, then heuristic auxiliary candidates, then rerun DDAR.
- `scripts/evaluate.sh` reads output JSONL artifacts and writes `scoring/scores.json` without importing from `method/`.

## Results

- Local smoke result on `auxiliary_core`: DDAR baseline solved 0/1, HAGeo-style runner solved 1/1 using one auxiliary construction.
- Compute-node smoke job `9b3c9005-1b5` reproduced the same `auxiliary_core` result: DDAR baseline solved 0/1, HAGeo-style runner solved 1/1 with auxiliary `x1 = on_line x1 a b, on_line x1 c d`.
- `python validate.py --compare` passes after the compute-node run. This supports `core_claim`.
- Compute-node retry job `2dffc44e-9ee` completed the prepared `hageo409_small` slice without hanging. DDAR-only solved 2/12 and the bounded HAGeo-style search also solved 2/12, so it does not yet support `core_claim_plus`.
- Compute-node job `b2a7bdfd-937` reached `core_claim_plus`: on `hageo409_small`, DDAR-only solved 2/12 and HAGeo-style auxiliary construction solved 3/12. The extra solve was `2000USATSTp2`, using a midpoint auxiliary.
- Re-audited with `python validate.py --compare` on 2026-06-02; validation passes and reports the same `auxiliary_core` and `hageo409_small` scores from current output artifacts.

## Remaining

- Run one larger bounded `hageo409_small` attempt budget now that auxiliary construction improves over DDAR on this slice.
- A fuller reproduction would require either the official HAGeo solver release or a larger in-house implementation of the paper's optimized DDAR and all heuristic categories at full K.

## Issues

- The upstream HAGeo GitHub repository currently does not include runnable source code; its README states the full code is pending release.
- The paper markdown listed `https://huggingface.co/datasets/HAGeo-409`, but the verified public dataset slug is `HAGeo-IMO/HAGeo-409`.
- The login node has a very small root filesystem. A local SciPy install failed due to space, so the vendored AlphaGeometry AR traceback dependency on SciPy was made optional. Solving still uses the DDAR algebra tables; only traceback minimization falls back.
- AlphaGeometry forced the `TkAgg` plotting backend, which fails headlessly; the vendored numerical module now uses `Agg`.
- The first `hageo409_small` expansion job was cancelled after the baseline completed but method output stayed empty. AlphaGeometry's DDAR timeout is a soft per-level threshold, so the method runner now wraps each DDAR invocation in a Unix signal-based hard wall-clock timeout and logs each processed problem.
- The first completed `hageo409_small` method run matched DDAR-only rather than improving it. Inspection showed candidate generation was treating construction predicate names as point symbols and trying too many same-category candidates early; the generator now uses left-hand-side point declarations and interleaves HAGeo-style construction categories.
- The improved generator reaches the intended effect on the small slice, but the reproduction remains scaled down from the paper's K=2048/8192 HAGeo-409 setting.

## Deviations from Paper

- The paper's official HAGeo solver code is not released in the public GitHub repository as of this run. To preserve the computation pattern, this reproduction vendors the public AlphaGeometry DDAR engine and adds a CPU-only HAGeo-style heuristic auxiliary construction search wrapper.
- The full paper setting uses K=4096 on IMO-30 and K=2048/8192 on HAGeo-409 with N=6 construction rounds. The verified core job scales this to a one-problem auxiliary core with smaller K for verification.
- The paper reports full IMO-30 and HAGeo-409 results. Current scoring includes a minimal auxiliary core experiment and a prepared small HAGeo-409 slice; the next submitted job runs the small slice with bounded CPU search.
